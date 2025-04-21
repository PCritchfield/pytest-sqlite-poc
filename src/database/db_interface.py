"""
Database interface for multiple database backends.

This module provides an abstraction layer for working with different database backends
(currently SQLite and PostgreSQL).
"""
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import psycopg2
from psycopg2.extras import RealDictCursor


class DatabaseInterface(ABC):
    """Abstract base class for database interfaces."""

    @abstractmethod
    def connect(self) -> None:
        """Establish a connection to the database."""

    @abstractmethod
    def close(self) -> None:
        """Close the database connection."""

    @abstractmethod
    def execute(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> None:
        """
        Execute a SQL query without returning results.

        Args:
            query: SQL query string
            params: Query parameters
        """

    @abstractmethod
    def execute_many(self, query: str, params_list: List[Tuple[Any, ...]]) -> None:
        """
        Execute a SQL query multiple times with different parameters.

        Args:
            query: SQL query string
            params_list: List of parameter tuples
        """

    @abstractmethod
    def query(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return the results.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of results as dictionaries
        """

    @abstractmethod
    def execute_script(self, script: str) -> None:
        """
        Execute a SQL script.

        Args:
            script: SQL script string
        """

    @abstractmethod
    def commit(self) -> None:
        """Commit the current transaction."""

    @abstractmethod
    def rollback(self) -> None:
        """Roll back the current transaction."""

    @property
    @abstractmethod
    def connection(self) -> Any:
        """Get the underlying database connection object."""


class SQLiteInterface(DatabaseInterface):
    """SQLite implementation of the database interface."""

    def __init__(self, db_path: Union[str, Path], in_memory: bool = False):
        """
        Initialize a SQLite database interface.

        Args:
            db_path: Path to the SQLite database file
            in_memory: If True, create an in-memory database instead of using the file
        """
        self.db_path = db_path
        self.in_memory = in_memory
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        """Establish a connection to the SQLite database."""
        if self.in_memory:
            self._conn = sqlite3.connect(":memory:")
        else:
            db_path = Path(self.db_path)
            self._conn = sqlite3.connect(str(db_path))

        # Enable foreign keys
        if self._conn is not None:
            self._conn.execute("PRAGMA foreign_keys = ON")

            # Return rows as dictionaries
            self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        """Close the SQLite database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def execute(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> None:
        """
        Execute a SQL query without returning results.

        Args:
            query: SQL query string
            params: Query parameters
        """
        if not self._conn:
            self.connect()

        if self._conn is None:
            raise RuntimeError("Database connection could not be established")

        # Convert %s placeholders to ? for SQLite
        query = query.replace("%s", "?")

        if params:
            self._conn.execute(query, params)
        else:
            self._conn.execute(query)

    def execute_many(self, query: str, params_list: List[Tuple[Any, ...]]) -> None:
        """
        Execute a SQL query multiple times with different parameters.

        Args:
            query: SQL query string
            params_list: List of parameter tuples
        """
        if not self._conn:
            self.connect()

        if self._conn is None:
            raise RuntimeError("Database connection could not be established")

        # Convert %s placeholders to ? for SQLite
        query = query.replace("%s", "?")

        self._conn.executemany(query, params_list)

    def query(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return the results.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of results as dictionaries
        """
        if not self._conn:
            self.connect()

        if self._conn is None:
            raise RuntimeError("Database connection could not be established")

        # Convert %s placeholders to ? for SQLite
        query = query.replace("%s", "?")

        cursor = self._conn.cursor()

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        results = cursor.fetchall()
        cursor.close()

        # Convert row objects to dictionaries and handle boolean fields
        result_dicts = []
        for row in results:
            row_dict = dict(row)

            # Convert integer values to booleans for known boolean fields
            if "is_verified" in row_dict and row_dict["is_verified"] is not None:
                row_dict["is_verified"] = bool(row_dict["is_verified"])

            result_dicts.append(row_dict)

        return result_dicts

    def execute_script(self, script: str) -> None:
        """
        Execute a SQL script.

        Args:
            script: SQL script string
        """
        if not self._conn:
            self.connect()

        if self._conn is None:
            raise RuntimeError("Database connection could not be established")

        self._conn.executescript(script)

    def commit(self) -> None:
        """Commit the current transaction."""
        if self._conn:
            self._conn.commit()

    def rollback(self) -> None:
        """Roll back the current transaction."""
        if self._conn:
            self._conn.rollback()

    @property
    def connection(self) -> sqlite3.Connection:
        """Get the underlying SQLite connection object."""
        if not self._conn:
            self.connect()
        return self._conn


class PostgreSQLInterface(DatabaseInterface):
    """PostgreSQL implementation of the database interface."""

    def __init__(
        self,
        dbname: str,
        user: str,
        password: str,
        host: str = "localhost",
        port: int = 5432,
    ) -> None:
        """
        Initialize a PostgreSQL database interface.

        Args:
            dbname: Database name
            user: Username
            password: Password
            host: Host address
            port: Port number
        """
        self.dbname = dbname
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self._conn: Optional[Any] = None

    def connect(self) -> None:
        """Establish a connection to the PostgreSQL database."""
        self._conn = psycopg2.connect(
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
        )

    def close(self) -> None:
        """Close the PostgreSQL database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def execute(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> None:
        """
        Execute a SQL query without returning results.

        Args:
            query: SQL query string
            params: Query parameters
        """
        if not self._conn:
            self.connect()

        if self._conn is None:
            raise RuntimeError("Database connection could not be established")

        try:
            with self._conn.cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
        except Exception:
            # If an error occurs, rollback the transaction
            if hasattr(self._conn, "rollback"):
                self._conn.rollback()
            # Re-raise the exception
            raise

    def execute_many(self, query: str, params_list: List[Tuple[Any, ...]]) -> None:
        """
        Execute a SQL query multiple times with different parameters.

        Args:
            query: SQL query string
            params_list: List of parameter tuples
        """
        if not self._conn:
            self.connect()

        if self._conn is None:
            raise RuntimeError("Database connection could not be established")

        try:
            with self._conn.cursor() as cursor:
                cursor.executemany(query, params_list)
        except Exception:
            # If an error occurs, rollback the transaction
            if hasattr(self._conn, "rollback"):
                self._conn.rollback()
            # Re-raise the exception
            raise

    def query(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return the results.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of results as dictionaries
        """
        if not self._conn:
            self.connect()

        if self._conn is None:
            raise RuntimeError("Database connection could not be established")

        try:
            with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                results = cursor.fetchall()

            # Results are already dictionaries with RealDictCursor
            return list(results)
        except Exception:
            # If an error occurs, rollback the transaction
            if hasattr(self._conn, "rollback"):
                self._conn.rollback()
            # Re-raise the exception
            raise

    def execute_script(self, script: str) -> None:
        """
        Execute a SQL script.

        Args:
            script: SQL script string
        """
        if not self._conn:
            self.connect()

        if self._conn is None:
            raise RuntimeError("Database connection could not be established")

        try:
            # PostgreSQL doesn't have a direct equivalent to executescript,
            # so we split the script and execute each statement
            with self._conn.cursor() as cursor:
                cursor.execute(script)
        except Exception:
            # If an error occurs, rollback the transaction
            if hasattr(self._conn, "rollback"):
                self._conn.rollback()
            # Re-raise the exception
            raise

    def commit(self) -> None:
        """Commit the current transaction."""
        if self._conn:
            self._conn.commit()

    def rollback(self) -> None:
        """Roll back the current transaction."""
        if self._conn:
            self._conn.rollback()

    @property
    def connection(self) -> psycopg2.extensions.connection:
        """Get the underlying PostgreSQL connection object."""
        if not self._conn:
            self.connect()
        return self._conn


def get_db_interface(db_type: str, **kwargs) -> DatabaseInterface:
    """
    Factory function to create a database interface.

    Args:
        db_type: Type of database ('sqlite' or 'postgres')
        **kwargs: Additional arguments for the specific database interface

    Returns:
        A DatabaseInterface implementation
    """
    if db_type.lower() == "sqlite":
        return SQLiteInterface(**kwargs)
    elif db_type.lower() in ("postgres", "postgresql"):
        return PostgreSQLInterface(**kwargs)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
