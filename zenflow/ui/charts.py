"""UI chart generators for terminal display."""


def generate_habit_calendar(
    completions: list[bool],
    habit_name: str = "Habit",
    current_streak: int = 0,
    longest_streak: int = 0,
) -> str:
    """
    Generate ASCII calendar visualization for habit tracking.

    Args:
        completions: List of booleans for last 30 days (True=completed, False=missed)
        habit_name: Name of the habit to display
        current_streak: Current active streak count
        longest_streak: Longest streak ever achieved

    Returns:
        Formatted calendar string with weekly breakdown and stats

    Example:
        >>> completions = [True] * 7 + [False] + [True] * 6
        >>> print(generate_habit_calendar(completions, "Morning Run", 6, 7))
        Morning Run - Last 30 Days

        Week 1: ✓✓✓✓✓✓✓
        Week 2: ✗✓✓✓✓✓✓
        ...
    """
    # Ensure we have exactly 30 days
    if len(completions) < 30:
        # Pad with False if less than 30 days
        completions = [False] * (30 - len(completions)) + completions
    elif len(completions) > 30:
        # Take only last 30 days
        completions = completions[-30:]

    # Build calendar output
    lines = []
    lines.append(f"{habit_name} - Last 30 Days")
    lines.append("")

    # Group into weeks (7 days each, except last week may be partial)
    week_num = 1
    for i in range(0, len(completions), 7):
        week_data = completions[i : i + 7]
        week_str = "".join("✓" if day else "✗" for day in week_data)
        lines.append(f"Week {week_num}: {week_str}")
        week_num += 1

    # Add empty line before stats
    lines.append("")

    # Calculate completion rate
    total_days = len(completions)
    completed_days = sum(completions)
    completion_rate = (completed_days / total_days * 100) if total_days > 0 else 0

    # Add summary statistics
    lines.append(f"Current Streak: 🔥 {current_streak} days")
    lines.append(f"Longest Streak: 🏆 {longest_streak} days")
    lines.append(f"Completion Rate: {completion_rate:.0f}%")

    return "\n".join(lines)


def generate_bar_chart(data: dict[str, int | float], max_width: int = 20) -> str:
    """
    Generate ASCII bar chart for terminal display.

    Args:
        data: Dictionary mapping labels to values
        max_width: Maximum width of bars in characters

    Returns:
        Formatted bar chart string

    Example:
        >>> data = {"Mon": 4, "Tue": 2, "Wed": 5}
        >>> print(generate_bar_chart(data, 10))
        Mon ████████░░ 4
        Tue ████░░░░░░ 2
        Wed ██████████ 5
    """
    if not data:
        return "No data to display"

    # Find maximum value for scaling
    max_value = max(data.values()) if data else 1

    lines = []
    for label, value in data.items():
        # Calculate bar width proportionally
        if max_value > 0:
            filled = int((value / max_value) * max_width)
        else:
            filled = 0

        empty = max_width - filled

        # Create bar with Unicode block characters
        bar = "█" * filled + "░" * empty

        # Format line with label, bar, and value
        lines.append(f"{label} {bar} {value}")

    return "\n".join(lines)
