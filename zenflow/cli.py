"""CLI command definitions for ZenFlow.

This module defines all Click commands for the ZenFlow CLI application,
including user initialization, task management, habit tracking, and more.
"""

import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from zenflow import __version__
from zenflow.ai.insights import OPENAI_AVAILABLE, AIInsightsEngine
from zenflow.core.focus_timer import FocusTimer
from zenflow.core.gamification import ACHIEVEMENT_DEFINITIONS, GamificationEngine
from zenflow.core.habit_tracker import HabitTracker
from zenflow.core.task_manager import TaskManager
from zenflow.database.db import Database
from zenflow.ui.charts import generate_habit_calendar
from zenflow.ui.formatters import (
    create_focus_panel,
    create_profile_panel,
    create_stats_panel,
    create_xp_panel,
)
from zenflow.ui.tables import create_achievement_table, create_habit_table, create_task_table
from zenflow.utils.config_loader import load_config, load_env
from zenflow.utils.exceptions import (
    APIError,
    ConfigurationError,
    DatabaseError,
    ValidationError,
)
from zenflow.utils.exporter import export_data
from zenflow.utils.logger import get_logger, setup_logger
from zenflow.utils.streak_calculator import calculate_streak_from_logs
from zenflow.utils.xp_calculator import (
    calculate_level_progress,
    calculate_task_xp,
    calculate_xp_to_next_level,
)

console = Console()


def get_database(config: dict[str, Any]) -> Database:
    """Get database instance from configuration.

    Args:
        config: Configuration dictionary with database settings

    Returns:
        Connected Database instance
    """
    db_path = config["database"]["path"]
    db = Database(db_path)
    db.connect()
    return db


def get_current_user(db: Database) -> dict[str, Any] | None:
    """Get the current user from the database.

    Args:
        db: Database instance

    Returns:
        User dictionary or None if not found
    """
    user = db.fetch_one("SELECT * FROM users ORDER BY id LIMIT 1")
    return dict(user) if user else None


def ensure_user_exists(db: Database) -> dict[str, Any]:
    """Ensure a user exists in the database.

    Args:
        db: Database instance

    Returns:
        User dictionary

    Raises:
        SystemExit: If no user found
    """
    user = get_current_user(db)
    if not user:
        console.print("[red]No user profile found. Please run 'zenflow init' first.[/red]")
        sys.exit(1)
    return user


@click.group()
@click.version_option(version=__version__, prog_name="zenflow")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """ZenFlow - CLI productivity tool with task management, habit tracking, and gamification.

    A beautiful command-line tool to boost your productivity with tasks, habits,
    focus sessions, and an engaging gamification system.
    """
    load_env()
    ctx.ensure_object(dict)
    try:
        ctx.obj["config"] = load_config()
        logger = setup_logger(ctx.obj["config"])
        ctx.obj["logger"] = logger
        logger.debug("ZenFlow CLI initialized")
    except ConfigurationError as e:
        console.print(
            Panel.fit(
                f"[bold red]Configuration Error[/bold red]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Check that config.yaml exists and is valid.[/dim]",
                border_style="red",
            )
        )
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected initialization error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--username",
    prompt="Username",
    help="Your username for ZenFlow",
)
@click.option(
    "--email",
    prompt="Email",
    help="Your email address",
)
@click.pass_context
def init(ctx: click.Context, username: str, email: str) -> None:
    """Initialize user profile and database.

    Creates the database, initializes all tables, and sets up your user profile.
    This command should be run once when you first start using ZenFlow.
    """
    config = ctx.obj["config"]
    logger = ctx.obj.get("logger") or get_logger()

    logger.info("Starting initialization for user: %s", username)

    console.print(
        Panel.fit(
            "[bold cyan]Welcome to ZenFlow![/bold cyan]\n" "Your productivity companion",
            border_style="cyan",
        )
    )

    db_path = config["database"]["path"]

    if Path(db_path).exists():
        logger.warning("Database already exists at: %s", db_path)
        overwrite = click.confirm(
            f"\nDatabase '{db_path}' already exists. Overwrite?",
            default=False,
        )
        if not overwrite:
            logger.info("Initialization cancelled by user")
            console.print("[yellow]Initialization cancelled.[/yellow]")
            return
        Path(db_path).unlink()
        logger.info("Existing database deleted")

    try:
        with Database(db_path) as db:
            console.print("[cyan]Creating database schema...[/cyan]")
            logger.info("Initializing database schema at: %s", db_path)
            db.initialize_schema()

            console.print("[cyan]Creating user profile...[/cyan]")
            now = datetime.now()
            logger.debug("Creating user profile: username=%s, email=%s", username, email)
            db.execute(
                """
                INSERT INTO users (username, email, level, xp, created_at)
                VALUES (?, ?, 1, 0, ?)
                """,
                (username, email, now),
            )
            db.commit()
            logger.info("User profile created successfully for: %s", username)

            console.print(
                Panel.fit(
                    f"[bold green]✓ Profile created![/bold green]\n\n"
                    f"[bold]Username:[/bold] {username}\n"
                    f"[bold]Email:[/bold] {email}\n"
                    f"[bold]Level:[/bold] 1\n"
                    f"[bold]XP:[/bold] 0",
                    border_style="green",
                    title="[bold]Profile Created[/bold]",
                )
            )

            console.print(
                "\n[dim]Get started with:[/dim]\n"
                '  [cyan]zenflow task add[/cyan] "Your first task" --priority HIGH\n'
                '  [cyan]zenflow habit add[/cyan] "Morning exercise" --frequency DAILY\n'
                "  [cyan]zenflow focus start[/cyan]\n"
            )

    except DatabaseError as e:
        logger.error("Database initialization failed: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Database Error[/bold red]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Failed to create or initialize the database.\n"
                f"Check file permissions and disk space.[/dim]",
                border_style="red",
            )
        )
        sys.exit(1)
    except ValidationError as e:
        logger.error("Validation error during init: %s", str(e))
        console.print(
            Panel.fit(
                f"[bold yellow]Invalid Input[/bold yellow]\n\n" f"{str(e)}",
                border_style="yellow",
            )
        )
        sys.exit(1)
    except Exception as e:
        logger.error("Initialization failed: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Unexpected Error[/bold red]\n\n"
                f"{str(e)}\n\n"
                f"[dim]An unexpected error occurred during initialization.[/dim]",
                border_style="red",
            )
        )
        sys.exit(1)


@cli.group()
def task() -> None:
    """Manage tasks: create, list, complete, update, and delete."""
    pass


