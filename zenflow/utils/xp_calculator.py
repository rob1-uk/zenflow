"""XP calculation utilities for ZenFlow gamification system."""

from typing import Any


def calculate_task_xp(priority: str, config: dict[str, Any]) -> int:
    """
    Calculate XP reward for completing a task based on priority.

    Args:
        priority: Task priority level (LOW, MEDIUM, or HIGH)
        config: Configuration dictionary containing gamification.task_xp settings

    Returns:
        XP amount for the task priority

    Raises:
        ValueError: If priority is not valid or config is missing required keys
    """
    priority_normalized = priority.upper()
    valid_priorities = ["LOW", "MEDIUM", "HIGH"]

    if priority_normalized not in valid_priorities:
        raise ValueError(
            f"Invalid priority '{priority}'. Must be one of: {', '.join(valid_priorities)}"
        )

    try:
        task_xp_config = config["gamification"]["task_xp"]
        priority_key = priority_normalized.lower()
        return int(task_xp_config[priority_key])
    except KeyError as e:
        raise ValueError(f"Missing required configuration key: {e}") from e


def calculate_habit_xp(base_xp: int) -> int:
    """
    Calculate XP reward for tracking a habit.

    Args:
        base_xp: Base XP amount for habit tracking (typically a fixed value)

    Returns:
        XP amount for habit tracking

    Raises:
        ValueError: If base_xp is negative
    """
    if base_xp < 0:
        raise ValueError(f"Base XP must be non-negative, got: {base_xp}")

    return base_xp


def calculate_milestone_xp(streak: int, config: dict[str, Any]) -> int:
    """
    Calculate bonus XP for reaching habit streak milestones.

    Args:
        streak: Current habit streak count
        config: Configuration dictionary containing gamification.habit_milestone_xp settings

    Returns:
        Bonus XP if a milestone was reached, 0 otherwise

    Raises:
        ValueError: If config is missing required keys
    """
    try:
        milestone_config = config["gamification"]["habit_milestone_xp"]
    except KeyError as e:
        raise ValueError(f"Missing required configuration key: {e}") from e

    milestone_xp = 0
    for milestone_days, xp_reward in milestone_config.items():
        if streak == int(milestone_days):
            milestone_xp = xp_reward
            break

    return milestone_xp


def calculate_focus_session_xp(config: dict[str, Any]) -> int:
    """
    Calculate XP reward for completing a focus session.

    Args:
        config: Configuration dictionary containing gamification.focus_xp setting

    Returns:
        XP amount for completing a focus session

    Raises:
        ValueError: If config is missing required keys
    """
    try:
        return int(config["gamification"]["focus_xp"])
    except KeyError as e:
        raise ValueError(f"Missing required configuration key: {e}") from e


def calculate_level(total_xp: int, xp_per_level: int) -> int:
    """
    Calculate user level based on total XP.

    Args:
        total_xp: Total XP accumulated by the user
        xp_per_level: XP required per level (default: 1000)

    Returns:
        Current level (minimum 1)

    Raises:
        ValueError: If total_xp is negative or xp_per_level is not positive
    """
    if total_xp < 0:
        raise ValueError(f"Total XP must be non-negative, got: {total_xp}")

    if xp_per_level <= 0:
        raise ValueError(f"XP per level must be positive, got: {xp_per_level}")

    return (total_xp // xp_per_level) + 1


def calculate_xp_to_next_level(current_xp: int, xp_per_level: int) -> int:
    """
    Calculate XP needed to reach the next level.

    Args:
        current_xp: Current total XP
        xp_per_level: XP required per level (default: 1000)

    Returns:
        XP needed to reach next level

    Raises:
        ValueError: If current_xp is negative or xp_per_level is not positive
    """
    if current_xp < 0:
        raise ValueError(f"Current XP must be non-negative, got: {current_xp}")

    if xp_per_level <= 0:
        raise ValueError(f"XP per level must be positive, got: {xp_per_level}")

    xp_in_current_level = current_xp % xp_per_level
    return xp_per_level - xp_in_current_level


def calculate_level_progress(current_xp: int, xp_per_level: int) -> float:
    """
    Calculate progress towards next level as a percentage.

    Args:
        current_xp: Current total XP
        xp_per_level: XP required per level (default: 1000)

    Returns:
        Progress percentage (0.0 to 1.0)

    Raises:
        ValueError: If current_xp is negative or xp_per_level is not positive
    """
    if current_xp < 0:
        raise ValueError(f"Current XP must be non-negative, got: {current_xp}")

    if xp_per_level <= 0:
        raise ValueError(f"XP per level must be positive, got: {xp_per_level}")

    xp_in_current_level = current_xp % xp_per_level
    return xp_in_current_level / xp_per_level
