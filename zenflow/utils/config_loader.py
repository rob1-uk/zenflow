"""Configuration loading utilities for ZenFlow.

This module provides functions to load configuration from YAML files and
environment variables, with support for default values and user overrides.
"""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""

    pass


DEFAULT_CONFIG: dict[str, Any] = {
    "database": {"path": "zenflow.db"},
    "gamification": {
        "xp_per_level": 1000,
        "task_xp": {"low": 10, "medium": 25, "high": 50},
        "habit_milestone_xp": {7: 25, 30: 100, 100: 500},
        "focus_xp": 15,
    },
    "focus": {
        "default_duration": 25,
        "break_duration": 5,
        "long_break_duration": 15,
    },
    "ai": {"enabled": False, "provider": "openai", "model": "gpt-4"},
    "ui": {
        "theme": "default",
        "color_scheme": {
            "success": "green",
            "warning": "yellow",
            "error": "red",
            "info": "cyan",
            "primary": "blue",
        },
    },
    "logging": {"level": "INFO", "file": "zenflow.log"},
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge two dictionaries.

    Args:
        base: Base dictionary with default values.
        override: Dictionary with override values.

    Returns:
        Merged dictionary with override values taking precedence.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """Load configuration from YAML file with defaults and validation.

    Loads the default configuration and merges it with user configuration
    from the specified file if it exists.

    Args:
        config_path: Path to YAML configuration file. If None, uses 'config.yaml'
                    in the current directory. If the file doesn't exist, returns
                    default configuration.

    Returns:
        Dictionary containing merged configuration.

    Raises:
        ConfigurationError: If configuration file is invalid or cannot be parsed.
    """
    config = DEFAULT_CONFIG.copy()

    if config_path is None:
        config_path = "config.yaml"

    config_file = Path(config_path)

    if not config_file.exists():
        return config

    try:
        with open(config_file) as f:
            user_config = yaml.safe_load(f)

        if user_config is None:
            return config

        if not isinstance(user_config, dict):
            raise ConfigurationError(
                f"Configuration file must contain a YAML dictionary, got {type(user_config).__name__}"
            )

        config = _deep_merge(config, user_config)

        _validate_config(config)

        return config

    except yaml.YAMLError as e:
        raise ConfigurationError(f"Failed to parse configuration file: {e}") from e
    except OSError as e:
        raise ConfigurationError(f"Failed to read configuration file: {e}") from e


def _validate_config(config: dict[str, Any]) -> None:
    """Validate configuration structure and values.

    Args:
        config: Configuration dictionary to validate.

    Raises:
        ConfigurationError: If configuration is invalid.
    """
    required_sections = ["database", "gamification", "focus", "ai", "ui", "logging"]
    for section in required_sections:
        if section not in config:
            raise ConfigurationError(f"Missing required configuration section: {section}")

    if "path" not in config["database"]:
        raise ConfigurationError("Database configuration must specify 'path'")

    if "xp_per_level" not in config["gamification"]:
        raise ConfigurationError("Gamification configuration must specify 'xp_per_level'")

    if config["gamification"]["xp_per_level"] <= 0:
        raise ConfigurationError("xp_per_level must be a positive integer")

    if "task_xp" not in config["gamification"]:
        raise ConfigurationError("Gamification configuration must specify 'task_xp'")

    task_xp = config["gamification"]["task_xp"]
    for priority in ["low", "medium", "high"]:
        if priority not in task_xp:
            raise ConfigurationError(f"task_xp must specify XP for '{priority}' priority")
        if not isinstance(task_xp[priority], int) or task_xp[priority] < 0:
            raise ConfigurationError(f"task_xp.{priority} must be a non-negative integer")

    if "default_duration" not in config["focus"]:
        raise ConfigurationError("Focus configuration must specify 'default_duration'")

    if config["focus"]["default_duration"] <= 0:
        raise ConfigurationError("default_duration must be a positive integer")


def load_env(env_path: str | None = None) -> bool:
    """Load environment variables from .env file.

    Args:
        env_path: Path to .env file. If None, uses '.env' in the current directory.

    Returns:
        True if .env file was found and loaded, False otherwise.

    Raises:
        ConfigurationError: If .env file exists but cannot be read.
    """
    if env_path is None:
        env_path = ".env"

    env_file = Path(env_path)

    if not env_file.exists():
        return False

    try:
        load_dotenv(env_path)
        return True
    except Exception as e:
        raise ConfigurationError(f"Failed to load environment variables: {e}") from e


def get_openai_api_key() -> str | None:
    """Get OpenAI API key from environment variables.

    Returns:
        OpenAI API key if set, None otherwise.
    """
    return os.getenv("OPENAI_API_KEY")