@task.command("add")
@click.argument("title")
@click.option("--description", "-d", help="Task description")
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["LOW", "MEDIUM", "HIGH"], case_sensitive=False),
    default="MEDIUM",
    help="Task priority (default: MEDIUM)",
)
@click.option("--due", help="Due date (YYYY-MM-DD format)")
@click.pass_context
def task_add(
    ctx: click.Context,
    title: str,
    description: str | None,
    priority: str,
    due: str | None,
) -> None:
    """Create a new task.

    Example:
        zenflow task add "Write documentation" --priority HIGH --due 2026-01-30
    """
    config = ctx.obj["config"]
    logger = ctx.obj.get("logger") or get_logger()

    try:
        with get_database(config) as db:
            user = ensure_user_exists(db)

            due_date = None
            if due:
                try:
                    due_date = datetime.strptime(due, "%Y-%m-%d")
                except ValueError:
                    console.print("[red]Invalid date format. Use YYYY-MM-DD[/red]")
                    return

            tm = TaskManager(db, calculate_task_xp, config)
            task_data = tm.create_task(
                user["id"],
                title,
                description,
                priority.upper(),
                due_date,
            )

            logger.info("Task created: %s (ID: %d, Priority: %s)", title, task_data["id"], priority)

            console.print("[green]✓ Task created![/green]")
            console.print(
                Panel.fit(
                    f"[bold]New Task Added[/bold]\n\n"
                    f"[bold]ID:[/bold] {task_data['id']}\n"
                    f"[bold]Title:[/bold] {title}\n"
                    f"[bold]Priority:[/bold] {priority.upper()}\n"
                    f"[bold]Reward:[/bold] [cyan]+{task_data['xp_reward']} XP[/cyan]",
                    border_style="green",
                )
            )
            console.print(f"\n[dim]Complete it with:[/dim] zenflow task complete {task_data['id']}")

    except ValidationError as e:
        logger.error("Task validation failed: %s", str(e))
        console.print(
            Panel.fit(
                f"[bold yellow]Invalid Task Data[/bold yellow]\n\n{str(e)}",
                border_style="yellow",
            )
        )
        sys.exit(1)
    except DatabaseError as e:
        logger.error("Database error during task creation: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Database Error[/bold red]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Failed to save task to database.[/dim]",
                border_style="red",
            )
        )
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error creating task: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Unexpected Error[/bold red]\n\n{str(e)}",
                border_style="red",
            )
        )
        sys.exit(1)


@task.command("list")
@click.option(
    "--status",
    "-s",
    type=click.Choice(["TODO", "IN_PROGRESS", "DONE"], case_sensitive=False),
    help="Filter by status",
)
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["LOW", "MEDIUM", "HIGH"], case_sensitive=False),
    help="Filter by priority",
)
@click.option(
    "--all",
    "-a",
    "show_all",
    is_flag=True,
    help="Show all tasks including completed",
)
@click.pass_context
def task_list(
    ctx: click.Context,
    status: str | None,
    priority: str | None,
    show_all: bool,
) -> None:
    """List tasks with optional filtering.

    Example:
        zenflow task list --status TODO --priority HIGH
    """
    config = ctx.obj["config"]
    logger = ctx.obj.get("logger") or get_logger()

    try:
        with get_database(config) as db:
            user = ensure_user_exists(db)

            tm = TaskManager(db, calculate_task_xp, config)
            tasks = tm.list_tasks(
                user["id"],
                status=status.upper() if status else None,
                priority=priority.upper() if priority else None,
                include_completed=show_all or status == "DONE",
            )

            logger.debug("Listing tasks: %d found", len(tasks))

            table = create_task_table(tasks)
            console.print(table)

            if tasks:
                total_xp = sum(t["xp_reward"] for t in tasks if t["status"] != "DONE")
                console.print(f"\n[dim]Total pending XP:[/dim] [cyan]{total_xp} XP[/cyan]")

    except DatabaseError as e:
        logger.error("Database error during task list: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Database Error[/bold red]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Failed to retrieve tasks from database.[/dim]",
                border_style="red",
            )
        )
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error listing tasks: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Unexpected Error[/bold red]\n\n{str(e)}",
                border_style="red",
            )
        )
        sys.exit(1)


@task.command("complete")
@click.argument("task_id", type=int)
@click.pass_context
def task_complete(ctx: click.Context, task_id: int) -> None:
    """Mark a task as complete and earn XP.

    Example:
        zenflow task complete 1
    """
    config = ctx.obj["config"]
    logger = ctx.obj.get("logger") or get_logger()

    try:
        with get_database(config) as db:
            user = ensure_user_exists(db)

            # Initialize gamification engine and task manager
            gamification = GamificationEngine(db, config)
            tm = TaskManager(db, calculate_task_xp, config, gamification)

            # Complete task (this will award XP and check achievements)
            result = tm.complete_task(user["id"], task_id)

            logger.info(
                "Task completed: ID=%d, XP earned=%d",
                task_id,
                result["xp_earned"],
            )

            console.print("[green]✓ Task completed![/green]\n")

            # Display XP panel if gamification data is available
            if "xp_data" in result:
                xp_data = result["xp_data"]
                xp_panel = create_xp_panel(
                    {
                        "xp_earned": xp_data["xp_awarded"],
                        "total_xp": xp_data["total_xp"],
                        "level": xp_data["new_level"],
                        "xp_to_next_level": xp_data["xp_to_next"],
                        "progress": xp_data["progress"],
                    }
                )
                console.print(xp_panel)

                # Show level up message
                if xp_data["level_up"]:
                    console.print(
                        f"\n[bold yellow]🎉 Level Up! You're now Level {xp_data['new_level']}![/bold yellow]"
                    )

            # Display newly unlocked achievements
            if "achievements" in result and result["achievements"]:
                console.print("\n[bold cyan]🏆 New Achievements Unlocked![/bold cyan]\n")
                for achievement in result["achievements"]:
                    console.print(
                        Panel.fit(
                            f"[bold yellow]{achievement['title']}[/bold yellow]\n"
                            f"{achievement['description']}\n"
                            f"[cyan]+{achievement['xp_earned']} XP[/cyan]",
                            border_style="yellow",
                        )
                    )

    except ValidationError as e:
        logger.error("Task validation failed: %s", str(e))
        console.print(
            Panel.fit(
                f"[bold yellow]Invalid Task[/bold yellow]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Task ID {task_id} may not exist or is invalid.[/dim]",
                border_style="yellow",
            )
        )
        sys.exit(1)
    except DatabaseError as e:
        logger.error("Database error during task completion: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Database Error[/bold red]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Failed to update task in database.[/dim]",
                border_style="red",
            )
        )
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error completing task: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Unexpected Error[/bold red]\n\n{str(e)}",
                border_style="red",
            )
        )
        sys.exit(1)


@task.command("update")
@click.argument("task_id", type=int)
@click.option("--title", "-t", help="New title")
@click.option("--description", "-d", help="New description")
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["LOW", "MEDIUM", "HIGH"], case_sensitive=False),
    help="New priority",
)
@click.option("--due", help="New due date (YYYY-MM-DD format)")
@click.option(
    "--status",
    "-s",
    type=click.Choice(["TODO", "IN_PROGRESS", "DONE"], case_sensitive=False),
    help="New status",
)
@click.pass_context
def task_update(
    ctx: click.Context,
    task_id: int,
    title: str | None,
    description: str | None,
    priority: str | None,
    due: str | None,
    status: str | None,
) -> None:
    """Update task details.

    Example:
        zenflow task update 1 --priority HIGH --status IN_PROGRESS
    """
    config = ctx.obj["config"]
    logger = ctx.obj.get("logger") or get_logger()

    if not any([title, description, priority, due, status]):
        console.print("[yellow]No updates specified. Use --help for options.[/yellow]")
        return

    try:
        with get_database(config) as db:
            user = ensure_user_exists(db)

            due_date = None
            if due:
                try:
                    due_date = datetime.strptime(due, "%Y-%m-%d")
                except ValueError:
                    console.print("[red]Invalid date format. Use YYYY-MM-DD[/red]")
                    return

            tm = TaskManager(db, calculate_task_xp, config)
            updated_task = tm.update_task(
                user["id"],
                task_id,
                title=title,
                description=description,
                priority=priority.upper() if priority else None,
                due_date=due_date,
                status=status.upper() if status else None,
            )

            logger.info("Task updated: ID=%d", task_id)

            console.print(f"[green]✓ Task {task_id} updated successfully![/green]")
            console.print(
                Panel.fit(
                    f"[bold]Title:[/bold] {updated_task['title']}\n"
                    f"[bold]Priority:[/bold] {updated_task['priority']}\n"
                    f"[bold]Status:[/bold] {updated_task['status']}\n"
                    f"[bold]XP Reward:[/bold] [cyan]+{updated_task['xp_reward']} XP[/cyan]",
                    border_style="cyan",
                    title="[bold]Updated Task[/bold]",
                )
            )

    except ValidationError as e:
        logger.error("Task validation failed: %s", str(e))
        console.print(
            Panel.fit(
                f"[bold yellow]Invalid Task Data[/bold yellow]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Check task ID and input values.[/dim]",
                border_style="yellow",
            )
        )
        sys.exit(1)
    except DatabaseError as e:
        logger.error("Database error during task update: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Database Error[/bold red]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Failed to update task in database.[/dim]",
                border_style="red",
            )
        )
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error updating task: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Unexpected Error[/bold red]\n\n{str(e)}",
                border_style="red",
            )
        )
        sys.exit(1)


