"""Gamification engine for ZenFlow.

This module handles XP awards, level calculations, and achievement unlocking
for the productivity gamification system.
"""

from datetime import datetime
from typing import Any

from zenflow.database.db import Database
from zenflow.utils.xp_calculator import (
    calculate_level,
    calculate_level_progress,
    calculate_xp_to_next_level,
)

# Achievement definitions with type, title, description, XP reward, and unlock condition
ACHIEVEMENT_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "first_task",
        "title": "First Task",
        "description": "Complete your first task",
        "xp": 25,
        "condition": lambda stats: stats.get("tasks_completed", 0) >= 1,
    },
    {
        "type": "task_master",
        "title": "Task Master",
        "description": "Complete 10 tasks",
        "xp": 100,
        "condition": lambda stats: stats.get("tasks_completed", 0) >= 10,
    },
    {
        "type": "task_centurion",
        "title": "Task Centurion",
        "description": "Complete 100 tasks",
        "xp": 500,
        "condition": lambda stats: stats.get("tasks_completed", 0) >= 100,
    },
    {
        "type": "task_legend",
        "title": "Task Legend",
        "description": "Complete 500 tasks",
        "xp": 1000,
        "condition": lambda stats: stats.get("tasks_completed", 0) >= 500,
    },
    {
        "type": "week_warrior",
        "title": "Week Warrior",
        "description": "Achieve a 7-day habit streak",
        "xp": 100,
        "condition": lambda stats: stats.get("max_habit_streak", 0) >= 7,
    },
    {
        "type": "month_master",
        "title": "Month Master",
        "description": "Achieve a 30-day habit streak",
        "xp": 250,
        "condition": lambda stats: stats.get("max_habit_streak", 0) >= 30,
    },
    {
        "type": "century_club",
        "title": "Century Club",
        "description": "Achieve a 100-day habit streak",
        "xp": 500,
        "condition": lambda stats: stats.get("max_habit_streak", 0) >= 100,
    },
    {
        "type": "focus_starter",
        "title": "Focus Starter",
        "description": "Complete your first focus session",
        "xp": 25,
        "condition": lambda stats: stats.get("focus_sessions_completed", 0) >= 1,
    },
    {
        "type": "focus_king",
        "title": "Focus King",
        "description": "Complete 10 focus sessions",
        "xp": 150,
        "condition": lambda stats: stats.get("focus_sessions_completed", 0) >= 10,
    },
    {
        "type": "focus_master",
        "title": "Focus Master",
        "description": "Complete 50 focus sessions",
        "xp": 300,
        "condition": lambda stats: stats.get("focus_sessions_completed", 0) >= 50,
    },
    {
        "type": "productive_day",
        "title": "Productive Day",
        "description": "Complete 5 or more tasks in a single day",
        "xp": 50,
        "condition": lambda stats: stats.get("max_tasks_per_day", 0) >= 5,
    },
    {
        "type": "power_user",
        "title": "Power User",
        "description": "Complete 10 or more tasks in a single day",
        "xp": 100,
        "condition": lambda stats: stats.get("max_tasks_per_day", 0) >= 10,
    },
    {
        "type": "habit_builder",
        "title": "Habit Builder",
        "description": "Track 3 active habits",
        "xp": 75,
        "condition": lambda stats: stats.get("active_habits", 0) >= 3,
    },
    {
        "type": "level_5",
        "title": "Rising Star",
        "description": "Reach Level 5",
        "xp": 100,
        "condition": lambda stats: stats.get("level", 1) >= 5,
    },
    {
        "type": "level_10",
        "title": "Productivity Pro",
        "description": "Reach Level 10",
        "xp": 250,
        "condition": lambda stats: stats.get("level", 1) >= 10,
    },
]


