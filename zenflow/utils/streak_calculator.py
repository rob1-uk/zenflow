"""Streak calculation utilities for habit tracking.

This module provides pure functions for calculating habit streaks based on
completion logs. Supports both daily and weekly habit frequencies.
"""

from datetime import date, datetime, timedelta
from typing import Any


def calculate_streak_from_logs(logs: list[dict[str, Any]], frequency: str, today: date) -> int:
    """Calculate current streak from habit completion logs.

    Args:
        logs: List of habit log dicts with 'completed_at' timestamp strings
        frequency: 'DAILY' or 'WEEKLY'
        today: Reference date for streak calculation (usually today's date)

    Returns:
        Current streak count (days for DAILY, weeks for WEEKLY)

    Examples:
        >>> logs = [{'completed_at': '2026-01-23'}, {'completed_at': '2026-01-22'}]
        >>> calculate_streak_from_logs(logs, 'DAILY', date(2026, 1, 23))
        2
    """
    if not logs:
        return 0

    if frequency == "DAILY":
        return _calculate_daily_streak(logs, today)
    elif frequency == "WEEKLY":
        return _calculate_weekly_streak(logs, today)
    else:
        raise ValueError(f"Invalid frequency: {frequency}. Must be 'DAILY' or 'WEEKLY'")


def _calculate_daily_streak(logs: list[dict[str, Any]], today: date) -> int:
    """Calculate streak for daily habits.

    A daily streak counts consecutive days with at least one completion.
    The streak breaks if there's a gap of more than 1 day.

    Args:
        logs: List of habit log dicts with 'completed_at' timestamp strings
        today: Reference date for streak calculation

    Returns:
        Number of consecutive days with completions
    """
    # Parse and convert all completion dates
    completion_dates = set()
    for log in logs:
        # Handle both dict and sqlite3.Row objects
        completed_at = log["completed_at"] if "completed_at" in log else None
        if completed_at:
            # Handle both datetime strings and date strings
            if isinstance(completed_at, str):
                # Try parsing as datetime first, then as date
                try:
                    dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                    completion_dates.add(dt.date())
                except ValueError:
                    # Try parsing as date only
                    completion_dates.add(date.fromisoformat(completed_at))
            elif isinstance(completed_at, datetime):
                completion_dates.add(completed_at.date())
            elif isinstance(completed_at, date):
                completion_dates.add(completed_at)

    if not completion_dates:
        return 0

    # Find the most recent completion date
    most_recent = max(completion_dates)

    # Check if the streak is still active
    # A streak is active if the last completion was today or yesterday
    days_since_last = (today - most_recent).days
    if days_since_last > 1:
        return 0  # Streak broken

    # Count consecutive days backward from most recent
    streak = 0
    current_date = most_recent

    while current_date in completion_dates:
        streak += 1
        current_date -= timedelta(days=1)

    return streak


def _calculate_weekly_streak(logs: list[dict[str, Any]], today: date) -> int:
    """Calculate streak for weekly habits.

    A weekly streak counts consecutive weeks with at least one completion.
    Uses ISO week numbering (Monday is first day of week).

    Args:
        logs: List of habit log dicts with 'completed_at' timestamp strings
        today: Reference date for streak calculation

    Returns:
        Number of consecutive weeks with at least one completion
    """
    # Parse and get ISO week numbers for all completions
    completion_weeks = set()
    for log in logs:
        # Handle both dict and sqlite3.Row objects
        completed_at = log["completed_at"] if "completed_at" in log else None
        if completed_at:
            # Handle both datetime strings and date strings
            if isinstance(completed_at, str):
                try:
                    dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                    completion_date = dt.date()
                except ValueError:
                    completion_date = date.fromisoformat(completed_at)
            elif isinstance(completed_at, datetime):
                completion_date = completed_at.date()
            elif isinstance(completed_at, date):
                completion_date = completed_at
            else:
                continue

            # Get ISO calendar (year, week_number, weekday)
            iso_year, iso_week, _ = completion_date.isocalendar()
            completion_weeks.add((iso_year, iso_week))

    if not completion_weeks:
        return 0

    # Get current week
    current_year, current_week, _ = today.isocalendar()
    current_week_tuple = (current_year, current_week)

    # Check if the streak is still active
    # A streak is active if there's a completion in the current or previous week
    if current_week_tuple not in completion_weeks:
        # Check previous week
        previous_week_date = today - timedelta(weeks=1)
        prev_year, prev_week, _ = previous_week_date.isocalendar()
        if (prev_year, prev_week) not in completion_weeks:
            return 0  # Streak broken

    # Start from the most recent week with a completion
    if current_week_tuple in completion_weeks:
        streak_year, streak_week = current_week_tuple
    else:
        # Start from previous week
        previous_week_date = today - timedelta(weeks=1)
        streak_year, streak_week, _ = previous_week_date.isocalendar()

    # Count consecutive weeks backward
    streak = 0
    check_week = (streak_year, streak_week)

    while check_week in completion_weeks:
        streak += 1

        # Move to previous week
        # Create a date in the current week and subtract 7 days
        # Find a date in the week we're checking
        # Use a simple approach: go back 7 days at a time
        temp_date = date.fromisocalendar(check_week[0], check_week[1], 1)
        temp_date -= timedelta(weeks=1)
        check_week = (temp_date.isocalendar()[0], temp_date.isocalendar()[1])

    return streak