@task.command("delete")
@click.argument("task_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.pass_context
def task_delete(ctx: click.Context, task_id: int, yes: bool) -> None:
    """Delete a task.

    Example:
        zenflow task delete 1
    """
    config = ctx.obj["config"]
    logger = ctx.obj.get("logger") or get_logger()

    try:
        with get_database(config) as db:
            user = ensure_user_exists(db)

            if not yes:
                if not click.confirm(f"Are you sure you want to delete task {task_id}?"):
                    console.print("[yellow]Deletion cancelled.[/yellow]")
                    return

            tm = TaskManager(db, calculate_task_xp, config)
            tm.delete_task(user["id"], task_id)

            logger.info("Task deleted: ID=%d", task_id)

            console.print(f"[green]✓ Task {task_id} deleted successfully![/green]")

    except ValidationError as e:
        logger.error("Task validation failed: %s", str(e))
        console.print(
            Panel.fit(
                f"[bold yellow]Invalid Task[/bold yellow]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Task ID {task_id} may not exist or you don't have permission.[/dim]",
                border_style="yellow",
            )
        )
        sys.exit(1)
    except DatabaseError as e:
        logger.error("Database error during task deletion: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Database Error[/bold red]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Failed to delete task from database.[/dim]",
                border_style="red",
            )
        )
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error deleting task: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Unexpected Error[/bold red]\n\n{str(e)}",
                border_style="red",
            )
        )
        sys.exit(1)


@cli.group()
def habit() -> None:
    """Manage habits: create, track, view streaks, and delete."""
    pass


@habit.command("add")
@click.argument("name")
@click.option(
    "--frequency",
    "-f",
    type=click.Choice(["DAILY", "WEEKLY"], case_sensitive=False),
    default="DAILY",
    help="Habit frequency (default: DAILY)",
)
@click.option("--target", "-t", type=int, help="Target streak goal (optional)")
@click.pass_context
def habit_add(
    ctx: click.Context,
    name: str,
    frequency: str,
    target: int | None,
) -> None:
    """Create a new habit.

    Example:
        zenflow habit add "Morning exercise" --frequency DAILY --target 30
    """
    config = ctx.obj["config"]
    logger = ctx.obj.get("logger") or get_logger()

    try:
        with get_database(config) as db:
            user = ensure_user_exists(db)

            ht = HabitTracker(db, calculate_streak_from_logs, config)
            habit_data = ht.create_habit(
                user["id"],
                name,
                frequency.upper(),
                target,
            )

            logger.info(
                "Habit created: %s (ID: %d, Frequency: %s)", name, habit_data["id"], frequency
            )

            console.print("[green]✓ Habit created![/green]")
            console.print(
                Panel.fit(
                    f"[bold]New Habit Added[/bold]\n\n"
                    f"[bold]ID:[/bold] {habit_data['id']}\n"
                    f"[bold]Name:[/bold] {name}\n"
                    f"[bold]Frequency:[/bold] {frequency.upper()}"
                    + (f"\n[bold]Target:[/bold] {target} days" if target else ""),
                    border_style="green",
                )
            )
            console.print(f"\n[dim]Track it with:[/dim] zenflow habit track {habit_data['id']}")

    except ValidationError as e:
        logger.error("Habit validation failed: %s", str(e))
        console.print(
            Panel.fit(
                f"[bold yellow]Invalid Habit Data[/bold yellow]\n\n{str(e)}",
                border_style="yellow",
            )
        )
        sys.exit(1)
    except DatabaseError as e:
        logger.error("Database error during habit creation: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Database Error[/bold red]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Failed to save habit to database.[/dim]",
                border_style="red",
            )
        )
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error creating habit: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Unexpected Error[/bold red]\n\n{str(e)}",
                border_style="red",
            )
        )
        sys.exit(1)


@habit.command("list")
@click.option(
    "--frequency",
    "-f",
    type=click.Choice(["DAILY", "WEEKLY"], case_sensitive=False),
    help="Filter by frequency",
)
@click.option(
    "--active",
    "-a",
    is_flag=True,
    help="Show only habits with active streaks",
)
@click.pass_context
def habit_list(
    ctx: click.Context,
    frequency: str | None,
    active: bool,
) -> None:
    """List habits with optional filtering.

    Example:
        zenflow habit list --frequency DAILY --active
    """
    config = ctx.obj["config"]
    logger = ctx.obj.get("logger") or get_logger()

    try:
        with get_database(config) as db:
            user = ensure_user_exists(db)

            ht = HabitTracker(db, calculate_streak_from_logs, config)
            habits = ht.list_habits(
                user["id"],
                frequency=frequency.upper() if frequency else None,
                active_only=active,
            )

            logger.debug("Listing habits: %d found", len(habits))

            table = create_habit_table(habits)
            console.print(table)

            if habits:
                active_count = sum(1 for h in habits if h.get("streak", 0) > 0)
                console.print(
                    f"\n[dim]Active streaks:[/dim] [cyan]{active_count}/{len(habits)}[/cyan]"
                )

    except DatabaseError as e:
        logger.error("Database error during habit list: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Database Error[/bold red]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Failed to retrieve habits from database.[/dim]",
                border_style="red",
            )
        )
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error listing habits: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Unexpected Error[/bold red]\n\n{str(e)}",
                border_style="red",
            )
        )
        sys.exit(1)


