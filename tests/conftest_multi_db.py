"""
PyTest configuration and fixtures for multi-database testing.

This module provides fixtures for testing with both SQLite and PostgreSQL databases.
"""
import sqlite3
from typing import Generator, Union

import psycopg2
import pytest

from src.database.db_interface import DatabaseInterface, get_db_interface
from src.database.schema_manager import get_schema_manager


def pytest_addoption(parser):
    """Add command-line options for database testing."""
    parser.addoption(
        "--db-type",
        action="store",
        default="sqlite",
        help="Database type to test against: sqlite or postgres",
    )
    parser.addoption(
        "--pg-host",
        action="store",
        default="localhost",
        help="PostgreSQL host",
    )
    parser.addoption(
        "--pg-port",
        action="store",
        default=5432,
        type=int,
        help="PostgreSQL port",
    )
    parser.addoption(
        "--pg-user",
        action="store",
        default="postgres",
        help="PostgreSQL username",
    )
    parser.addoption(
        "--pg-password",
        action="store",
        default="postgres",
        help="PostgreSQL password",
    )
    parser.addoption(
        "--pg-dbname",
        action="store",
        default="test_mail_system",
        help="PostgreSQL database name",
    )


@pytest.fixture(scope="session")
def db_type(request):
    """Get the database type from command line options."""
    return request.config.getoption("--db-type")


@pytest.fixture(scope="session")
def pg_config(request):
    """Get PostgreSQL configuration from command line options."""
    return {
        "host": request.config.getoption("--pg-host"),
        "port": request.config.getoption("--pg-port"),
        "user": request.config.getoption("--pg-user"),
        "password": request.config.getoption("--pg-password"),
        "dbname": request.config.getoption("--pg-dbname"),
    }


@pytest.fixture(scope="function")
def db_interface(db_type, pg_config) -> Generator[DatabaseInterface, None, None]:
    """
    Create a database interface for testing.

    This fixture creates a database interface based on the specified database type.
    For SQLite, it creates an in-memory database.
    For PostgreSQL, it connects to the specified database.

    Args:
        db_type: Database type ('sqlite' or 'postgres')
        pg_config: PostgreSQL configuration

    Yields:
        DatabaseInterface: A database interface for testing
    """
    if db_type.lower() == "sqlite":
        # Create an in-memory SQLite database
        db = get_db_interface("sqlite", db_path=":memory:", in_memory=True)
    elif db_type.lower() in ("postgres", "postgresql"):
        # Create a PostgreSQL database
        db = get_db_interface("postgres", **pg_config)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

    # Connect to the database
    db.connect()

    # Create the schema
    schema_manager = get_schema_manager(db)
    schema_manager.create_tables()

    # Yield the database interface to the test
    yield db

    # Clean up after the test
    try:
        # Drop all tables
        schema_manager.drop_tables()
    finally:
        # Close the connection
        db.close()


@pytest.fixture(scope="function")
def db_connection(db_interface) -> Generator[Union[sqlite3.Connection, psycopg2.extensions.connection], None, None]:
    """
    Get the underlying database connection for testing.

    This fixture provides the raw database connection object for tests that need it.

    Args:
        db_interface: Database interface

    Yields:
        Union[sqlite3.Connection, psycopg2.extensions.connection]: The underlying database connection
    """
    yield db_interface.connection


@pytest.fixture(scope="function")
def sample_data(db_interface) -> None:
    """
    Insert sample data into the database for testing.

    This fixture inserts a standard set of test data into the database.

    Args:
        db_interface: Database interface
    """
    # Import here to avoid circular imports
    from tests.test_data_helper import insert_test_data

    # Insert the test data
    insert_test_data(db_interface)
