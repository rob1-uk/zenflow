"""Habit tracking core functionality for ZenFlow."""

from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any, Optional

from zenflow.database.db import Database

if TYPE_CHECKING:
    from zenflow.core.gamification import GamificationEngine


class HabitTracker:
    """Manages habit tracking operations and streak calculations."""

    def __init__(
        self,
        db: Database,
        streak_calculator: Callable[[list[dict[str, Any]], str, date], int],
        config: dict[str, Any],
        gamification_engine: Optional["GamificationEngine"] = None,
    ) -> None:
        """
        Initialize HabitTracker with dependencies.

        Args:
            db: Database instance for habit persistence
            streak_calculator: Function to calculate streaks (calculate_streak_from_logs)
            config: Configuration dictionary
            gamification_engine: Optional GamificationEngine instance for XP and achievements
        """
        self.db = db
        self.streak_calculator = streak_calculator
        self.config = config
        self.gamification_engine = gamification_engine

    def create_habit(
        self,
        user_id: int,
        name: str,
        frequency: str = "DAILY",
        target_days: int | None = None,
    ) -> dict[str, Any]:
        """
        Create a new habit.

        Args:
            user_id: ID of the user creating the habit
            name: Habit name (required)
            frequency: Habit frequency (DAILY or WEEKLY)
            target_days: Optional target streak goal

        Returns:
            Dictionary containing habit data with keys:
                - id, user_id, name, frequency, streak, longest_streak,
                  last_completed, target_days, created_at

        Raises:
            ValueError: If name is empty or frequency is invalid
        """
        if not name or not name.strip():
            raise ValueError("Habit name cannot be empty")

        frequency_normalized = frequency.upper()
        valid_frequencies = ["DAILY", "WEEKLY"]
        if frequency_normalized not in valid_frequencies:
            raise ValueError(
                f"Invalid frequency '{frequency}'. Must be one of: {', '.join(valid_frequencies)}"
            )

        now = datetime.now()
        self.db.execute(
            """
            INSERT INTO habits
            (user_id, name, frequency, streak, longest_streak, target_days, created_at)
            VALUES (?, ?, ?, 0, 0, ?, ?)
            """,
            (user_id, name, frequency_normalized, target_days, now),
        )
        self.db.commit()

        habit = self.db.fetch_one(
            "SELECT * FROM habits WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        )

        return dict(habit) if habit else {}

    def track_habit(self, user_id: int, habit_id: int) -> dict[str, Any]:
        """
        Mark a habit as completed for today.

        Prevents double-tracking the same day. Updates streak and longest_streak.
        Checks for milestone achievements and awards bonus XP.

        Args:
            user_id: ID of the user tracking the habit
            habit_id: ID of the habit to track

        Returns:
            Dictionary containing tracking result with keys:
                - habit: Updated habit data
                - streak: Current streak value
                - longest_streak: Longest streak achieved
                - xp_earned: XP awarded (base + milestone bonus)
                - milestone_reached: Boolean indicating if milestone was reached
                - milestone_xp: Bonus XP from milestone (if applicable)
                - achievements: List of newly unlocked achievements (if engine available)

        Raises:
            ValueError: If habit not found, doesn't belong to user, or already tracked today
        """
        # Fetch habit
        habit = self.db.fetch_one(
            "SELECT * FROM habits WHERE id = ? AND user_id = ?",
            (habit_id, user_id),
        )

        if not habit:
            raise ValueError(f"Habit {habit_id} not found or doesn't belong to user")

        # Check if already tracked today
        today = date.today()
        existing_log = self.db.fetch_one(
            """
            SELECT id FROM habit_logs
            WHERE habit_id = ? AND DATE(completed_at) = ?
            """,
            (habit_id, today),
        )

        if existing_log:
            raise ValueError(f"Habit {habit_id} already tracked today")

        # Log the completion
        now = datetime.now()
        self.db.execute(
            "INSERT INTO habit_logs (habit_id, completed_at) VALUES (?, ?)",
            (habit_id, now),
        )
        self.db.commit()

        # Recalculate streak
        new_streak = self.calculate_streak(habit_id)
        new_longest_streak = max(habit["longest_streak"], new_streak)

        # Update habit with new streak data
        self.db.execute(
            """
            UPDATE habits
            SET streak = ?, longest_streak = ?, last_completed = ?
            WHERE id = ?
            """,
            (new_streak, new_longest_streak, now, habit_id),
        )
        self.db.commit()

        # Fetch updated habit
        updated_habit = self.db.fetch_one("SELECT * FROM habits WHERE id = ?", (habit_id,))

        # Calculate base XP (from config)
        base_xp = 15  # Default base XP for habit tracking

        # Check for milestone and calculate bonus XP
        milestone_xp = 0
        milestone_reached = False
        milestone_config = self.config.get("gamification", {}).get("habit_milestone_xp", {})

        if new_streak in milestone_config:
            milestone_xp = milestone_config[new_streak]
            milestone_reached = True

        total_xp = base_xp + milestone_xp

        result: dict[str, Any] = {
            "habit": dict(updated_habit) if updated_habit else {},
            "streak": new_streak,
            "longest_streak": new_longest_streak,
            "xp_earned": total_xp,
            "milestone_reached": milestone_reached,
            "milestone_xp": milestone_xp,
        }

        # If gamification engine is available, award XP and check achievements
        if self.gamification_engine:
            # Award base XP
            xp_data = self.gamification_engine.award_xp(
                user_id=user_id, xp_amount=base_xp, reason=f"Habit tracked: {habit['name']}"
            )

            # Award milestone XP if applicable
            if milestone_reached:
                milestone_xp_data = self.gamification_engine.award_xp(
                    user_id=user_id,
                    xp_amount=milestone_xp,
                    reason=f"Milestone: {new_streak}-day streak",
                )
                # Use the final XP data after milestone bonus
                xp_data = milestone_xp_data

            result["xp_data"] = xp_data

            # Check for newly unlocked achievements
            achievements = self.gamification_engine.check_achievements(user_id)
            result["achievements"] = achievements

        # Update daily stats
        self._update_daily_stats(user_id, today, xp_earned=total_xp)

        return result

    def list_habits(
        self,
        user_id: int,
        frequency: str | None = None,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        """
        List habits with optional filtering.

        Args:
            user_id: ID of the user
            frequency: Optional frequency filter (DAILY or WEEKLY)
            active_only: If True, only return habits with streak > 0 (default: False)

        Returns:
            List of habit dictionaries

        Raises:
            ValueError: If frequency value is invalid
        """
        query = "SELECT * FROM habits WHERE user_id = ?"
        params: list[Any] = [user_id]

        if frequency:
            frequency_normalized = frequency.upper()
            valid_frequencies = ["DAILY", "WEEKLY"]
            if frequency_normalized not in valid_frequencies:
                raise ValueError(
                    f"Invalid frequency '{frequency}'. Must be one of: {', '.join(valid_frequencies)}"
                )
            query += " AND frequency = ?"
            params.append(frequency_normalized)

        if active_only:
            query += " AND streak > 0"

        query += " ORDER BY created_at DESC"

        habits = self.db.fetch_all(query, tuple(params))
        return [dict(habit) for habit in habits]

    def calculate_streak(self, habit_id: int) -> int:
        """
        Calculate current streak for a habit.

        Args:
            habit_id: ID of the habit

        Returns:
            Current streak count (days for DAILY, weeks for WEEKLY)

        Raises:
            ValueError: If habit not found
        """
        # Fetch habit
        habit = self.db.fetch_one("SELECT * FROM habits WHERE id = ?", (habit_id,))

        if not habit:
            raise ValueError(f"Habit {habit_id} not found")

        # Fetch all completion logs
        logs = self.db.fetch_all(
            "SELECT completed_at FROM habit_logs WHERE habit_id = ? ORDER BY completed_at DESC",
            (habit_id,),
        )

        # Convert to list of dicts for streak calculator
        logs_list = [dict(log) for log in logs]

        # Calculate streak using utility function
        today = date.today()
        return self.streak_calculator(logs_list, habit["frequency"], today)

    def get_calendar(self, habit_id: int, days: int = 30) -> dict[str, Any]:
        """
        Get habit completion calendar for visualization.

        Args:
            habit_id: ID of the habit
            days: Number of days to retrieve (default: 30)

        Returns:
            Dictionary with:
                - habit: Habit data
                - completions: List of dates with completions (date objects)
                - date_range: Tuple of (start_date, end_date)
                - completion_map: Dict mapping date strings to boolean completion status

        Raises:
            ValueError: If habit not found
        """
        # Fetch habit
        habit = self.db.fetch_one("SELECT * FROM habits WHERE id = ?", (habit_id,))

        if not habit:
            raise ValueError(f"Habit {habit_id} not found")

        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        # Fetch completions in date range
        logs = self.db.fetch_all(
            """
            SELECT completed_at
            FROM habit_logs
            WHERE habit_id = ? AND DATE(completed_at) >= ? AND DATE(completed_at) <= ?
            ORDER BY completed_at ASC
            """,
            (habit_id, start_date, end_date),
        )

        # Convert logs to date objects
        completion_dates = set()
        for log in logs:
            completed_at = log["completed_at"]
            if isinstance(completed_at, str):
                try:
                    dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                    completion_dates.add(dt.date())
                except ValueError:
                    completion_dates.add(date.fromisoformat(completed_at))
            elif isinstance(completed_at, datetime):
                completion_dates.add(completed_at.date())
            elif isinstance(completed_at, date):
                completion_dates.add(completed_at)

        # Create completion map for all days in range
        completion_map = {}
        current_date = start_date
        while current_date <= end_date:
            completion_map[current_date.isoformat()] = current_date in completion_dates
            current_date += timedelta(days=1)

        # Calculate completion rate
        total_days = len(completion_map)
        completed_days = sum(1 for completed in completion_map.values() if completed)
        completion_rate = (completed_days / total_days * 100) if total_days > 0 else 0

        return {
            "habit": dict(habit),
            "completions": sorted(completion_dates),
            "date_range": (start_date, end_date),
            "completion_map": completion_map,
            "completion_rate": completion_rate,
            "total_days": total_days,
            "completed_days": completed_days,
        }

    def delete_habit(self, user_id: int, habit_id: int) -> bool:
        """
        Delete a habit and all its logs.

        Args:
            user_id: ID of the user deleting the habit
            habit_id: ID of the habit to delete

        Returns:
            True if habit was deleted successfully

        Raises:
            ValueError: If habit not found or doesn't belong to user
        """
        habit = self.db.fetch_one(
            "SELECT * FROM habits WHERE id = ? AND user_id = ?",
            (habit_id, user_id),
        )

        if not habit:
            raise ValueError(f"Habit {habit_id} not found or doesn't belong to user")

        # Delete habit logs first (foreign key constraint)
        self.db.execute("DELETE FROM habit_logs WHERE habit_id = ?", (habit_id,))

        # Delete habit
        self.db.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
        self.db.commit()

        return True

    def get_habit_stats(self, user_id: int) -> dict[str, Any]:
        """
        Get habit statistics for a user.

        Args:
            user_id: ID of the user

        Returns:
            Dictionary with habit statistics:
                - total: Total number of habits
                - active: Number of habits with active streaks (streak > 0)
                - longest_streak: Longest streak across all habits
                - total_completions: Total number of habit completions
                - by_frequency: Count by frequency type
        """
        all_habits = self.list_habits(user_id)

        # Get longest streak
        longest_streak = 0
        if all_habits:
            longest_streak = max(h["longest_streak"] for h in all_habits)

        # Count total completions
        completions_result = self.db.fetch_one(
            """
            SELECT COUNT(*) as count
            FROM habit_logs hl
            JOIN habits h ON hl.habit_id = h.id
            WHERE h.user_id = ?
            """,
            (user_id,),
        )
        total_completions = completions_result["count"] if completions_result else 0

        stats = {
            "total": len(all_habits),
            "active": len([h for h in all_habits if h["streak"] > 0]),
            "longest_streak": longest_streak,
            "total_completions": total_completions,
            "by_frequency": {
                "DAILY": len([h for h in all_habits if h["frequency"] == "DAILY"]),
                "WEEKLY": len([h for h in all_habits if h["frequency"] == "WEEKLY"]),
            },
        }

        return stats

    def _update_daily_stats(
        self,
        user_id: int,
        stat_date: date,
        tasks_completed: int = 0,
        xp_earned: int = 0,
        focus_minutes: int = 0,
    ) -> None:
        """
        Update daily statistics for a user.

        This is an upsert operation - if a record exists for the date, it increments
        the values; otherwise, it creates a new record.

        Args:
            user_id: ID of the user
            stat_date: Date for the statistics
            tasks_completed: Number of tasks completed to add (default: 0)
            xp_earned: XP earned to add (default: 0)
            focus_minutes: Focus minutes to add (default: 0)
        """
        # Check if record exists for this date
        existing = self.db.fetch_one(
            "SELECT * FROM daily_stats WHERE user_id = ? AND date = ?", (user_id, stat_date)
        )

        if existing:
            # Update existing record
            self.db.execute(
                """
                UPDATE daily_stats
                SET tasks_completed = tasks_completed + ?,
                    xp_earned = xp_earned + ?,
                    focus_minutes = focus_minutes + ?
                WHERE user_id = ? AND date = ?
                """,
                (tasks_completed, xp_earned, focus_minutes, user_id, stat_date),
            )
        else:
            # Insert new record
            self.db.execute(
                """
                INSERT INTO daily_stats (user_id, date, tasks_completed, xp_earned, focus_minutes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, stat_date, tasks_completed, xp_earned, focus_minutes),
            )

        self.db.commit()