class GamificationEngine:
    """Manages gamification features: XP, levels, and achievements.

    This class handles all gamification logic including awarding XP,
    calculating levels, checking for achievement unlocks, and managing
    user progression through the productivity system.

    Args:
        db: Database instance for persistence
        config: Configuration dictionary containing gamification settings

    Example:
        >>> engine = GamificationEngine(db, config)
        >>> result = engine.award_xp(user_id=1, xp_amount=50, reason="Task completed")
        >>> print(result['new_level'])
    """

    def __init__(self, db: Database, config: dict[str, Any]) -> None:
        """Initialize GamificationEngine with database and config.

        Args:
            db: Database instance for queries and persistence
            config: Configuration dictionary with gamification settings
        """
        self.db = db
        self.config = config
        self.xp_per_level = config["gamification"]["xp_per_level"]

    def award_xp(self, user_id: int, xp_amount: int, reason: str = "") -> dict[str, Any]:
        """Award XP to a user and update their level.

        Updates the user's total XP and recalculates their level.
        Detects level-ups and returns comprehensive progression data.

        Args:
            user_id: ID of the user to award XP to
            xp_amount: Amount of XP to award (must be positive)
            reason: Optional reason for XP award (for logging)

        Returns:
            Dictionary containing:
                - xp_awarded: Amount of XP awarded
                - total_xp: New total XP
                - old_level: Level before award
                - new_level: Level after award
                - level_up: Boolean indicating if user leveled up
                - xp_to_next: XP needed to reach next level
                - progress: Progress to next level (0.0 to 1.0)

        Raises:
            ValueError: If xp_amount is negative or user_id doesn't exist
        """
        if xp_amount < 0:
            raise ValueError(f"XP amount must be non-negative, got: {xp_amount}")

        # Fetch current user data
        user = self.db.fetch_one("SELECT xp, level FROM users WHERE id = ?", (user_id,))

        if user is None:
            raise ValueError(f"User with ID {user_id} not found")

        old_xp = user["xp"]
        old_level = user["level"]

        # Calculate new XP and level
        new_xp = old_xp + xp_amount
        new_level = calculate_level(new_xp, self.xp_per_level)

        # Update user in database
        self.db.execute(
            "UPDATE users SET xp = ?, level = ? WHERE id = ?", (new_xp, new_level, user_id)
        )
        self.db.commit()

        # Calculate progression metrics
        level_up = new_level > old_level
        xp_to_next = calculate_xp_to_next_level(new_xp, self.xp_per_level)
        progress = calculate_level_progress(new_xp, self.xp_per_level)

        return {
            "xp_awarded": xp_amount,
            "total_xp": new_xp,
            "old_level": old_level,
            "new_level": new_level,
            "level_up": level_up,
            "xp_to_next": xp_to_next,
            "progress": progress,
        }

    def calculate_level(self, total_xp: int) -> int:
        """Calculate user level based on total XP.

        Delegates to xp_calculator utility function.

        Args:
            total_xp: Total XP accumulated by user

        Returns:
            Current level (minimum 1)
        """
        return calculate_level(total_xp, self.xp_per_level)

    def xp_to_next_level(self, current_xp: int) -> int:
        """Calculate XP needed to reach next level.

        Delegates to xp_calculator utility function.

        Args:
            current_xp: Current total XP

        Returns:
            XP needed to reach next level
        """
        return calculate_xp_to_next_level(current_xp, self.xp_per_level)

    def check_achievements(self, user_id: int) -> list[dict[str, Any]]:
        """Check for and unlock newly achieved achievements.

        Evaluates all achievement conditions against current user stats.
        Automatically unlocks any achievements that meet their conditions
        but haven't been unlocked yet.

        Args:
            user_id: ID of user to check achievements for

        Returns:
            List of newly unlocked achievements, each containing:
                - achievement_type: Unique achievement identifier
                - title: Achievement title
                - description: Achievement description
                - xp_earned: XP awarded for achievement
                - unlocked_at: Timestamp of unlock

        Raises:
            ValueError: If user_id doesn't exist
        """
        # Get user stats
        stats = self._get_user_stats(user_id)

        # Get already unlocked achievements
        unlocked = self.db.fetch_all(
            "SELECT achievement_type FROM achievements WHERE user_id = ?", (user_id,)
        )
        unlocked_types = {row["achievement_type"] for row in unlocked}

        # Check each achievement definition
        newly_unlocked = []
        for achievement in ACHIEVEMENT_DEFINITIONS:
            achievement_type = achievement["type"]

            # Skip if already unlocked
            if achievement_type in unlocked_types:
                continue

            # Check if condition is met
            if achievement["condition"](stats):
                unlocked_achievement = self.unlock_achievement(user_id, achievement_type)
                if unlocked_achievement:
                    newly_unlocked.append(unlocked_achievement)

        return newly_unlocked

    def unlock_achievement(self, user_id: int, achievement_type: str) -> dict[str, Any] | None:
        """Unlock a specific achievement for a user.

        Awards achievement XP to the user and records the unlock.
        Handles duplicate unlocks gracefully (returns None if already unlocked).

        Args:
            user_id: ID of user to unlock achievement for
            achievement_type: Type identifier of achievement to unlock

        Returns:
            Dictionary with achievement data if newly unlocked, None if already unlocked:
                - achievement_type: Achievement identifier
                - title: Achievement title
                - description: Achievement description
                - xp_earned: XP awarded
                - unlocked_at: Unlock timestamp

        Raises:
            ValueError: If achievement_type is not recognized or user doesn't exist
        """
        # Find achievement definition
        achievement_def = None
        for ach in ACHIEVEMENT_DEFINITIONS:
            if ach["type"] == achievement_type:
                achievement_def = ach
                break

        if achievement_def is None:
            raise ValueError(f"Unknown achievement type: {achievement_type}")

        # Check if already unlocked
        existing = self.db.fetch_one(
            "SELECT id FROM achievements WHERE user_id = ? AND achievement_type = ?",
            (user_id, achievement_type),
        )

        if existing is not None:
            return None  # Already unlocked

        # Insert achievement
        unlocked_at = datetime.now().isoformat()
        self.db.execute(
            """
            INSERT INTO achievements (user_id, achievement_type, title, description, xp_earned)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                achievement_type,
                achievement_def["title"],
                achievement_def["description"],
                achievement_def["xp"],
            ),
        )
        self.db.commit()

        # Award XP for achievement
        self.award_xp(user_id, achievement_def["xp"], f"Achievement: {achievement_def['title']}")

        return {
            "achievement_type": achievement_type,
            "title": achievement_def["title"],
            "description": achievement_def["description"],
            "xp_earned": achievement_def["xp"],
            "unlocked_at": unlocked_at,
        }

    def _get_user_stats(self, user_id: int) -> dict[str, Any]:
        """Gather comprehensive user statistics for achievement checking.

        Private helper method that aggregates data from multiple tables
        to evaluate achievement conditions.

        Args:
            user_id: ID of user to gather stats for

        Returns:
            Dictionary containing various user statistics:
                - tasks_completed: Total tasks completed
                - max_habit_streak: Longest habit streak achieved
                - focus_sessions_completed: Total completed focus sessions
                - max_tasks_per_day: Most tasks completed in a single day
                - active_habits: Number of active habits
                - level: Current user level

        Raises:
            ValueError: If user doesn't exist
        """
        # Get user data
        user = self.db.fetch_one("SELECT level FROM users WHERE id = ?", (user_id,))

        if user is None:
            raise ValueError(f"User with ID {user_id} not found")

        # Count completed tasks
        tasks_result = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM tasks WHERE user_id = ? AND status = 'DONE'", (user_id,)
        )
        tasks_completed = tasks_result["count"] if tasks_result else 0

        # Get max habit streak
        habits_result = self.db.fetch_one(
            "SELECT MAX(longest_streak) as max_streak FROM habits WHERE user_id = ?", (user_id,)
        )
        max_habit_streak = (
            habits_result["max_streak"] if habits_result and habits_result["max_streak"] else 0
        )

        # Count completed focus sessions
        focus_result = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM focus_sessions WHERE user_id = ? AND completed = 1",
            (user_id,),
        )
        focus_sessions_completed = focus_result["count"] if focus_result else 0

        # Get max tasks completed in a day
        max_tasks_day_result = self.db.fetch_one(
            "SELECT MAX(tasks_completed) as max_tasks FROM daily_stats WHERE user_id = ?",
            (user_id,),
        )
        max_tasks_per_day = (
            max_tasks_day_result["max_tasks"]
            if max_tasks_day_result and max_tasks_day_result["max_tasks"]
            else 0
        )

        # Count active habits
        active_habits_result = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM habits WHERE user_id = ?", (user_id,)
        )
        active_habits = active_habits_result["count"] if active_habits_result else 0

        return {
            "tasks_completed": tasks_completed,
            "max_habit_streak": max_habit_streak,
            "focus_sessions_completed": focus_sessions_completed,
            "max_tasks_per_day": max_tasks_per_day,
            "active_habits": active_habits,
            "level": user["level"],
        }
