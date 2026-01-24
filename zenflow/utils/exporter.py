"""Data export functionality for ZenFlow.

This module provides functions to export data from the ZenFlow database
in various formats (CSV, JSON, TXT) for backup and external analysis.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from zenflow.database.db import Database


def export_data(
    export_type: str,
    format: str,
    output_path: str,
    db: Database,
    user_id: int,
    start_date: str | None = None,
    end_date: str | None = None,
) -> None:
    """Export data from database to file in specified format.

    Args:
        export_type: Type of data to export ('tasks', 'habits', 'stats', 'all')
        format: Output format ('csv', 'json', 'txt')
        output_path: Path to output file
        db: Database connection
        user_id: ID of user whose data to export
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)

    Raises:
        ValueError: If invalid export_type or format
        IOError: If file cannot be written
    """
    valid_types = ["tasks", "habits", "stats", "achievements", "focus", "all"]
    valid_formats = ["csv", "json", "txt"]

    if export_type not in valid_types:
        raise ValueError(
            f"Invalid export type '{export_type}'. " f"Must be one of: {', '.join(valid_types)}"
        )

    if format not in valid_formats:
        raise ValueError(
            f"Invalid format '{format}'. " f"Must be one of: {', '.join(valid_formats)}"
        )

    output_file = Path(output_path)

    if export_type == "all":
        _export_all(db, user_id, format, output_file, start_date, end_date)
    elif export_type == "tasks":
        data = _get_tasks(db, user_id, start_date, end_date)
        _write_data(data, format, output_file, "tasks")
    elif export_type == "habits":
        data = _get_habits(db, user_id, start_date, end_date)
        _write_data(data, format, output_file, "habits")
    elif export_type == "stats":
        data = _get_stats(db, user_id, start_date, end_date)
        _write_data(data, format, output_file, "stats")
    elif export_type == "achievements":
        data = _get_achievements(db, user_id, start_date, end_date)
        _write_data(data, format, output_file, "achievements")
    elif export_type == "focus":
        data = _get_focus_sessions(db, user_id, start_date, end_date)
        _write_data(data, format, output_file, "focus_sessions")


def _export_all(
    db: Database,
    user_id: int,
    format: str,
    output_file: Path,
    start_date: str | None,
    end_date: str | None,
) -> None:
    """Export all data types to a single file or multiple files.

    For JSON format, creates a single file with all data.
    For CSV/TXT, creates separate files with suffixes.
    """
    if format == "json":
        all_data = {
            "tasks": _get_tasks(db, user_id, start_date, end_date),
            "habits": _get_habits(db, user_id, start_date, end_date),
            "achievements": _get_achievements(db, user_id, start_date, end_date),
            "focus_sessions": _get_focus_sessions(db, user_id, start_date, end_date),
            "daily_stats": _get_stats(db, user_id, start_date, end_date),
        }
        _write_json(all_data, output_file)
    else:
        stem = output_file.stem
        suffix = output_file.suffix

        tasks = _get_tasks(db, user_id, start_date, end_date)
        tasks_file = output_file.parent / f"{stem}_tasks{suffix}"
        _write_data(tasks, format, tasks_file, "tasks")

        habits = _get_habits(db, user_id, start_date, end_date)
        habits_file = output_file.parent / f"{stem}_habits{suffix}"
        _write_data(habits, format, habits_file, "habits")

        achievements = _get_achievements(db, user_id, start_date, end_date)
        achievements_file = output_file.parent / f"{stem}_achievements{suffix}"
        _write_data(achievements, format, achievements_file, "achievements")

        focus = _get_focus_sessions(db, user_id, start_date, end_date)
        focus_file = output_file.parent / f"{stem}_focus{suffix}"
        _write_data(focus, format, focus_file, "focus_sessions")

        stats = _get_stats(db, user_id, start_date, end_date)
        stats_file = output_file.parent / f"{stem}_stats{suffix}"
        _write_data(stats, format, stats_file, "daily_stats")


def _get_tasks(
    db: Database,
    user_id: int,
    start_date: str | None,
    end_date: str | None,
) -> list[dict[str, Any]]:
    """Fetch tasks from database with optional date filtering."""
    query = """
        SELECT id, title, description, priority, status,
               due_date, completed_at, xp_reward, created_at
        FROM tasks
        WHERE user_id = ?
    """
    params: list[Any] = [user_id]

    if start_date:
        query += " AND created_at >= ?"
        params.append(start_date)

    if end_date:
        query += " AND created_at <= ?"
        params.append(end_date)

    query += " ORDER BY created_at DESC"

    rows = db.fetch_all(query, tuple(params))
    return [dict(row) for row in rows]


def _get_habits(
    db: Database,
    user_id: int,
    start_date: str | None,
    end_date: str | None,
) -> list[dict[str, Any]]:
    """Fetch habits from database with optional date filtering."""
    query = """
        SELECT id, name, frequency, streak, longest_streak,
               last_completed, target_days, created_at
        FROM habits
        WHERE user_id = ?
    """
    params: list[Any] = [user_id]

    if start_date:
        query += " AND created_at >= ?"
        params.append(start_date)

    if end_date:
        query += " AND created_at <= ?"
        params.append(end_date)

    query += " ORDER BY created_at DESC"

    rows = db.fetch_all(query, tuple(params))
    return [dict(row) for row in rows]


def _get_achievements(
    db: Database,
    user_id: int,
    start_date: str | None,
    end_date: str | None,
) -> list[dict[str, Any]]:
    """Fetch achievements from database with optional date filtering."""
    query = """
        SELECT id, achievement_type, title, description,
               xp_earned, unlocked_at
        FROM achievements
        WHERE user_id = ?
    """
    params: list[Any] = [user_id]

    if start_date:
        query += " AND unlocked_at >= ?"
        params.append(start_date)

    if end_date:
        query += " AND unlocked_at <= ?"
        params.append(end_date)

    query += " ORDER BY unlocked_at DESC"

    rows = db.fetch_all(query, tuple(params))
    return [dict(row) for row in rows]


def _get_focus_sessions(
    db: Database,
    user_id: int,
    start_date: str | None,
    end_date: str | None,
) -> list[dict[str, Any]]:
    """Fetch focus sessions from database with optional date filtering."""
    query = """
        SELECT id, duration_minutes, completed,
               started_at, completed_at
        FROM focus_sessions
        WHERE user_id = ?
    """
    params: list[Any] = [user_id]

    if start_date:
        query += " AND started_at >= ?"
        params.append(start_date)

    if end_date:
        query += " AND started_at <= ?"
        params.append(end_date)

    query += " ORDER BY started_at DESC"

    rows = db.fetch_all(query, tuple(params))
    return [dict(row) for row in rows]


def _get_stats(
    db: Database,
    user_id: int,
    start_date: str | None,
    end_date: str | None,
) -> list[dict[str, Any]]:
    """Fetch daily stats from database with optional date filtering."""
    query = """
        SELECT id, date, tasks_completed, xp_earned, focus_minutes
        FROM daily_stats
        WHERE user_id = ?
    """
    params: list[Any] = [user_id]

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date DESC"

    rows = db.fetch_all(query, tuple(params))
    return [dict(row) for row in rows]


def _write_data(
    data: list[dict[str, Any]],
    format: str,
    output_file: Path,
    data_type: str,
) -> None:
    """Write data to file in specified format.

    Args:
        data: List of dictionaries to export
        format: Output format ('csv', 'json', 'txt')
        output_file: Path to output file
        data_type: Type of data for labeling
    """
    if format == "json":
        _write_json(data, output_file)
    elif format == "csv":
        _write_csv(data, output_file)
    elif format == "txt":
        _write_txt(data, output_file, data_type)


def _write_json(data: Any, output_file: Path) -> None:
    """Write data to JSON file with pretty printing."""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def _write_csv(data: list[dict[str, Any]], output_file: Path) -> None:
    """Write data to CSV file."""
    if not data:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("")
        return

    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)


def _write_txt(
    data: list[dict[str, Any]],
    output_file: Path,
    data_type: str,
) -> None:
    """Write data to human-readable text file."""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"ZenFlow {data_type.title()} Export\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total records: {len(data)}\n")
        f.write("=" * 80 + "\n\n")

        if not data:
            f.write("No data to export.\n")
            return

        for i, record in enumerate(data, 1):
            f.write(f"Record {i}:\n")
            f.write("-" * 40 + "\n")
            for key, value in record.items():
                f.write(f"  {key}: {value}\n")
            f.write("\n")
