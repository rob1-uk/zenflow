"""Rich table formatters for ZenFlow."""

from datetime import datetime
from typing import Any

from rich.table import Table
from rich.text import Text


def create_task_table(tasks: list[dict[str, Any]]) -> Table:
    """
    Create a Rich table for displaying tasks.

    Args:
        tasks: List of task dictionaries with keys:
            - id, title, priority, status, due_date, xp_reward

    Returns:
        Rich Table instance ready for display
    """
    table = Table(
        title="Tasks" if tasks else "No Tasks",
        show_header=True,
        header_style="bold cyan",
        border_style="blue",
        show_lines=False,
    )

    table.add_column("ID", style="dim", width=4, justify="right")
    table.add_column("Title", style="white", min_width=20, max_width=40)
    table.add_column("Priority", width=10, justify="center")
    table.add_column("Status", width=12, justify="center")
    table.add_column("Due Date", width=12, justify="center")
    table.add_column("XP", width=8, justify="right")

    if not tasks:
        table.add_row("", "No tasks found", "", "", "", "")
        return table

    for task in tasks:
        task_id = str(task.get("id", ""))
        title = task.get("title", "Untitled")
        priority = task.get("priority", "MEDIUM")
        status = task.get("status", "TODO")
        due_date = task.get("due_date")
        xp_reward = task.get("xp_reward", 0)

        priority_text = _format_priority(priority)
        status_text = _format_status(status)
        due_date_text = _format_due_date(due_date)
        xp_text = f"+{xp_reward} XP" if status != "DONE" else f"{xp_reward} XP"

        if len(title) > 40:
            title = title[:37] + "..."

        table.add_row(
            task_id,
            title,
            priority_text,
            status_text,
            due_date_text,
            xp_text,
        )

    return table


def _format_priority(priority: str) -> Text:
    """
    Format priority with color coding.

    Args:
        priority: Priority level (LOW, MEDIUM, HIGH)

    Returns:
        Rich Text object with appropriate styling
    """
    priority_colors = {
        "LOW": "green",
        "MEDIUM": "yellow",
        "HIGH": "red",
    }

    color = priority_colors.get(priority, "white")
    return Text(priority, style=f"bold {color}")


def _format_status(status: str) -> Text:
    """
    Format status with color coding and icons.

    Args:
        status: Task status (TODO, IN_PROGRESS, DONE)

    Returns:
        Rich Text object with appropriate styling
    """
    status_styles = {
        "TODO": ("⚪ TODO", "dim white"),
        "IN_PROGRESS": ("🔵 In Progress", "bold blue"),
        "DONE": ("✓ Done", "bold green"),
    }

    display_text, style = status_styles.get(status, (status, "white"))
    return Text(display_text, style=style)


def _format_due_date(due_date: Any | None) -> Text:
    """
    Format due date with color coding based on urgency.

    Args:
        due_date: Due date (datetime or ISO string)

    Returns:
        Rich Text object with appropriate styling
    """
    if not due_date:
        return Text("—", style="dim")

    try:
        if isinstance(due_date, str):
            dt = datetime.fromisoformat(due_date)
        else:
            dt = due_date

        now = datetime.now()
        days_until = (dt.date() - now.date()).days

        if days_until < 0:
            formatted = dt.strftime("%b %d")
            return Text(f"⚠ {formatted}", style="bold red")
        elif days_until == 0:
            return Text("Today", style="bold yellow")
        elif days_until == 1:
            return Text("Tomorrow", style="yellow")
        elif days_until <= 7:
            formatted = dt.strftime("%b %d")
            return Text(formatted, style="yellow")
        else:
            formatted = dt.strftime("%b %d")
            return Text(formatted, style="white")

    except (ValueError, AttributeError):
        return Text(str(due_date)[:12], style="dim")


