"""Rich panel and formatting utilities for ZenFlow."""

from typing import Any

from rich.align import Align
from rich.panel import Panel


def create_xp_panel(xp_data: dict[str, Any]) -> Panel:
    """
    Create a Rich panel for displaying XP and level information.

    Args:
        xp_data: Dictionary with keys:
            - xp_earned: XP just earned (int)
            - total_xp: Total XP accumulated (int)
            - level: Current level (int)
            - xp_to_next_level: XP needed for next level (int)
            - progress: Progress percentage (float, 0.0-1.0)

    Returns:
        Rich Panel instance ready for display
    """
    xp_earned = xp_data.get("xp_earned", 0)
    total_xp = xp_data.get("total_xp", 0)
    level = xp_data.get("level", 1)
    xp_to_next_level = xp_data.get("xp_to_next_level", 1000)
    progress = xp_data.get("progress", 0.0)

    progress_bar = _create_progress_bar(progress, width=20)

    content = f"""[bold green]+{xp_earned} XP[/bold green]
Total: [cyan]{total_xp:,} XP[/cyan]
Level: [yellow]{level}[/yellow]

{progress_bar} [dim]{progress:.0%}[/dim]
{xp_to_next_level:,} XP to Level {level + 1}"""

    panel = Panel(
        Align.center(content),
        title="[bold]XP Earned[/bold]",
        border_style="green",
        padding=(1, 2),
    )

    return panel


