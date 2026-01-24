"""Database connection and query management for ZenFlow.

This module provides the Database class for SQLite operations with
connection management, query execution, and schema initialization.
"""

import sqlite3
from typing import Any

from zenflow.database.models import (
    ALL_INDEXES,
    ALL_TABLES,
    PRAGMA_FOREIGN_KEYS,
)


class Database:
    """SQLite database connection manager with query methods.

    Provides connection management, query execution, and context manager
    support for database operations. Automatically configures row factory
    for dict-like access to query results.

    Args:
        db_path: Path to SQLite database file (or ':memory:' for in-memory)

    Example:
        >>> with Database('zenflow.db') as db:
        ...     db.initialize_schema()
        ...     result = db.fetch_one("SELECT * FROM users WHERE id = ?", (1,))
    """

    def __init__(self, db_path: str) -> None:
        """Initialize Database with path to SQLite file.

        Args:
            db_path: Path to SQLite database file or ':memory:' for in-memory db
        """
        self.db_path: str = db_path
        self.conn: sqlite3.Connection | None = None
        self.cursor: sqlite3.Cursor | None = None

    def connect(self) -> None:
        """Establish connection to SQLite database.

        Sets up connection with row factory for dict-like access to results.
        Enables foreign key constraints.

        Raises:
            sqlite3.Error: If connection fails
        """
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access
        self.cursor = self.conn.cursor()
        # Enable foreign key constraints
        self.cursor.execute(PRAGMA_FOREIGN_KEYS)
        self.conn.commit()

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        """Execute a SQL query with parameters.

        Args:
            query: SQL query string with ? placeholders
            params: Tuple of parameters to bind to query

        Returns:
            Cursor object with query results

        Raises:
            sqlite3.Error: If query execution fails
            RuntimeError: If not connected to database
        """
        if self.cursor is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.cursor.execute(query, params)

    def fetch_one(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        """Execute query and fetch one result row.

        Args:
            query: SQL query string with ? placeholders
            params: Tuple of parameters to bind to query

        Returns:
            Row object (dict-like) or None if no results

        Raises:
            sqlite3.Error: If query execution fails
            RuntimeError: If not connected to database
        """
        self.execute(query, params)
        if self.cursor is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        result = self.cursor.fetchone()
        return result  # type: ignore[no-any-return]

    def fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        """Execute query and fetch all result rows.

        Args:
            query: SQL query string with ? placeholders
            params: Tuple of parameters to bind to query

        Returns:
            List of Row objects (dict-like), empty list if no results

        Raises:
            sqlite3.Error: If query execution fails
            RuntimeError: If not connected to database
        """
        self.execute(query, params)
        if self.cursor is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.cursor.fetchall()

    def commit(self) -> None:
        """Commit current transaction to database.

        Raises:
            RuntimeError: If not connected to database
        """
        if self.conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        self.conn.commit()

    def close(self) -> None:
        """Close database connection and cursor.

        Safe to call multiple times. Does nothing if already closed.
        """
        if self.cursor is not None:
            self.cursor.close()
            self.cursor = None
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def initialize_schema(self) -> None:
        """Create all database tables and indexes.

        Creates all tables defined in models.py if they don't exist.
        Creates all indexes for query optimization.
        Safe to call multiple times (uses IF NOT EXISTS).

        Raises:
            sqlite3.Error: If schema creation fails
            RuntimeError: If not connected to database
        """
        if self.cursor is None or self.conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        # Create all tables
        for table_sql in ALL_TABLES:
            self.cursor.execute(table_sql)

        # Create all indexes
        for index_sql in ALL_INDEXES:
            self.cursor.execute(index_sql)

        self.conn.commit()

    def __enter__(self) -> "Database":
        """Context manager entry: connect to database.

        Returns:
            Self for use in with statement
        """
        self.connect()
        return self

    def __exit__(
        self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any | None
    ) -> None:
        """Context manager exit: commit and close database connection.

        Args:
            exc_type: Exception type if exception occurred
            exc_val: Exception value if exception occurred
            exc_tb: Exception traceback if exception occurred
        """
        if exc_type is None and self.conn is not None:
            # No exception occurred, commit the transaction
            self.conn.commit()
        self.close()