@habit.command("track")
@click.argument("habit_id", type=int)
@click.pass_context
def habit_track(ctx: click.Context, habit_id: int) -> None:
    """Mark a habit as completed for today.

    Example:
        zenflow habit track 1
    """
    config = ctx.obj["config"]
    logger = ctx.obj.get("logger") or get_logger()

    try:
        with get_database(config) as db:
            user = ensure_user_exists(db)

            # Initialize gamification engine and habit tracker
            gamification = GamificationEngine(db, config)
            ht = HabitTracker(db, calculate_streak_from_logs, config, gamification)

            # Track habit (this will award XP and check achievements)
            result = ht.track_habit(user["id"], habit_id)

            logger.info(
                "Habit tracked: ID=%d, Streak=%d, XP earned=%d",
                habit_id,
                result["streak"],
                result["xp_earned"],
            )

            console.print("[green]✓ Habit tracked![/green]\n")

            # Display streak info
            streak = result["streak"]
            longest_streak = result["longest_streak"]

            console.print(
                Panel.fit(
                    f"[bold yellow]🔥 Streak: {streak} days[/bold yellow]\n"
                    f"[bold]🏆 Longest: {longest_streak} days[/bold]\n"
                    f"[cyan]+{result['xp_earned']} XP earned[/cyan]",
                    border_style="yellow",
                    title="[bold]Streak Info[/bold]",
                )
            )

            # Show milestone message
            if result.get("milestone_reached"):
                console.print(
                    f"\n[bold green]🎉 Milestone reached![/bold green]\n"
                    f"[yellow]{streak}-day streak[/yellow] [cyan]+{result['milestone_xp']} bonus XP[/cyan]"
                )

            # Display XP panel if gamification data is available
            if "xp_data" in result:
                xp_data = result["xp_data"]
                console.print()  # Empty line
                xp_panel = create_xp_panel(
                    {
                        "xp_earned": xp_data["xp_awarded"],
                        "total_xp": xp_data["total_xp"],
                        "level": xp_data["new_level"],
                        "xp_to_next_level": xp_data["xp_to_next"],
                        "progress": xp_data["progress"],
                    }
                )
                console.print(xp_panel)

                # Show level up message
                if xp_data["level_up"]:
                    console.print(
                        f"\n[bold yellow]🎉 Level Up! You're now Level {xp_data['new_level']}![/bold yellow]"
                    )

            # Display newly unlocked achievements
            if "achievements" in result and result["achievements"]:
                console.print("\n[bold cyan]🏆 New Achievements Unlocked![/bold cyan]\n")
                for achievement in result["achievements"]:
                    console.print(
                        Panel.fit(
                            f"[bold yellow]{achievement['title']}[/bold yellow]\n"
                            f"{achievement['description']}\n"
                            f"[cyan]+{achievement['xp_earned']} XP[/cyan]",
                            border_style="yellow",
                        )
                    )

    except ValidationError as e:
        logger.error("Habit validation failed: %s", str(e))
        console.print(
            Panel.fit(
                f"[bold yellow]Invalid Habit[/bold yellow]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Habit ID {habit_id} may not exist or already tracked today.[/dim]",
                border_style="yellow",
            )
        )
        sys.exit(1)
    except DatabaseError as e:
        logger.error("Database error during habit tracking: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Database Error[/bold red]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Failed to save habit tracking to database.[/dim]",
                border_style="red",
            )
        )
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error tracking habit: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Unexpected Error[/bold red]\n\n{str(e)}",
                border_style="red",
            )
        )
        sys.exit(1)


@habit.command("calendar")
@click.argument("habit_id", type=int)
@click.option(
    "--days",
    "-d",
    type=int,
    default=30,
    help="Number of days to show (default: 30)",
)
@click.pass_context
def habit_calendar(ctx: click.Context, habit_id: int, days: int) -> None:
    """Show habit completion calendar (ASCII visualization).

    Example:
        zenflow habit calendar 1 --days 30
    """
    config = ctx.obj["config"]
    logger = ctx.obj.get("logger") or get_logger()

    try:
        with get_database(config) as db:
            ensure_user_exists(db)

            ht = HabitTracker(db, calculate_streak_from_logs, config)
            calendar_data = ht.get_calendar(habit_id, days)

            habit = calendar_data["habit"]
            completion_map = calendar_data["completion_map"]
            current_streak = habit.get("streak", 0)
            longest_streak = habit.get("longest_streak", 0)
            calendar_data["completion_rate"]

            # Convert completion_map to list of booleans in chronological order
            completions = [completion_map[date_str] for date_str in sorted(completion_map.keys())]

            # Generate calendar visualization
            calendar_str = generate_habit_calendar(
                completions,
                habit["name"],
                current_streak,
                longest_streak,
            )

            console.print()  # Empty line
            console.print(
                Panel.fit(
                    calendar_str,
                    border_style="cyan",
                    title=f"[bold]{habit['name']} - Last {days} Days[/bold]",
                )
            )

            logger.debug("Calendar displayed for habit: %s (ID: %d)", habit["name"], habit_id)

    except ValidationError as e:
        logger.error("Habit validation failed: %s", str(e))
        console.print(
            Panel.fit(
                f"[bold yellow]Invalid Habit[/bold yellow]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Habit ID {habit_id} may not exist.[/dim]",
                border_style="yellow",
            )
        )
        sys.exit(1)
    except DatabaseError as e:
        logger.error("Database error during calendar display: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Database Error[/bold red]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Failed to retrieve habit data from database.[/dim]",
                border_style="red",
            )
        )
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error displaying calendar: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Unexpected Error[/bold red]\n\n{str(e)}",
                border_style="red",
            )
        )
        sys.exit(1)


@habit.command("delete")
@click.argument("habit_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.pass_context
def habit_delete(ctx: click.Context, habit_id: int, yes: bool) -> None:
    """Delete a habit and all its tracking logs.

    Example:
        zenflow habit delete 1
    """
    config = ctx.obj["config"]
    logger = ctx.obj.get("logger") or get_logger()

    try:
        with get_database(config) as db:
            user = ensure_user_exists(db)

            if not yes:
                if not click.confirm(
                    f"Are you sure you want to delete habit {habit_id}? This will also delete all tracking logs."
                ):
                    console.print("[yellow]Deletion cancelled.[/yellow]")
                    return

            ht = HabitTracker(db, calculate_streak_from_logs, config)
            ht.delete_habit(user["id"], habit_id)

            logger.info("Habit deleted: ID=%d", habit_id)

            console.print(f"[green]✓ Habit {habit_id} deleted successfully![/green]")

    except ValidationError as e:
        logger.error("Habit validation failed: %s", str(e))
        console.print(
            Panel.fit(
                f"[bold yellow]Invalid Habit[/bold yellow]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Habit ID {habit_id} may not exist or you don't have permission.[/dim]",
                border_style="yellow",
            )
        )
        sys.exit(1)
    except DatabaseError as e:
        logger.error("Database error during habit deletion: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Database Error[/bold red]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Failed to delete habit from database.[/dim]",
                border_style="red",
            )
        )
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error deleting habit: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Unexpected Error[/bold red]\n\n{str(e)}",
                border_style="red",
            )
        )
        sys.exit(1)


@cli.group()
def focus() -> None:
    """Manage focus sessions: start Pomodoro timers and view history."""
    pass