def create_profile_panel(user_data: dict[str, Any]) -> Panel:
    """
    Create a Rich panel for displaying user profile.

    Args:
        user_data: Dictionary with keys:
            - username, email, level, xp, xp_to_next_level, progress,
              tasks_completed, habits_tracked, focus_sessions, achievements_unlocked

    Returns:
        Rich Panel instance ready for display
    """
    username = user_data.get("username", "Unknown")
    email = user_data.get("email", "")
    level = user_data.get("level", 1)
    xp = user_data.get("xp", 0)
    xp_per_level = user_data.get("xp_per_level", 1000)
    xp_to_next_level = user_data.get("xp_to_next_level", 1000)
    progress = user_data.get("progress", 0.0)

    tasks_completed = user_data.get("tasks_completed", 0)
    habits_tracked = user_data.get("habits_tracked", 0)
    focus_sessions = user_data.get("focus_sessions", 0)
    achievements_unlocked = user_data.get("achievements_unlocked", 0)
    total_achievements = user_data.get("total_achievements", 20)

    progress_bar = _create_progress_bar(progress, width=20)
    next_level_xp = level * xp_per_level

    content = f"""👤 [bold]Username:[/bold] {username}
📧 [bold]Email:[/bold] {email}

⭐ [bold]Level:[/bold] [yellow]{level}[/yellow]
💎 [bold]XP:[/bold] [cyan]{xp:,}[/cyan] / {next_level_xp:,}

{progress_bar} [dim]{progress:.0%}[/dim]
{xp_to_next_level:,} XP to Level {level + 1}

📊 [bold]Statistics:[/bold]
  • Tasks completed: {tasks_completed}
  • Habits tracked: {habits_tracked}
  • Focus sessions: {focus_sessions}
  • Current streaks: {user_data.get('current_streaks', 0)}

🏆 [bold]Achievements:[/bold] {achievements_unlocked}/{total_achievements} unlocked"""

    panel = Panel(
        content,
        title="[bold cyan]Profile[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    )

    return panel


def create_stats_panel(stats_data: dict[str, Any], period: str = "week") -> Panel:
    """
    Create a Rich panel for displaying productivity statistics.

    Args:
        stats_data: Dictionary with statistics:
            - tasks_completed, xp_earned, focus_time, active_habits,
              daily_breakdown, most_productive_day, least_productive_day
        period: Time period (day, week, month)

    Returns:
        Rich Panel instance ready for display
    """
    tasks_completed = stats_data.get("tasks_completed", 0)
    xp_earned = stats_data.get("xp_earned", 0)
    focus_time = stats_data.get("focus_time", 0)
    active_habits = stats_data.get("active_habits", 0)
    daily_breakdown = stats_data.get("daily_breakdown", {})
    most_productive = stats_data.get("most_productive_day", {})
    least_productive = stats_data.get("least_productive_day", {})

    period_title = {
        "day": "Today's",
        "week": "This Week's",
        "month": "This Month's",
    }.get(period, "This Week's")

    content = f"""[bold]Tasks Completed:[/bold] {tasks_completed}
[bold]XP Earned:[/bold] [cyan]{xp_earned:,}[/cyan]
[bold]Focus Time:[/bold] {focus_time} minutes
[bold]Active Habits:[/bold] {active_habits}

[bold]Daily Tasks (Last 7 Days):[/bold]"""

    for day, count in daily_breakdown.items():
        bar = _create_bar_chart_row(
            count, max_count=max(daily_breakdown.values()) if daily_breakdown else 1, width=10
        )
        content += f"\n{day:3} {bar} {count} tasks"

    if most_productive:
        content += f"\n\n[bold]Most Productive:[/bold] {most_productive.get('day', 'N/A')} ({most_productive.get('tasks', 0)} tasks, {most_productive.get('xp', 0)} XP)"

    if least_productive:
        content += f"\n[bold]Least Productive:[/bold] {least_productive.get('day', 'N/A')} ({least_productive.get('tasks', 0)} tasks)"

    panel = Panel(
        content,
        title=f"[bold cyan]{period_title} Productivity[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    )

    return panel


def create_insights_panel(insights_data: dict[str, Any]) -> Panel:
    """
    Create a Rich panel for displaying AI insights.

    Args:
        insights_data: Dictionary with keys:
            - patterns, recommendations, optimal_times

    Returns:
        Rich Panel instance ready for display
    """
    patterns = insights_data.get("patterns", "No patterns detected yet.")
    recommendations = insights_data.get("recommendations", [])
    optimal_times = insights_data.get("optimal_times", {})

    content = f"""📊 [bold]Pattern Analysis:[/bold]
{patterns}

💡 [bold]Recommendations:[/bold]"""

    for i, rec in enumerate(recommendations, 1):
        content += f"\n{i}. {rec}"

    if optimal_times:
        content += "\n\n⏰ [bold]Optimal Work Times:[/bold]"
        for time_period, description in optimal_times.items():
            content += f"\n{time_period}: {description}"

    panel = Panel(
        content,
        title="[bold cyan]🤖 AI Insights[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    )

    return panel


def create_focus_panel(remaining_seconds: int, duration_seconds: int) -> Panel:
    """
    Create a Rich panel for displaying focus timer.

    Args:
        remaining_seconds: Remaining time in seconds
        duration_seconds: Total duration in seconds

    Returns:
        Rich Panel instance ready for display
    """
    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60
    time_display = f"{minutes:02d}:{seconds:02d}"

    progress = (duration_seconds - remaining_seconds) / duration_seconds
    progress_bar = _create_progress_bar(progress, width=20)

    content = f"""[bold cyan]{time_display}[/bold cyan]

{progress_bar} [dim]{progress:.0%}[/dim]

[dim][P] Pause  [S] Stop[/dim]"""

    panel = Panel(
        Align.center(content),
        title="[bold]Focus Session[/bold]",
        border_style="blue",
        padding=(1, 2),
    )

    return panel


def create_completion_message(
    item_type: str, item_name: str, xp_earned: int = 0, extra_info: str = ""
) -> Panel:
    """
    Create a Rich panel for displaying completion messages.

    Args:
        item_type: Type of item completed (task, habit, focus session)
        item_name: Name of the completed item
        xp_earned: XP earned
        extra_info: Additional information to display

    Returns:
        Rich Panel instance ready for display
    """
    content = f"""[bold green]✓ {item_type.title()} completed![/bold green]

[bold]{item_name}[/bold]"""

    if xp_earned > 0:
        content += f"\n\n[cyan]+{xp_earned} XP earned[/cyan]"

    if extra_info:
        content += f"\n\n{extra_info}"

    panel = Panel(
        Align.center(content),
        border_style="green",
        padding=(1, 2),
    )

    return panel


def _create_progress_bar(progress: float, width: int = 20) -> str:
    """
    Create an ASCII progress bar.

    Args:
        progress: Progress percentage (0.0 to 1.0)
        width: Width of the progress bar in characters

    Returns:
        String representation of progress bar with Unicode blocks
    """
    progress = max(0.0, min(1.0, progress))
    filled = int(progress * width)
    empty = width - filled

    bar = "[cyan]" + "█" * filled + "[/cyan]" + "[dim]░[/dim]" * empty
    return f"[{bar}]"


def _create_bar_chart_row(value: int, max_count: int, width: int = 10) -> str:
    """
    Create a single row for a horizontal bar chart.

    Args:
        value: Value to display
        max_count: Maximum value for scaling
        width: Maximum width of the bar

    Returns:
        String representation of the bar
    """
    if max_count == 0:
        return "[dim]░[/dim]" * width

    proportion = value / max_count
    filled = int(proportion * width)
    empty = width - filled

    return "[cyan]█[/cyan]" * filled + "[dim]░[/dim]" * empty


def format_duration(seconds: int) -> str:
    """
    Format a duration in seconds to a human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string (e.g., "1h 23m", "45m", "30s")
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{hours}h {minutes}m"
        return f"{hours}h"


def format_xp(xp: int) -> str:
    """
    Format XP with proper styling.

    Args:
        xp: XP amount

    Returns:
        Formatted XP string with color
    """
    return f"[cyan]+{xp:,} XP[/cyan]"
