"""AI-powered productivity insights using OpenAI.

This module provides AI-driven analysis of user productivity patterns,
personalized recommendations, and optimal work time predictions using
the OpenAI API.
"""

import os
from datetime import datetime, timedelta
from typing import Any

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from zenflow.database.db import Database


class AIInsightsEngine:
    """AI-powered productivity insights using OpenAI API.

    Analyzes user's task completion patterns, habit tracking data, and
    focus session history to generate personalized productivity insights
    and recommendations.

    Args:
        db: Database instance for querying user data
        config: Configuration dict with AI settings (model, provider)
        api_key: OpenAI API key (optional, defaults to OPENAI_API_KEY env var)

    Example:
        >>> engine = AIInsightsEngine(db, config)
        >>> insights = engine.analyze_patterns(user_id=1)
        >>> print(insights['summary'])
    """

    def __init__(self, db: Database, config: dict[str, Any], api_key: str | None = None) -> None:
        """Initialize AIInsightsEngine with database and configuration.

        Args:
            db: Database instance for querying productivity data
            config: Configuration dict with 'ai' section
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)

        Raises:
            RuntimeError: If OpenAI library not installed
            ValueError: If API key not provided or AI not enabled in config
        """
        if not OPENAI_AVAILABLE:
            raise RuntimeError("OpenAI library not installed. Install with: pip install openai")

        self.db = db
        self.config = config

        if not self.config.get("ai", {}).get("enabled", False):
            raise ValueError(
                "AI insights are disabled in config. Set ai.enabled=true in config.yaml"
            )

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter"
            )

        self.client = OpenAI(api_key=self.api_key)
        self.model = self.config.get("ai", {}).get("model", "gpt-4")

    def analyze_patterns(self, user_id: int) -> dict[str, Any]:
        """Analyze user's productivity patterns using AI.

        Collects user data (tasks, habits, focus sessions, daily stats) and
        sends to OpenAI for pattern analysis. Returns insights about most
        productive times, completion trends, and behavior patterns.

        Args:
            user_id: ID of user to analyze

        Returns:
            Dict with keys:
                - summary: str (Overview of productivity patterns)
                - insights: List[str] (Specific pattern observations)
                - productive_times: Dict[str, str] (Best times for work)
                - trends: List[str] (Completion trend observations)

        Raises:
            RuntimeError: If API call fails
        """
        user_data = self._collect_user_data(user_id)

        prompt = self._build_pattern_analysis_prompt(user_data)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a productivity analyst. Analyze the user's "
                            "productivity data and identify patterns, trends, and "
                            "insights. Be specific, concise, and actionable."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=500,
            )

            analysis = response.choices[0].message.content or ""

            return self._parse_analysis_response(analysis)

        except Exception as e:
            raise RuntimeError(f"Failed to analyze patterns: {str(e)}") from e

    def generate_recommendations(self, user_id: int) -> list[str]:
        """Generate personalized productivity recommendations.

        Uses AI to analyze user data and generate actionable recommendations
        for improving productivity, task management, and habit consistency.

        Args:
            user_id: ID of user to generate recommendations for

        Returns:
            List of recommendation strings (3-5 recommendations)

        Raises:
            RuntimeError: If API call fails
        """
        user_data = self._collect_user_data(user_id)

        prompt = self._build_recommendations_prompt(user_data)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a productivity coach. Based on the user's data, "
                            "provide 3-5 specific, actionable recommendations to improve "
                            "their productivity. Each recommendation should be 1-2 sentences."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=400,
            )

            recommendations_text = response.choices[0].message.content or ""

            return self._parse_recommendations_response(recommendations_text)

        except Exception as e:
            raise RuntimeError(f"Failed to generate recommendations: {str(e)}") from e

    def predict_optimal_times(self, user_id: int) -> dict[str, str]:
        """Predict optimal work times based on completion history.

        Analyzes when user completes most tasks and has successful focus
        sessions to recommend best times for different types of work.

        Args:
            user_id: ID of user to analyze

        Returns:
            Dict with time recommendations:
                - high_focus: str (Best time for deep work)
                - task_execution: str (Best time for task completion)
                - habits: str (Best time for habit tracking)

        Raises:
            RuntimeError: If API call fails
        """
        user_data = self._collect_user_data(user_id)

        prompt = self._build_optimal_times_prompt(user_data)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a productivity analyst. Based on task completion "
                            "times and focus session data, recommend optimal times for "
                            "different work activities. Be specific with time ranges."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=300,
            )

            optimal_times_text = response.choices[0].message.content or ""

            return self._parse_optimal_times_response(optimal_times_text)

        except Exception as e:
            raise RuntimeError(f"Failed to predict optimal times: {str(e)}") from e

    def _collect_user_data(self, user_id: int) -> dict[str, Any]:
        """Collect all relevant user productivity data.

        Args:
            user_id: ID of user to collect data for

        Returns:
            Dict containing tasks, habits, focus sessions, and stats
        """
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()

        user = self.db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))

        tasks = self.db.fetch_all(
            """
            SELECT priority, status, completed_at, created_at, due_date
            FROM tasks
            WHERE user_id = ? AND created_at > ?
            ORDER BY completed_at DESC
            """,
            (user_id, thirty_days_ago),
        )

        habits = self.db.fetch_all(
            "SELECT name, frequency, streak, longest_streak FROM habits WHERE user_id = ?",
            (user_id,),
        )

        focus_sessions = self.db.fetch_all(
            """
            SELECT duration_minutes, completed, started_at, completed_at
            FROM focus_sessions
            WHERE user_id = ? AND started_at > ?
            """,
            (user_id, thirty_days_ago),
        )

        daily_stats = self.db.fetch_all(
            """
            SELECT date, tasks_completed, xp_earned, focus_minutes
            FROM daily_stats
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT 30
            """,
            (user_id,),
        )

        return {
            "user": dict(user) if user else {},
            "tasks": [dict(t) for t in tasks] if tasks else [],
            "habits": [dict(h) for h in habits] if habits else [],
            "focus_sessions": [dict(f) for f in focus_sessions] if focus_sessions else [],
            "daily_stats": [dict(d) for d in daily_stats] if daily_stats else [],
        }

    def _build_pattern_analysis_prompt(self, user_data: dict[str, Any]) -> str:
        """Build prompt for pattern analysis.

        Args:
            user_data: User productivity data dict

        Returns:
            Formatted prompt string for OpenAI
        """
        tasks = user_data.get("tasks", [])
        daily_stats = user_data.get("daily_stats", [])
        habits = user_data.get("habits", [])

        completed_tasks = [t for t in tasks if t.get("status") == "DONE"]
        total_tasks = len(tasks)
        completion_rate = (len(completed_tasks) / total_tasks * 100) if total_tasks > 0 else 0

        total_xp = sum(d.get("xp_earned", 0) for d in daily_stats)
        avg_tasks_per_day = (
            sum(d.get("tasks_completed", 0) for d in daily_stats) / len(daily_stats)
            if daily_stats
            else 0
        )

        return f"""Analyze this user's productivity data from the last 30 days:

User Profile:
- Level: {user_data.get('user', {}).get('level', 1)}
- Total XP: {user_data.get('user', {}).get('xp', 0)}

Tasks:
- Total tasks created: {total_tasks}
- Completed tasks: {len(completed_tasks)}
- Completion rate: {completion_rate:.1f}%
- Average tasks per day: {avg_tasks_per_day:.1f}

Habits:
- Active habits: {len(habits)}
- Longest streak: {max((h.get('longest_streak', 0) for h in habits), default=0)} days

Recent Activity:
- Total XP earned (30 days): {total_xp}
- Days with data: {len(daily_stats)}

Please provide:
1. A brief summary of overall productivity patterns
2. 2-3 specific insights about their work habits
3. Observations about productive vs. unproductive periods
4. Any notable trends or patterns"""

    def _build_recommendations_prompt(self, user_data: dict[str, Any]) -> str:
        """Build prompt for generating recommendations.

        Args:
            user_data: User productivity data dict

        Returns:
            Formatted prompt string for OpenAI
        """
        tasks = user_data.get("tasks", [])
        habits = user_data.get("habits", [])
        daily_stats = user_data.get("daily_stats", [])

        overdue_tasks = [
            t
            for t in tasks
            if t.get("status") != "DONE"
            and t.get("due_date")
            and datetime.fromisoformat(t["due_date"]) < datetime.now()
        ]

        weak_streaks = [h for h in habits if h.get("streak", 0) < 3]

        return f"""Based on this productivity data, provide recommendations:

Current Status:
- Pending tasks: {len([t for t in tasks if t.get('status') == 'TODO'])}
- Overdue tasks: {len(overdue_tasks)}
- Habits with weak streaks: {len(weak_streaks)}
- Average XP per day: {sum(d.get('xp_earned', 0) for d in daily_stats) / len(daily_stats) if daily_stats else 0:.0f}

Provide 3-5 actionable recommendations to improve their productivity.
Focus on:
- Task management improvements
- Habit consistency strategies
- Time management optimization
- Procrastination reduction"""

    def _build_optimal_times_prompt(self, user_data: dict[str, Any]) -> str:
        """Build prompt for optimal times prediction.

        Args:
            user_data: User productivity data dict

        Returns:
            Formatted prompt string for OpenAI
        """
        tasks = user_data.get("tasks", [])
        focus_sessions = user_data.get("focus_sessions", [])

        completed_tasks_with_time = [
            t for t in tasks if t.get("status") == "DONE" and t.get("completed_at")
        ]

        completion_hours = []
        for task in completed_tasks_with_time:
            try:
                completed_at = datetime.fromisoformat(task["completed_at"])
                completion_hours.append(completed_at.hour)
            except (ValueError, KeyError):
                continue

        completed_focus = [
            f for f in focus_sessions if f.get("completed") and f.get("completed_at")
        ]

        return f"""Analyze task completion times to recommend optimal work times:

Task Completions:
- Total completed tasks: {len(completed_tasks_with_time)}
- Completion times available: {len(completion_hours)}

Focus Sessions:
- Total completed: {len(completed_focus)}

Based on when this user successfully completes tasks and focus sessions,
recommend optimal times for:
1. High-focus work (deep work, complex tasks)
2. Task execution (regular task completion)
3. Habit tracking (best time to maintain consistency)

Provide specific time ranges (e.g., "9-11 AM", "2-4 PM")."""

    def _parse_analysis_response(self, analysis: str) -> dict[str, Any]:
        """Parse AI analysis response into structured format.

        Args:
            analysis: Raw AI response text

        Returns:
            Dict with structured analysis data
        """
        lines = [line.strip() for line in analysis.split("\n") if line.strip()]

        return {
            "summary": analysis[:200] if len(analysis) > 200 else analysis,
            "insights": lines[:5] if len(lines) > 5 else lines,
            "full_analysis": analysis,
        }

    def _parse_recommendations_response(self, recommendations: str) -> list[str]:
        """Parse AI recommendations response into list.

        Args:
            recommendations: Raw AI response text

        Returns:
            List of recommendation strings
        """
        lines = [
            line.strip().lstrip("0123456789.-) ")
            for line in recommendations.split("\n")
            if line.strip()
        ]

        return [line for line in lines if len(line) > 10][:5]

    def _parse_optimal_times_response(self, optimal_times: str) -> dict[str, str]:
        """Parse AI optimal times response into dict.

        Args:
            optimal_times: Raw AI response text

        Returns:
            Dict with time recommendations for different activities
        """
        result = {
            "high_focus": "Morning (9-11 AM)",
            "task_execution": "Afternoon (2-4 PM)",
            "habits": "Morning or Evening",
        }

        lower_text = optimal_times.lower()

        if "high-focus" in lower_text or "deep work" in lower_text:
            for line in optimal_times.split("\n"):
                if "high-focus" in line.lower() or "deep work" in line.lower():
                    result["high_focus"] = (
                        line.split(":", 1)[-1].strip() if ":" in line else line.strip()
                    )
                    break

        if "task execution" in lower_text or "task completion" in lower_text:
            for line in optimal_times.split("\n"):
                if "task execution" in line.lower() or "task completion" in line.lower():
                    result["task_execution"] = (
                        line.split(":", 1)[-1].strip() if ":" in line else line.strip()
                    )
                    break

        if "habit" in lower_text:
            for line in optimal_times.split("\n"):
                if "habit" in line.lower():
                    result["habits"] = (
                        line.split(":", 1)[-1].strip() if ":" in line else line.strip()
                    )
                    break

        return result