@focus.command("start")
@click.option(
    "--duration",
    "-d",
    type=int,
    default=25,
    help="Focus session duration in minutes (default: 25)",
)
@click.pass_context
def focus_start(ctx: click.Context, duration: int) -> None:
    """Start a Pomodoro focus session with live countdown.

    The timer will run for the specified duration and award XP upon completion.
    Press Ctrl+C to stop the timer early (no XP awarded).

    Example:
        zenflow focus start --duration 25
    """
    config = ctx.obj["config"]
    logger = ctx.obj.get("logger") or get_logger()

    if duration <= 0 or duration > 120:
        console.print("[red]Duration must be between 1 and 120 minutes.[/red]")
        return

    try:
        with get_database(config) as db:
            user = ensure_user_exists(db)
            user_id = user["id"]

            # Initialize gamification engine and focus timer
            gamification = GamificationEngine(db, config)
            timer = FocusTimer(db, config, gamification, duration)

            # Start the session
            session_id = timer.start(user_id)
            logger.info(
                "Focus session started: session_id=%d, duration=%d minutes", session_id, duration
            )

            console.print(f"[cyan]Starting {duration}-minute focus session...[/cyan]\n")

            # Stop flag for graceful interruption
            stop_requested = False

            def timer_tick() -> None:
                """Background thread that ticks the timer every second."""
                while timer.is_running() and not stop_requested:
                    time.sleep(1)
                    timer.tick()

            # Start timer thread
            timer_thread = threading.Thread(target=timer_tick, daemon=True)
            timer_thread.start()

            try:
                # Live countdown display
                with Live(console=console, refresh_per_second=1) as live:
                    while timer.is_running() and timer.remaining > 0:
                        panel = create_focus_panel(timer.remaining, timer.duration)
                        live.update(panel)
                        time.sleep(0.1)  # Small sleep to prevent CPU spinning

                # Timer completed naturally
                if timer.remaining == 0 and timer.is_running():
                    result = timer.complete(user_id)

                    logger.info(
                        "Focus session completed: session_id=%d, xp_earned=%d",
                        session_id,
                        result["xp_earned"],
                    )

                    console.print("\n[bold green]✓ Focus session complete![/bold green]")
                    console.print(f"[cyan]+{result['xp_earned']} XP earned[/cyan]")
                    console.print(
                        f"[dim]Total focus time today: {result['total_focus_today']} minutes[/dim]"
                    )

                    # Display achievements if any were unlocked
                    if result.get("achievements"):
                        console.print("\n[bold cyan]🏆 New Achievements Unlocked![/bold cyan]\n")
                        for achievement in result["achievements"]:
                            console.print(
                                Panel.fit(
                                    f"[bold yellow]{achievement['title']}[/bold yellow]\n"
                                    f"{achievement['description']}\n"
                                    f"[cyan]+{achievement['xp_earned']} XP[/cyan]",
                                    border_style="yellow",
                                )
                            )

                    # Show level up if applicable
                    if result.get("level_up"):
                        console.print("\n[bold yellow]🎉 Level Up![/bold yellow]")

            except KeyboardInterrupt:
                # User interrupted with Ctrl+C
                stop_requested = True
                timer.stop()
                logger.info("Focus session interrupted: session_id=%d", session_id)
                console.print("\n\n[yellow]Focus session stopped. No XP awarded.[/yellow]")

    except ValidationError as e:
        logger.error("Focus session validation failed: %s", str(e))
        console.print(
            Panel.fit(
                f"[bold yellow]Invalid Session Data[/bold yellow]\n\n{str(e)}",
                border_style="yellow",
            )
        )
        sys.exit(1)
    except DatabaseError as e:
        logger.error("Database error during focus session: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Database Error[/bold red]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Failed to save focus session to database.[/dim]",
                border_style="red",
            )
        )
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error in focus session: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Unexpected Error[/bold red]\n\n{str(e)}",
                border_style="red",
            )
        )
        sys.exit(1)


@focus.command("history")
@click.option(
    "--limit",
    "-l",
    type=int,
    default=10,
    help="Number of recent sessions to show (default: 10)",
)
@click.option(
    "--all",
    "-a",
    "show_all",
    is_flag=True,
    help="Show all sessions (completed and incomplete)",
)
@click.pass_context
def focus_history(ctx: click.Context, limit: int, show_all: bool) -> None:
    """View focus session history.

    Shows recent focus sessions with duration, completion status, and timestamps.

    Example:
        zenflow focus history --limit 20
        zenflow focus history --all
    """
    config = ctx.obj["config"]
    logger = ctx.obj.get("logger") or get_logger()

    try:
        with get_database(config) as db:
            user = ensure_user_exists(db)
            user_id = user["id"]

            # Build query
            query = """
                SELECT
                    id,
                    duration_minutes,
                    completed,
                    started_at,
                    completed_at
                FROM focus_sessions
                WHERE user_id = ?
            """

            if not show_all:
                query += " AND completed = 1"

            query += " ORDER BY started_at DESC LIMIT ?"

            sessions = db.fetch_all(query, (user_id, limit))

            if not sessions:
                console.print("[yellow]No focus sessions found.[/yellow]")
                console.print("[dim]Start your first session with:[/dim] zenflow focus start")
                return

            # Create table
            table = Table(title="Focus Session History", show_header=True, header_style="bold cyan")
            table.add_column("ID", style="dim", width=6)
            table.add_column("Duration", width=10)
            table.add_column("Status", width=12)
            table.add_column("Started", width=20)
            table.add_column("Completed", width=20)

            for session in sessions:
                session_id = str(session["id"])
                duration = f"{session['duration_minutes']} min"
                status = (
                    "[green]✓ Complete[/green]"
                    if session["completed"]
                    else "[red]✗ Incomplete[/red]"
                )

                started = session["started_at"]
                if isinstance(started, str):
                    started_dt = datetime.fromisoformat(started)
                else:
                    started_dt = started
                started_str = started_dt.strftime("%Y-%m-%d %H:%M")

                if session["completed"] and session["completed_at"]:
                    completed = session["completed_at"]
                    if isinstance(completed, str):
                        completed_dt = datetime.fromisoformat(completed)
                    else:
                        completed_dt = completed
                    completed_str = completed_dt.strftime("%Y-%m-%d %H:%M")
                else:
                    completed_str = "-"

                table.add_row(session_id, duration, status, started_str, completed_str)

            console.print()
            console.print(table)

            # Show summary statistics
            total_completed = sum(1 for s in sessions if s["completed"])
            total_minutes = sum(s["duration_minutes"] for s in sessions if s["completed"])

            console.print(
                f"\n[dim]Showing {len(sessions)} sessions | "
                f"{total_completed} completed | "
                f"{total_minutes} total minutes[/dim]"
            )

            logger.debug("Focus history displayed: %d sessions", len(sessions))

    except DatabaseError as e:
        logger.error("Database error during focus history display: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Database Error[/bold red]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Failed to retrieve focus sessions from database.[/dim]",
                border_style="red",
            )
        )
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error displaying focus history: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Unexpected Error[/bold red]\n\n{str(e)}",
                border_style="red",
            )
        )
        sys.exit(1)


