"""Focus timer implementation for Pomodoro-style work sessions.

This module provides the FocusTimer class for managing focus sessions
with pause/resume functionality and XP rewards.
"""

import threading
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Optional

from zenflow.database.db import Database

if TYPE_CHECKING:
    from zenflow.core.gamification import GamificationEngine


class FocusTimer:
    """Manages Pomodoro-style focus sessions with timer and XP rewards.

    Provides timer functionality with pause/resume support, database
    persistence, and gamification integration for completed sessions.

    Args:
        db: Database instance for session persistence
        config: Configuration dictionary with focus settings
        gamification_engine: Optional GamificationEngine for XP rewards
        duration: Session duration in minutes (default: 25)

    Example:
        >>> timer = FocusTimer(db, config)
        >>> timer.start(user_id=1)
        >>> # ... timer ticks down ...
        >>> result = timer.complete(user_id=1)
        >>> print(f"Earned {result['xp_earned']} XP!")
    """

    def __init__(
        self,
        db: Database,
        config: dict[str, Any],
        gamification_engine: Optional["GamificationEngine"] = None,
        duration: int = 25,
    ) -> None:
        """
        Initialize FocusTimer with dependencies.

        Args:
            db: Database instance for session persistence
            config: Configuration dictionary
            gamification_engine: Optional GamificationEngine instance for XP rewards
            duration: Session duration in minutes (default: 25)
        """
        self.db = db
        self.config = config
        self.gamification_engine = gamification_engine
        self.duration = duration * 60  # Convert to seconds
        self.remaining = self.duration
        self.running = False
        self.paused = False
        self.session_id: int | None = None
        self._timer_thread: threading.Thread | None = None

    def start(self, user_id: int) -> int:
        """
        Start a new focus session.

        Creates a session record in the database and sets the timer to running state.

        Args:
            user_id: ID of the user starting the session

        Returns:
            Session ID for the created session

        Raises:
            RuntimeError: If a session is already running
        """
        if self.running:
            raise RuntimeError("A focus session is already running")

        # Create session in database
        self.db.execute(
            """
            INSERT INTO focus_sessions (user_id, duration_minutes, completed, started_at)
            VALUES (?, ?, 0, ?)
            """,
            (user_id, self.duration // 60, datetime.now()),
        )
        self.db.commit()

        # Get the session ID
        result = self.db.fetch_one("SELECT last_insert_rowid() as id")

        if result is None:
            raise RuntimeError("Failed to create focus session")

        self.session_id = result["id"]
        self.running = True
        self.paused = False
        self.remaining = self.duration

        return self.session_id

    def pause(self) -> None:
        """
        Pause the running timer.

        Timer state is preserved and can be resumed later.

        Raises:
            RuntimeError: If timer is not running
        """
        if not self.running:
            raise RuntimeError("No focus session is running")

        self.paused = True

    def resume(self) -> None:
        """
        Resume a paused timer.

        Raises:
            RuntimeError: If timer is not paused
        """
        if not self.running:
            raise RuntimeError("No focus session is running")

        if not self.paused:
            raise RuntimeError("Timer is not paused")

        self.paused = False

    def stop(self) -> None:
        """
        Stop the timer without completing the session.

        Session is logged as incomplete and no XP is awarded.
        Resets the timer to initial state.
        """
        if not self.running:
            raise RuntimeError("No focus session is running")

        self.running = False
        self.paused = False
        self.session_id = None
        self.remaining = self.duration

    def tick(self) -> int:
        """
        Decrease remaining time by 1 second.

        Only ticks if timer is running and not paused.

        Returns:
            Remaining time in seconds
        """
        if self.running and not self.paused:
            self.remaining = max(0, self.remaining - 1)

        return self.remaining

    def complete(self, user_id: int) -> dict[str, Any]:
        """
        Complete the focus session and award XP.

        Updates session as completed, awards XP via gamification engine,
        updates daily stats, and checks for achievements.

        Args:
            user_id: ID of the user completing the session

        Returns:
            Dictionary with:
                - xp_earned: XP awarded for this session
                - total_focus_today: Total focus minutes for today
                - achievements: List of newly unlocked achievements (if any)
                - level_up: True if user leveled up

        Raises:
            RuntimeError: If no session is running or session not finished
        """
        if not self.running:
            raise RuntimeError("No focus session is running")

        if self.session_id is None:
            raise RuntimeError("No session ID found")

        if self.remaining > 0:
            raise RuntimeError("Session not finished. Use stop() to abandon.")

        # Update session as completed
        self.db.execute(
            """
            UPDATE focus_sessions
            SET completed = 1, completed_at = ?
            WHERE id = ?
            """,
            (datetime.now(), self.session_id),
        )
        self.db.commit()

        # Reset timer state
        self.running = False
        self.paused = False
        session_duration_minutes = self.duration // 60
        self.remaining = self.duration
        self.session_id = None

        # Update daily stats
        today = date.today()
        self._update_daily_stats(user_id, today, session_duration_minutes)

        # Get total focus time for today
        stats_row = self.db.fetch_one(
            """
            SELECT focus_minutes
            FROM daily_stats
            WHERE user_id = ? AND date = ?
            """,
            (user_id, today),
        )
        total_focus_today = stats_row["focus_minutes"] if stats_row else session_duration_minutes

        # Award XP and check achievements
        result: dict[str, Any] = {
            "xp_earned": 0,
            "total_focus_today": total_focus_today,
            "achievements": [],
            "level_up": False,
        }

        if self.gamification_engine:
            # Award focus session XP
            focus_xp = self.config["gamification"]["focus_xp"]
            xp_result = self.gamification_engine.award_xp(user_id, focus_xp)
            result["xp_earned"] = focus_xp
            result["level_up"] = xp_result.get("level_up", False)

            # Check for Focus King achievement (10 sessions)
            total_completed = self.db.fetch_one(
                """
                SELECT COUNT(*) as count
                FROM focus_sessions
                WHERE user_id = ? AND completed = 1
                """,
                (user_id,),
            )

            if total_completed and total_completed["count"] >= 10:
                achievements = self.gamification_engine.check_achievements(user_id)
                result["achievements"].extend(achievements)

            # Check for 5 sessions in one day achievement
            sessions_today = self.db.fetch_one(
                """
                SELECT COUNT(*) as count
                FROM focus_sessions
                WHERE user_id = ? AND completed = 1
                AND DATE(started_at) = ?
                """,
                (user_id, today),
            )

            if sessions_today and sessions_today["count"] >= 5:
                # Award bonus XP
                bonus_xp = 25
                bonus_result = self.gamification_engine.award_xp(user_id, bonus_xp)
                result["xp_earned"] += bonus_xp
                result["level_up"] = result["level_up"] or bonus_result.get("level_up", False)

        return result

    def _update_daily_stats(self, user_id: int, today: date, focus_minutes: int) -> None:
        """
        Update daily stats with focus minutes.

        Inserts or updates the daily_stats record for today.

        Args:
            user_id: ID of the user
            today: Date to update stats for
            focus_minutes: Minutes to add to focus time
        """
        # Try to update existing record
        self.db.execute(
            """
            UPDATE daily_stats
            SET focus_minutes = focus_minutes + ?
            WHERE user_id = ? AND date = ?
            """,
            (focus_minutes, user_id, today),
        )

        # If no record was updated, insert a new one
        if self.db.cursor and self.db.cursor.rowcount == 0:
            self.db.execute(
                """
                INSERT INTO daily_stats (user_id, date, focus_minutes)
                VALUES (?, ?, ?)
                """,
                (user_id, today, focus_minutes),
            )

        self.db.commit()

    def get_remaining_time(self) -> dict[str, int]:
        """
        Get remaining time formatted as minutes and seconds.

        Returns:
            Dictionary with 'minutes' and 'seconds' keys
        """
        minutes = self.remaining // 60
        seconds = self.remaining % 60
        return {"minutes": minutes, "seconds": seconds}

    def is_running(self) -> bool:
        """
        Check if timer is currently running.

        Returns:
            True if timer is running (even if paused)
        """
        return self.running

    def is_paused(self) -> bool:
        """
        Check if timer is currently paused.

        Returns:
            True if timer is paused
        """
        return self.paused
