"""
PyTest plugin for multi-database testing.

This module registers command-line options and fixtures for multi-database testing.
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
        "--enable-postgres-tests",
        action="store_true",
        default=False,
        help="Enable PostgreSQL-specific tests",
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
    except Exception as e:
        # If an error occurs, try to rollback the transaction
        if hasattr(db, "connection") and db.connection is not None:
            if hasattr(db.connection, "rollback"):
                db.connection.rollback()
        print(f"Error during cleanup: {e}")
    finally:
        # Close the connection
        db.close()


@pytest.fixture(scope="function")
def db_connection(db_interface) -> Generator[Union[sqlite3.Connection, psycopg2.extensions.connection], None, None]:
    """
    Get the underlying database connection.

    This fixture provides access to the underlying database connection
    for tests that need to use database-specific features.

    Args:
        db_interface: Database interface

    Yields:
        Connection: The underlying database connection
    """
    yield db_interface.connection


@pytest.fixture(scope="session")
def enable_postgres_tests(request) -> bool:
    """
    Check if PostgreSQL-specific tests should be enabled.

    This fixture provides a boolean value indicating whether
    PostgreSQL-specific tests should be enabled.

    Args:
        request: Pytest request object

    Returns:
        bool: True if PostgreSQL-specific tests should be enabled
    """
    return request.config.getoption("--enable-postgres-tests")


@pytest.fixture(scope="function")
def sample_data(db_interface):
    """
    Insert sample data into the database.

    This fixture inserts sample data into the database for testing.

    Args:
        db_interface: Database interface

    Returns:
        None
    """
    # Check if we're using PostgreSQL by looking at the db_type fixture
    # This is more reliable than checking the connection module
    db_type_value = db_interface.__class__.__name__

    if db_type_value == "PostgreSQLInterface":
        # For PostgreSQL, we need to handle the schema creation and data insertion differently
        # First, make sure the schema is created
        from src.database.schema_manager import get_schema_manager

        schema_manager = get_schema_manager(db_interface)
        schema_manager.create_tables()

        # Then insert data using PostgreSQL-compatible SQL
        # Insert customers without specifying customer_id
        customers = [
            ("John Smith", "john.smith@example.com", "555-123-4567"),
            ("Jane Doe", "jane.doe@example.com", "555-234-5678"),
            ("Bob Johnson", "bob.johnson@example.com", "555-345-6789"),
            ("Alice Brown", "alice.brown@example.com", "555-789-0123"),
            ("Charlie Davis", "charlie.davis@example.com", "555-321-6540"),
        ]

        for customer in customers:
            db_interface.execute("INSERT INTO customers (name, email, phone) VALUES (%s, %s, %s)", customer)

        # Get customer IDs
        results = db_interface.query("SELECT customer_id FROM customers")
        customer_ids = [row["customer_id"] for row in results]

        # Continue with the rest of the data insertion using test_data_helper functions
        from tests.test_data_helper import (
            insert_addresses,
            insert_campaigns,
            insert_inventory,
            insert_list_members,
            insert_mail_items,
            insert_mailing_lists,
            insert_materials,
            insert_print_jobs,
            insert_print_queue,
        )

        # Insert the rest of the data
        address_data = insert_addresses(db_interface, customer_ids)
        material_ids = insert_materials(db_interface)
        insert_inventory(db_interface, material_ids)
        list_ids = insert_mailing_lists(db_interface)
        insert_list_members(db_interface, list_ids, address_data)
        campaign_data = insert_campaigns(db_interface, list_ids)
        mail_item_ids = insert_mail_items(db_interface, campaign_data)
        job_ids = insert_print_jobs(db_interface)
        insert_print_queue(db_interface, job_ids, mail_item_ids)
    else:
        # For SQLite, use the existing test_data_helper
        from tests.test_data_helper import insert_test_data

        insert_test_data(db_interface)

    return None


def is_postgres(db_interface):
    """Check if the database is PostgreSQL."""
    return hasattr(db_interface.connection, "__module__") and "psycopg2" in db_interface.connection.__module__


def pytest_runtest_setup(item):
    """Skip tests marked with postgres_only when running with SQLite."""
    if "postgres_only" in item.keywords:
        db_type = item.config.getoption("--db-type")
        if db_type.lower() != "postgres" and db_type.lower() != "postgresql":
            pytest.skip("Test requires PostgreSQL")


@pytest.fixture(scope="function")
def postgres_procedures(db_interface):
    """Create PostgreSQL stored procedures for testing."""
    if is_postgres(db_interface):
        from src.database.postgres_procedures import create_stored_procedures

        create_stored_procedures(db_interface)