@cli.command()
@click.pass_context
def profile(ctx: click.Context) -> None:
    """Display user profile with gamification stats.

    Shows your current level, XP, progress to next level, statistics,
    and achievements unlocked.

    Example:
        zenflow profile
    """
    config = ctx.obj["config"]
    logger = ctx.obj.get("logger") or get_logger()

    try:
        with get_database(config) as db:
            user = ensure_user_exists(db)

            # Get user basic data
            user_id = user["id"]
            username = user["username"]
            email = user["email"]
            level = user["level"]
            xp = user["xp"]

            # Calculate level progress
            xp_per_level = config["gamification"]["xp_per_level"]
            xp_to_next_level = calculate_xp_to_next_level(xp, xp_per_level)
            progress = calculate_level_progress(xp, xp_per_level)

            # Get statistics
            tasks_completed_row = db.fetch_one(
                "SELECT COUNT(*) as count FROM tasks WHERE user_id = ? AND status = 'DONE'",
                (user_id,),
            )
            tasks_completed = tasks_completed_row["count"] if tasks_completed_row else 0

            habits_tracked_row = db.fetch_one(
                "SELECT COUNT(*) as count FROM habit_logs hl JOIN habits h ON hl.habit_id = h.id WHERE h.user_id = ?",
                (user_id,),
            )
            habits_tracked = habits_tracked_row["count"] if habits_tracked_row else 0

            focus_sessions_row = db.fetch_one(
                "SELECT COUNT(*) as count FROM focus_sessions WHERE user_id = ? AND completed = 1",
                (user_id,),
            )
            focus_sessions = focus_sessions_row["count"] if focus_sessions_row else 0

            current_streaks_row = db.fetch_one(
                "SELECT COUNT(*) as count FROM habits WHERE user_id = ? AND streak > 0",
                (user_id,),
            )
            current_streaks = current_streaks_row["count"] if current_streaks_row else 0

            achievements_unlocked_row = db.fetch_one(
                "SELECT COUNT(*) as count FROM achievements WHERE user_id = ?", (user_id,)
            )
            achievements_unlocked = (
                achievements_unlocked_row["count"] if achievements_unlocked_row else 0
            )

            total_achievements = len(ACHIEVEMENT_DEFINITIONS)

            # Prepare profile data
            profile_data = {
                "username": username,
                "email": email,
                "level": level,
                "xp": xp,
                "xp_per_level": xp_per_level,
                "xp_to_next_level": xp_to_next_level,
                "progress": progress,
                "tasks_completed": tasks_completed,
                "habits_tracked": habits_tracked,
                "focus_sessions": focus_sessions,
                "current_streaks": current_streaks,
                "achievements_unlocked": achievements_unlocked,
                "total_achievements": total_achievements,
            }

            # Display profile panel
            panel = create_profile_panel(profile_data)
            console.print(panel)

            logger.debug("Profile displayed for user: %s", username)

    except DatabaseError as e:
        logger.error("Database error during profile display: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Database Error[/bold red]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Failed to retrieve profile data from database.[/dim]",
                border_style="red",
            )
        )
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error displaying profile: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Unexpected Error[/bold red]\n\n{str(e)}",
                border_style="red",
            )
        )
        sys.exit(1)


@cli.command()
@click.pass_context
def achievements(ctx: click.Context) -> None:
    """Display all achievements with unlock status.

    Shows all available achievements, their descriptions, XP rewards,
    and whether they are locked or unlocked. For locked achievements,
    displays progress towards unlocking them.

    Example:
        zenflow achievements
    """
    config = ctx.obj["config"]
    logger = ctx.obj.get("logger") or get_logger()

    try:
        with get_database(config) as db:
            user = ensure_user_exists(db)
            user_id = user["id"]

            # Get unlocked achievements
            unlocked_achievements = db.fetch_all(
                "SELECT achievement_type, xp_earned FROM achievements WHERE user_id = ?", (user_id,)
            )
            unlocked_types = {
                ach["achievement_type"]: ach["xp_earned"] for ach in unlocked_achievements
            }

            # Get user stats for progress calculation
            gamification = GamificationEngine(db, config)
            user_stats = gamification._get_user_stats(user_id)

            # Build achievement list with unlock status
            achievements_list = []
            for achievement_def in ACHIEVEMENT_DEFINITIONS:
                achievement_type = achievement_def["type"]
                title = achievement_def["title"]
                description = achievement_def["description"]
                xp = achievement_def["xp"]
                achievement_def["condition"]

                # Check if unlocked
                unlocked = achievement_type in unlocked_types

                # Calculate progress for locked achievements
                progress = None
                if not unlocked:
                    # Try to extract progress from the condition
                    # This is a simple approach - check the condition description
                    try:
                        # For task-based achievements
                        if "tasks" in description.lower():
                            if "complete 10 tasks" in description.lower():
                                progress = {
                                    "current": user_stats.get("tasks_completed", 0),
                                    "target": 10,
                                }
                            elif "complete 100 tasks" in description.lower():
                                progress = {
                                    "current": user_stats.get("tasks_completed", 0),
                                    "target": 100,
                                }
                            elif "complete 500 tasks" in description.lower():
                                progress = {
                                    "current": user_stats.get("tasks_completed", 0),
                                    "target": 500,
                                }
                            elif "5 or more tasks" in description.lower():
                                progress = {
                                    "current": user_stats.get("max_tasks_per_day", 0),
                                    "target": 5,
                                }
                            elif "10 or more tasks" in description.lower():
                                progress = {
                                    "current": user_stats.get("max_tasks_per_day", 0),
                                    "target": 10,
                                }
                        # For habit-based achievements
                        elif "habit" in description.lower():
                            if "7-day" in description.lower():
                                progress = {
                                    "current": user_stats.get("max_habit_streak", 0),
                                    "target": 7,
                                }
                            elif "30-day" in description.lower():
                                progress = {
                                    "current": user_stats.get("max_habit_streak", 0),
                                    "target": 30,
                                }
                            elif "100-day" in description.lower():
                                progress = {
                                    "current": user_stats.get("max_habit_streak", 0),
                                    "target": 100,
                                }
                            elif "3 active habits" in description.lower():
                                progress = {
                                    "current": user_stats.get("active_habits", 0),
                                    "target": 3,
                                }
                        # For focus session achievements
                        elif "focus" in description.lower():
                            if "10 focus sessions" in description.lower():
                                progress = {
                                    "current": user_stats.get("focus_sessions_completed", 0),
                                    "target": 10,
                                }
                            elif "50 focus sessions" in description.lower():
                                progress = {
                                    "current": user_stats.get("focus_sessions_completed", 0),
                                    "target": 50,
                                }
                        # For level achievements
                        elif "level" in description.lower():
                            if "level 5" in description.lower():
                                progress = {"current": user_stats.get("level", 1), "target": 5}
                            elif "level 10" in description.lower():
                                progress = {"current": user_stats.get("level", 1), "target": 10}
                    except Exception:
                        # If progress calculation fails, just skip it
                        pass

                achievements_list.append(
                    {
                        "title": title,
                        "description": description,
                        "unlocked": unlocked,
                        "xp_earned": xp,
                        "progress": progress,
                    }
                )

            # Sort: unlocked first, then by XP
            achievements_list.sort(key=lambda x: (not x["unlocked"], x["xp_earned"]))

            # Display achievements table
            table = create_achievement_table(achievements_list)
            console.print(table)

            # Display summary
            unlocked_count = len(unlocked_types)
            total_count = len(ACHIEVEMENT_DEFINITIONS)
            console.print(
                f"\n[cyan]Achievements:[/cyan] {unlocked_count}/{total_count} unlocked "
                f"({unlocked_count * 100 // total_count}%)"
            )

            logger.debug(
                "Achievements displayed: %d unlocked, %d total", unlocked_count, total_count
            )

    except DatabaseError as e:
        logger.error("Database error during achievements display: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Database Error[/bold red]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Failed to retrieve achievements from database.[/dim]",
                border_style="red",
            )
        )
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error displaying achievements: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Unexpected Error[/bold red]\n\n{str(e)}",
                border_style="red",
            )
        )
        sys.exit(1)


