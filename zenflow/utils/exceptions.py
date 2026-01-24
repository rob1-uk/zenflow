"""Custom exception classes for ZenFlow.

This module defines all custom exceptions used throughout the application
for better error handling and user feedback.
"""


class ZenFlowError(Exception):
    """Base exception class for all ZenFlow errors.

    All custom exceptions in ZenFlow should inherit from this base class.
    This allows for catching all ZenFlow-specific errors with a single
    except clause if needed.
    """

    pass


class DatabaseError(ZenFlowError):
    """Exception raised for database-related errors.

    This includes connection failures, query errors, constraint violations,
    and other database operation failures.

    Examples:
        - Failed to connect to database
        - SQL query execution failed
        - Foreign key constraint violation
        - Table not found
    """

    pass


class ValidationError(ZenFlowError):
    """Exception raised for data validation errors.

    This is raised when user input or data fails validation checks,
    such as invalid priority values, malformed dates, or missing
    required fields.

    Examples:
        - Invalid priority (not LOW/MEDIUM/HIGH)
        - Invalid frequency (not DAILY/WEEKLY)
        - Invalid date format
        - Empty required field
        - Invalid XP value
    """

    pass


class ConfigurationError(ZenFlowError):
    """Exception raised for configuration-related errors.

    This includes missing or malformed configuration files, invalid
    configuration values, and missing required environment variables.

    Examples:
        - config.yaml not found
        - Invalid YAML syntax
        - Missing required configuration key
        - Invalid configuration value type
        - Missing .env file when AI features enabled
    """

    pass


class APIError(ZenFlowError):
    """Exception raised for external API errors.

    This is used for errors when interacting with external APIs,
    primarily the OpenAI API for AI insights.

    Examples:
        - API authentication failure
        - API rate limit exceeded
        - API request timeout
        - Invalid API response
        - Network connectivity issues
    """

    pass
