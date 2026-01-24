"""Task management core functionality for ZenFlow."""

from collections.abc import Callable
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Optional

from zenflow.database.db import Database

if TYPE_CHECKING:
    from zenflow.core.gamification import GamificationEngine


class TaskManager:
    """Manages task CRUD operations and task-related logic."""

    def __init__(
        self,
        db: Database,
        xp_calculator: Callable[[str, dict[str, Any]], int],
        config: dict[str, Any],
        gamification_engine: Optional["GamificationEngine"] = None,
    ) -> None:
        """
        Initialize TaskManager with dependencies.

        Args:
            db: Database instance for task persistence
            xp_calculator: Function to calculate XP rewards (calculate_task_xp)
            config: Configuration dictionary
            gamification_engine: Optional GamificationEngine instance for XP and achievements
        """
        self.db = db
        self.xp_calculator = xp_calculator
        self.config = config
        self.gamification_engine = gamification_engine

    def create_task(
        self,
        user_id: int,
        title: str,
        description: str | None = None,
        priority: str = "MEDIUM",
        due_date: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Create a new task.

        Args:
            user_id: ID of the user creating the task
            title: Task title (required)
            description: Optional task description
            priority: Task priority (LOW, MEDIUM, or HIGH)
            due_date: Optional due date for the task

        Returns:
            Dictionary containing task data with keys:
                - id, title, description, priority, status, due_date, xp_reward, created_at

        Raises:
            ValueError: If priority is invalid or title is empty
        """
        if not title or not title.strip():
            raise ValueError("Task title cannot be empty")

        priority_normalized = priority.upper()
        valid_priorities = ["LOW", "MEDIUM", "HIGH"]
        if priority_normalized not in valid_priorities:
            raise ValueError(
                f"Invalid priority '{priority}'. Must be one of: {', '.join(valid_priorities)}"
            )

        xp_reward = self.xp_calculator(priority_normalized, self.config)

        now = datetime.now()
        self.db.execute(
            """
            INSERT INTO tasks
            (user_id, title, description, priority, status, due_date, xp_reward, created_at)
            VALUES (?, ?, ?, ?, 'TODO', ?, ?, ?)
            """,
            (user_id, title, description, priority_normalized, due_date, xp_reward, now),
        )
        self.db.commit()

        task = self.db.fetch_one(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        )

        return dict(task) if task else {}

    def list_tasks(
        self,
        user_id: int,
        status: str | None = None,
        priority: str | None = None,
        include_completed: bool = True,
    ) -> list[dict[str, Any]]:
        """
        List tasks with optional filtering.

        Args:
            user_id: ID of the user
            status: Optional status filter (TODO, IN_PROGRESS, DONE)
            priority: Optional priority filter (LOW, MEDIUM, HIGH)
            include_completed: Whether to include completed tasks (default: True)

        Returns:
            List of task dictionaries

        Raises:
            ValueError: If status or priority values are invalid
        """
        query = "SELECT * FROM tasks WHERE user_id = ?"
        params: list[Any] = [user_id]

        if status:
            status_normalized = status.upper()
            valid_statuses = ["TODO", "IN_PROGRESS", "DONE"]
            if status_normalized not in valid_statuses:
                raise ValueError(
                    f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}"
                )
            query += " AND status = ?"
            params.append(status_normalized)

        if priority:
            priority_normalized = priority.upper()
            valid_priorities = ["LOW", "MEDIUM", "HIGH"]
            if priority_normalized not in valid_priorities:
                raise ValueError(
                    f"Invalid priority '{priority}'. Must be one of: {', '.join(valid_priorities)}"
                )
            query += " AND priority = ?"
            params.append(priority_normalized)

        if not include_completed:
            query += " AND status != 'DONE'"

        query += " ORDER BY created_at DESC"

        tasks = self.db.fetch_all(query, tuple(params))
        return [dict(task) for task in tasks]

    def complete_task(self, user_id: int, task_id: int) -> dict[str, Any]:
        """
        Mark a task as complete.

        Args:
            user_id: ID of the user completing the task
            task_id: ID of the task to complete

        Returns:
            Dictionary containing completion result with keys:
                - task: Task data
                - xp_earned: XP awarded for completion
                - xp_data: Gamification data (if engine available)
                - achievements: List of newly unlocked achievements (if engine available)

        Raises:
            ValueError: If task not found, already completed, or doesn't belong to user
        """
        task = self.db.fetch_one(
            "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, user_id),
        )

        if not task:
            raise ValueError(f"Task {task_id} not found or doesn't belong to user")

        if task["status"] == "DONE":
            raise ValueError(f"Task {task_id} is already completed")

        now = datetime.now()
        self.db.execute(
            "UPDATE tasks SET status = 'DONE', completed_at = ? WHERE id = ?",
            (now, task_id),
        )
        self.db.commit()

        updated_task = self.db.fetch_one("SELECT * FROM tasks WHERE id = ?", (task_id,))

        result: dict[str, Any] = {
            "task": dict(updated_task) if updated_task else {},
            "xp_earned": task["xp_reward"],
        }

        # If gamification engine is available, award XP and check achievements
        if self.gamification_engine:
            # Award XP for task completion
            xp_data = self.gamification_engine.award_xp(
                user_id=user_id,
                xp_amount=task["xp_reward"],
                reason=f"Task completed: {task['title']}",
            )
            result["xp_data"] = xp_data

            # Check for newly unlocked achievements
            achievements = self.gamification_engine.check_achievements(user_id)
            result["achievements"] = achievements

        # Update daily stats
        self._update_daily_stats(
            user_id, date.today(), tasks_completed=1, xp_earned=task["xp_reward"]
        )

        return result

    def update_task(
        self,
        user_id: int,
        task_id: int,
        title: str | None = None,
        description: str | None = None,
        priority: str | None = None,
        due_date: datetime | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """
        Update task details.

        Args:
            user_id: ID of the user updating the task
            task_id: ID of the task to update
            title: New title (optional)
            description: New description (optional)
            priority: New priority (optional, LOW/MEDIUM/HIGH)
            due_date: New due date (optional)
            status: New status (optional, TODO/IN_PROGRESS/DONE)

        Returns:
            Updated task dictionary

        Raises:
            ValueError: If task not found, invalid values, or doesn't belong to user
        """
        task = self.db.fetch_one(
            "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, user_id),
        )

        if not task:
            raise ValueError(f"Task {task_id} not found or doesn't belong to user")

        updates: list[str] = []
        params: list[Any] = []

        if title is not None:
            if not title.strip():
                raise ValueError("Task title cannot be empty")
            updates.append("title = ?")
            params.append(title)

        if description is not None:
            updates.append("description = ?")
            params.append(description)

        if priority is not None:
            priority_normalized = priority.upper()
            valid_priorities = ["LOW", "MEDIUM", "HIGH"]
            if priority_normalized not in valid_priorities:
                raise ValueError(
                    f"Invalid priority '{priority}'. Must be one of: {', '.join(valid_priorities)}"
                )
            xp_reward = self.xp_calculator(priority_normalized, self.config)
            updates.append("priority = ?")
            updates.append("xp_reward = ?")
            params.extend([priority_normalized, xp_reward])

        if due_date is not None:
            updates.append("due_date = ?")
            params.append(due_date)

        if status is not None:
            status_normalized = status.upper()
            valid_statuses = ["TODO", "IN_PROGRESS", "DONE"]
            if status_normalized not in valid_statuses:
                raise ValueError(
                    f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}"
                )
            updates.append("status = ?")
            params.append(status_normalized)

            if status_normalized == "DONE" and not task["completed_at"]:
                updates.append("completed_at = ?")
                params.append(datetime.now())

        if not updates:
            return dict(task)

        params.append(task_id)
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
        self.db.execute(query, tuple(params))
        self.db.commit()

        updated_task = self.db.fetch_one("SELECT * FROM tasks WHERE id = ?", (task_id,))

        return dict(updated_task) if updated_task else {}

    def delete_task(self, user_id: int, task_id: int) -> bool:
        """
        Delete a task.

        Args:
            user_id: ID of the user deleting the task
            task_id: ID of the task to delete

        Returns:
            True if task was deleted successfully

        Raises:
            ValueError: If task not found or doesn't belong to user
        """
        task = self.db.fetch_one(
            "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, user_id),
        )

        if not task:
            raise ValueError(f"Task {task_id} not found or doesn't belong to user")

        self.db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.db.commit()

        return True

    def get_task_stats(self, user_id: int) -> dict[str, Any]:
        """
        Get task statistics for a user.

        Args:
            user_id: ID of the user

        Returns:
            Dictionary with task statistics:
                - total: Total number of tasks
                - completed: Number of completed tasks
                - pending: Number of pending tasks (TODO + IN_PROGRESS)
                - by_priority: Count by priority level
        """
        all_tasks = self.list_tasks(user_id, include_completed=True)

        stats = {
            "total": len(all_tasks),
            "completed": len([t for t in all_tasks if t["status"] == "DONE"]),
            "pending": len([t for t in all_tasks if t["status"] != "DONE"]),
            "by_priority": {
                "LOW": len([t for t in all_tasks if t["priority"] == "LOW"]),
                "MEDIUM": len([t for t in all_tasks if t["priority"] == "MEDIUM"]),
                "HIGH": len([t for t in all_tasks if t["priority"] == "HIGH"]),
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