@cli.command()
@click.option(
    "--period",
    "-p",
    type=click.Choice(["day", "week", "month"], case_sensitive=False),
    default="week",
    help="Time period for statistics (default: week)",
)
@click.pass_context
def stats(ctx: click.Context, period: str) -> None:
    """Display productivity statistics and analytics.

    Shows task completion, XP earned, focus time, and daily breakdown
    for the specified period.

    Example:
        zenflow stats
        zenflow stats --period day
        zenflow stats --period month
    """
    config = ctx.obj["config"]
    logger = ctx.obj.get("logger") or get_logger()

    try:
        with get_database(config) as db:
            user = ensure_user_exists(db)
            user_id = user["id"]

            # Calculate date range based on period
            from datetime import datetime, timedelta

            today = datetime.now().date()

            if period.lower() == "day":
                start_date = today
            elif period.lower() == "week":
                start_date = today - timedelta(days=6)  # Last 7 days including today
            else:  # month
                start_date = today - timedelta(days=29)  # Last 30 days including today

            # Query daily stats for the period
            daily_stats = db.fetch_all(
                """
                SELECT date, tasks_completed, xp_earned, focus_minutes
                FROM daily_stats
                WHERE user_id = ? AND date >= ? AND date <= ?
                ORDER BY date ASC
                """,
                (user_id, start_date.isoformat(), today.isoformat()),
            )

            # Aggregate totals
            total_tasks = sum(stat["tasks_completed"] for stat in daily_stats)
            total_xp = sum(stat["xp_earned"] for stat in daily_stats)
            total_focus_time = sum(stat["focus_minutes"] for stat in daily_stats)

            # Count active habits (habits with streaks > 0)
            active_habits = db.fetch_one(
                "SELECT COUNT(*) as count FROM habits WHERE user_id = ? AND streak > 0",
                (user_id,),
            )
            active_habits_count = active_habits["count"] if active_habits else 0

            # Build daily breakdown for last 7 days (for chart)
            daily_breakdown = {}
            if period.lower() in ["week", "month"]:
                # For week/month, show last 7 days
                last_7_days_start = today - timedelta(days=6)
                for i in range(7):
                    day_date = last_7_days_start + timedelta(days=i)
                    day_name = day_date.strftime("%a")  # Mon, Tue, Wed, etc.

                    # Find matching stat
                    matching_stat = next(
                        (s for s in daily_stats if s["date"] == day_date.isoformat()), None
                    )

                    tasks_count = matching_stat["tasks_completed"] if matching_stat else 0
                    daily_breakdown[day_name] = tasks_count
            else:  # day
                # For single day, show hourly or just today's total
                day_name = today.strftime("%a")
                daily_breakdown[day_name] = total_tasks

            # Find most and least productive days
            most_productive = None
            least_productive = None

            if daily_stats and period.lower() != "day":
                # Find max
                max_stat = max(daily_stats, key=lambda x: x["tasks_completed"])
                max_date = datetime.fromisoformat(max_stat["date"]).strftime("%A")
                most_productive = {
                    "day": max_date,
                    "tasks": max_stat["tasks_completed"],
                    "xp": max_stat["xp_earned"],
                }

                # Find min (excluding zero days if possible)
                non_zero_stats = [s for s in daily_stats if s["tasks_completed"] > 0]
                if non_zero_stats:
                    min_stat = min(non_zero_stats, key=lambda x: x["tasks_completed"])
                else:
                    min_stat = min(daily_stats, key=lambda x: x["tasks_completed"])

                min_date = datetime.fromisoformat(min_stat["date"]).strftime("%A")
                least_productive = {
                    "day": min_date,
                    "tasks": min_stat["tasks_completed"],
                }

            # Build stats data for panel
            stats_data = {
                "tasks_completed": total_tasks,
                "xp_earned": total_xp,
                "focus_time": total_focus_time,
                "active_habits": active_habits_count,
                "daily_breakdown": daily_breakdown,
                "most_productive_day": most_productive,
                "least_productive_day": least_productive,
            }

            # Display stats panel
            panel = create_stats_panel(stats_data, period.lower())
            console.print(panel)

            logger.info(
                "Stats displayed: period=%s, tasks=%d, xp=%d, focus=%d",
                period,
                total_tasks,
                total_xp,
                total_focus_time,
            )

    except DatabaseError as e:
        logger.error("Database error during stats display: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Database Error[/bold red]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Failed to retrieve statistics from database.[/dim]",
                border_style="red",
            )
        )
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error displaying stats: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Unexpected Error[/bold red]\n\n{str(e)}",
                border_style="red",
            )
        )
        sys.exit(1)


@cli.command()
@click.pass_context
def insights(ctx: click.Context) -> None:
    """Get AI-powered productivity insights and recommendations.

    Analyzes your productivity patterns, task completion history, habit streaks,
    and focus session data to provide personalized insights and recommendations.

    Requirements:
        - AI must be enabled in config.yaml (ai.enabled: true)
        - OPENAI_API_KEY environment variable must be set
        - OpenAI library must be installed (pip install openai)

    Example:
        export OPENAI_API_KEY=sk-...
        zenflow insights
    """
    config = ctx.obj["config"]
    logger = ctx.obj.get("logger") or get_logger()

    try:
        # Check if AI is enabled in config
        if not config.get("ai", {}).get("enabled", False):
            console.print(
                Panel.fit(
                    "[bold yellow]AI Insights Disabled[/bold yellow]\n\n"
                    "AI insights are currently disabled in your configuration.\n\n"
                    "To enable:\n"
                    "1. Edit config.yaml and set ai.enabled: true\n"
                    "2. Set OPENAI_API_KEY environment variable\n"
                    "3. Install OpenAI library: pip install openai",
                    border_style="yellow",
                )
            )
            return

        # Check if OpenAI library is available
        if not OPENAI_AVAILABLE:
            console.print(
                Panel.fit(
                    "[bold red]OpenAI Library Not Installed[/bold red]\n\n"
                    "The OpenAI library is required for AI insights.\n\n"
                    "Install with: pip install openai",
                    border_style="red",
                )
            )
            return

        with get_database(config) as db:
            user = ensure_user_exists(db)

            console.print("[cyan]🤖 Analyzing your productivity patterns...[/cyan]\n")

            try:
                # Initialize AI insights engine
                ai_engine = AIInsightsEngine(db, config)

                logger.info("Generating AI insights for user: %d", user["id"])

                # Get pattern analysis
                console.print("[dim]Analyzing task completion patterns...[/dim]")
                patterns = ai_engine.analyze_patterns(user["id"])

                # Get recommendations
                console.print("[dim]Generating personalized recommendations...[/dim]")
                recommendations = ai_engine.generate_recommendations(user["id"])

                # Get optimal times
                console.print("[dim]Predicting optimal work times...[/dim]")
                optimal_times = ai_engine.predict_optimal_times(user["id"])

                console.print()

                # Display pattern analysis
                pattern_content = "[bold cyan]📊 Pattern Analysis:[/bold cyan]\n\n"
                pattern_content += patterns.get("full_analysis", "No analysis available.")

                console.print(
                    Panel.fit(
                        pattern_content,
                        border_style="cyan",
                        title="[bold]AI Insights[/bold]",
                    )
                )

                console.print()

                # Display recommendations
                if recommendations:
                    rec_content = "[bold yellow]💡 Recommendations:[/bold yellow]\n\n"
                    for i, rec in enumerate(recommendations, 1):
                        rec_content += f"{i}. {rec}\n"
                        if i < len(recommendations):
                            rec_content += "\n"

                    console.print(
                        Panel.fit(
                            rec_content.rstrip(),
                            border_style="yellow",
                        )
                    )

                    console.print()

                # Display optimal times
                times_content = "[bold green]⏰ Optimal Work Times:[/bold green]\n\n"
                times_content += (
                    f"[bold]High Focus Work:[/bold] {optimal_times.get('high_focus', 'N/A')}\n"
                )
                times_content += (
                    f"[bold]Task Execution:[/bold] {optimal_times.get('task_execution', 'N/A')}\n"
                )
                times_content += (
                    f"[bold]Habit Tracking:[/bold] {optimal_times.get('habits', 'N/A')}"
                )

                console.print(
                    Panel.fit(
                        times_content,
                        border_style="green",
                    )
                )

                logger.info("AI insights generated successfully for user: %d", user["id"])

            except ConfigurationError as e:
                logger.error("AI configuration error: %s", str(e))
                console.print(
                    Panel.fit(
                        f"[bold red]Configuration Error[/bold red]\n\n{str(e)}",
                        border_style="red",
                    )
                )
            except APIError as e:
                logger.error("AI API error: %s", str(e))
                console.print(
                    Panel.fit(
                        f"[bold red]API Error[/bold red]\n\n{str(e)}\n\n"
                        "Please check:\n"
                        "1. OPENAI_API_KEY is set correctly\n"
                        "2. You have API credits available\n"
                        "3. Your internet connection is working",
                        border_style="red",
                    )
                )
            except ValidationError as e:
                logger.error("AI validation error: %s", str(e))
                console.print(
                    Panel.fit(
                        f"[bold yellow]Invalid Data[/bold yellow]\n\n{str(e)}",
                        border_style="yellow",
                    )
                )
            except DatabaseError as e:
                logger.error("Database error during insights: %s", str(e), exc_info=True)
                console.print(
                    Panel.fit(
                        f"[bold red]Database Error[/bold red]\n\n"
                        f"{str(e)}\n\n"
                        f"[dim]Failed to retrieve data from database.[/dim]",
                        border_style="red",
                    )
                )

    except Exception as e:
        logger.error("Unexpected error in insights command: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Unexpected Error[/bold red]\n\n{str(e)}",
                border_style="red",
            )
        )
        sys.exit(1)