def create_habit_table(habits: list[dict[str, Any]]) -> Table:
    """
    Create a Rich table for displaying habits.

    Args:
        habits: List of habit dictionaries with keys:
            - id, name, frequency, streak, last_completed

    Returns:
        Rich Table instance ready for display
    """
    table = Table(
        title="Habits" if habits else "No Habits",
        show_header=True,
        header_style="bold cyan",
        border_style="blue",
        show_lines=False,
    )

    table.add_column("ID", style="dim", width=4, justify="right")
    table.add_column("Habit", style="white", min_width=20, max_width=35)
    table.add_column("Frequency", width=10, justify="center")
    table.add_column("Streak", width=10, justify="center")
    table.add_column("Last Done", width=15, justify="center")

    if not habits:
        table.add_row("", "No habits found", "", "", "")
        return table

    for habit in habits:
        habit_id = str(habit.get("id", ""))
        name = habit.get("name", "Untitled")
        frequency = habit.get("frequency", "DAILY")
        streak = habit.get("streak", 0)
        last_completed = habit.get("last_completed")

        if len(name) > 35:
            name = name[:32] + "..."

        streak_text = _format_streak(streak)
        last_done_text = _format_last_completed(last_completed)

        table.add_row(
            habit_id,
            name,
            frequency,
            streak_text,
            last_done_text,
        )

    return table


def _format_streak(streak: int) -> Text:
    """
    Format habit streak with fire emoji for active streaks.

    Args:
        streak: Streak count

    Returns:
        Rich Text object with appropriate styling
    """
    if streak >= 7:
        return Text(f"🔥 {streak}", style="bold red")
    elif streak > 0:
        return Text(f"🔥 {streak}", style="yellow")
    else:
        return Text(str(streak), style="dim")


def _format_last_completed(last_completed: Any | None) -> Text:
    """
    Format last completed timestamp as relative time.

    Args:
        last_completed: Last completion timestamp (datetime or ISO string)

    Returns:
        Rich Text object with appropriate styling
    """
    if not last_completed:
        return Text("Never", style="dim")

    try:
        if isinstance(last_completed, str):
            dt = datetime.fromisoformat(last_completed)
        else:
            dt = last_completed

        now = datetime.now()
        delta = now - dt
        days = delta.days

        if days == 0:
            hours = delta.seconds // 3600
            if hours == 0:
                return Text("Just now", style="bold green")
            elif hours == 1:
                return Text("1 hour ago", style="green")
            else:
                return Text(f"{hours} hours ago", style="green")
        elif days == 1:
            return Text("Yesterday", style="yellow")
        elif days <= 7:
            return Text(f"{days} days ago", style="yellow")
        else:
            formatted = dt.strftime("%b %d")
            return Text(formatted, style="dim")

    except (ValueError, AttributeError):
        return Text(str(last_completed)[:15], style="dim")


def create_achievement_table(achievements: list[dict[str, Any]]) -> Table:
    """
    Create a Rich table for displaying achievements.

    Args:
        achievements: List of achievement dictionaries with keys:
            - title, description, status (locked/unlocked), xp_earned, progress

    Returns:
        Rich Table instance ready for display
    """
    table = Table(
        title="Achievements",
        show_header=True,
        header_style="bold cyan",
        border_style="blue",
        show_lines=True,
    )

    table.add_column("Achievement", style="white", min_width=20)
    table.add_column("Description", style="dim", min_width=25, max_width=45)
    table.add_column("Status", width=15, justify="center")
    table.add_column("XP", width=8, justify="right")

    if not achievements:
        table.add_row("No achievements", "", "", "")
        return table

    for achievement in achievements:
        title = achievement.get("title", "Unknown")
        description = achievement.get("description", "")
        unlocked = achievement.get("unlocked", False)
        xp_earned = achievement.get("xp_earned", 0)
        progress = achievement.get("progress", {})

        if len(description) > 45:
            description = description[:42] + "..."

        if unlocked:
            status_text = Text("✓ Earned", style="bold green")
            xp_text = f"+{xp_earned}"
        else:
            if progress:
                current = progress.get("current", 0)
                target = progress.get("target", 1)
                status_text = Text(f"🔒 {current}/{target}", style="dim")
            else:
                status_text = Text("🔒 Locked", style="dim")
            xp_text = f"+{xp_earned}"

        table.add_row(title, description, status_text, xp_text)

    return table