@cli.command()
@click.option(
    "--type",
    "-t",
    "export_type",
    type=click.Choice(
        ["tasks", "habits", "stats", "achievements", "focus", "all"], case_sensitive=False
    ),
    default="all",
    help="Type of data to export (default: all)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["csv", "json", "txt"], case_sensitive=False),
    default="json",
    help="Output format (default: json)",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    required=True,
    help="Output file path",
)
@click.option(
    "--start-date",
    help="Filter start date (YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    help="Filter end date (YYYY-MM-DD)",
)
@click.pass_context
def export(
    ctx: click.Context,
    export_type: str,
    format: str,
    output_path: str,
    start_date: str | None,
    end_date: str | None,
) -> None:
    """Export ZenFlow data to file for backup or analysis.

    Supports exporting tasks, habits, achievements, focus sessions,
    and daily statistics in CSV, JSON, or TXT formats.

    Examples:
        zenflow export --type tasks --format csv --output tasks.csv
        zenflow export --type all --format json --output backup.json
        zenflow export --type stats --format txt --output report.txt --start-date 2026-01-01
    """
    config = ctx.obj["config"]
    logger = ctx.obj.get("logger") or get_logger()

    try:
        # Validate dates if provided
        if start_date:
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                console.print("[red]Invalid start date format. Use YYYY-MM-DD[/red]")
                return

        if end_date:
            try:
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                console.print("[red]Invalid end date format. Use YYYY-MM-DD[/red]")
                return

        # Validate output path
        output_file = Path(output_path)

        # Check if output directory exists
        if output_file.parent != Path(".") and not output_file.parent.exists():
            console.print(f"[red]Directory does not exist:[/red] {output_file.parent}")
            return

        # Check if file exists and confirm overwrite
        if output_file.exists():
            overwrite = click.confirm(
                f"\nFile '{output_path}' already exists. Overwrite?",
                default=False,
            )
            if not overwrite:
                console.print("[yellow]Export cancelled.[/yellow]")
                return

        with get_database(config) as db:
            user = ensure_user_exists(db)

            logger.info(
                "Exporting data: type=%s, format=%s, output=%s",
                export_type,
                format,
                output_path,
            )

            console.print(f"[cyan]Exporting {export_type} data...[/cyan]")

            # Call export function
            export_data(
                export_type=export_type.lower(),
                format=format.lower(),
                output_path=output_path,
                db=db,
                user_id=user["id"],
                start_date=start_date,
                end_date=end_date,
            )

            # Check what files were created
            if export_type == "all" and format != "json":
                # Multiple files created
                console.print("\n[green]✓ Data exported successfully![/green]")
                console.print(
                    Panel.fit(
                        f"[bold]Export Complete[/bold]\n\n"
                        f"[bold]Type:[/bold] All data\n"
                        f"[bold]Format:[/bold] {format.upper()}\n"
                        f"[bold]Files created:[/bold]\n"
                        f"  • {output_file.stem}_tasks{output_file.suffix}\n"
                        f"  • {output_file.stem}_habits{output_file.suffix}\n"
                        f"  • {output_file.stem}_achievements{output_file.suffix}\n"
                        f"  • {output_file.stem}_focus{output_file.suffix}\n"
                        f"  • {output_file.stem}_stats{output_file.suffix}",
                        border_style="green",
                    )
                )
            else:
                # Single file created
                file_size = output_file.stat().st_size if output_file.exists() else 0
                size_kb = file_size / 1024

                console.print("\n[green]✓ Data exported successfully![/green]")
                console.print(
                    Panel.fit(
                        f"[bold]Export Complete[/bold]\n\n"
                        f"[bold]Type:[/bold] {export_type.capitalize()}\n"
                        f"[bold]Format:[/bold] {format.upper()}\n"
                        f"[bold]File:[/bold] {output_path}\n"
                        f"[bold]Size:[/bold] {size_kb:.2f} KB",
                        border_style="green",
                    )
                )

            logger.info("Export completed successfully: %s", output_path)

    except ValidationError as e:
        logger.error("Export validation failed: %s", str(e))
        console.print(
            Panel.fit(
                f"[bold yellow]Invalid Export Parameters[/bold yellow]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Check export type, format, and date range.[/dim]",
                border_style="yellow",
            )
        )
        sys.exit(1)
    except DatabaseError as e:
        logger.error("Database error during export: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Database Error[/bold red]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Failed to retrieve data from database.[/dim]",
                border_style="red",
            )
        )
        sys.exit(1)
    except OSError as e:
        logger.error("File error during export: %s", str(e))
        console.print(
            Panel.fit(
                f"[bold red]File I/O Error[/bold red]\n\n"
                f"{str(e)}\n\n"
                f"[dim]Check file permissions and disk space.[/dim]",
                border_style="red",
            )
        )
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error during export: %s", str(e), exc_info=True)
        console.print(
            Panel.fit(
                f"[bold red]Unexpected Error[/bold red]\n\n{str(e)}",
                border_style="red",
            )
        )
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI application."""
    cli(obj={})


if __name__ == "__main__":
    main()
