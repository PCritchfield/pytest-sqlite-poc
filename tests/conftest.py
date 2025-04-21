"""
PyTest configuration and fixtures for SQLite testing.
"""
import sqlite3
from pathlib import Path
from typing import Union

import pytest

# Import sample data generation functions where needed
from src.database.connection import execute_script, get_connection
from src.database.functions import create_triggers, register_functions
from src.database.schema import create_tables


@pytest.fixture(scope="function")
def db_connection():
    """
    Create an in-memory SQLite database for testing.
    This fixture provides a fresh database for each test function.
    """
    # Create in-memory database
    conn = get_connection(":memory:", in_memory=True)

    # Create tables
    create_tables(conn)

    # Register custom functions
    register_functions(conn)

    # Create triggers
    create_triggers(conn)

    yield conn

    # Close connection after test
    conn.close()


@pytest.fixture(scope="function")
def db_with_schema():
    """
    Create an in-memory SQLite database with schema loaded from SQL file.
    """
    # Create in-memory database
    conn = get_connection(":memory:", in_memory=True)

    # Load schema from SQL file
    schema_path = Path(__file__).parent.parent / "data" / "sql" / "initial_schema.sql"
    execute_script(conn, schema_path)

    # Register custom functions
    register_functions(conn)

    # Create triggers
    create_triggers(conn)

    yield conn

    # Close connection after test
    conn.close()


@pytest.fixture(scope="function")
def db_with_sample_data(db_with_schema):
    """
    Create an in-memory SQLite database with sample data.

    Args:
        db_with_schema: Fixture that provides a database connection with schema
    """
    # Use the connection provided by the db_with_schema fixture
    db_connection = db_with_schema

    # Generate sample data for tests with the record count expected by tests
    generate_sample_data_for_tests(db_connection, record_count=5)

    # Create triggers (again after data insertion to ensure they're active)
    create_triggers(db_connection)

    yield db_connection


def insert_sample_data(conn: sqlite3.Connection) -> None:
    """Insert sample data into the database."""
    # Clear any existing data first
    tables = [
        "delivery_tracking",
        "print_queue",
        "mail_items",
        "print_jobs",
        "mailing_campaigns",
        "list_members",
        "mailing_lists",
        "inventory",
        "materials",
        "addresses",
        "customers",
    ]

    # Disable foreign key constraints temporarily for clean deletion
    conn.execute("PRAGMA foreign_keys = OFF")
    for table in tables:
        conn.execute(f"DELETE FROM {table}")
    conn.execute("PRAGMA foreign_keys = ON")

    # Reset auto-increment counters
    for table in tables:
        conn.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")

    # Insert customers
    customers = [
        (None, "John Smith", "john.smith@example.com", "555-123-4567"),
        (None, "Jane Doe", "jane.doe@example.com", "555-234-5678"),
        (None, "Bob Johnson", "bob.johnson@example.com", "555-345-6789"),
        (None, "Alice Brown", "alice.brown@example.com", "555-789-0123"),
        (None, "Charlie Davis", "charlie.davis@example.com", "555-321-6540"),
    ]
    conn.executemany(
        "INSERT INTO customers (customer_id, name, email, phone) VALUES (?, ?, ?, ?)",
        customers,
    )

    # Get customer IDs
    cursor = conn.cursor()
    cursor.execute("SELECT customer_id FROM customers")
    customer_ids = [row[0] for row in cursor.fetchall()]

    # Insert addresses
    addresses = []
    for customer_id in customer_ids:
        # Home address for every customer
        addresses.append(
            (
                None,
                customer_id,
                "home",
                f"{customer_id*123} Main St",
                None,
                "Anytown",
                "OH",
                f"{customer_id+10000}",
                "USA",
                1,
            )
        )

        # Work address for some customers
        if customer_id % 2 == 0:
            addresses.append(
                (
                    None,
                    customer_id,
                    "work",
                    f"{customer_id*100} Business Ave",
                    f"Suite {customer_id*10}",
                    "Workville",
                    "OH",
                    f"{customer_id+20000}",
                    "USA",
                    1,
                )
            )

    conn.executemany(
        "INSERT INTO addresses (address_id, customer_id, address_type, street_line1, street_line2, city, state, postal_code, country, is_verified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        addresses,
    )

    # Insert materials
    materials = [
        (None, "Standard Envelope", "Standard #10 business envelope", 0.05, "each"),
        (None, "Large Envelope", "9x12 manila envelope", 0.15, "each"),
        (None, "Standard Paper", "20lb 8.5x11 white paper", 0.02, "sheet"),
        (None, "Premium Paper", "24lb 8.5x11 ivory paper", 0.04, "sheet"),
        (None, "Ink - Black", "Black printer ink", 0.10, "page"),
    ]
    conn.executemany(
        "INSERT INTO materials (material_id, name, description, unit_cost, unit_type) VALUES (?, ?, ?, ?, ?)",
        materials,
    )

    # Get material IDs
    cursor.execute("SELECT material_id FROM materials")
    material_ids = [row[0] for row in cursor.fetchall()]

    # Insert inventory
    inventory = []
    for i, material_id in enumerate(material_ids):
        inventory.append(
            (
                None,
                material_id,
                (i + 1) * 1000,
                f"Warehouse {chr(65 + i % 3)}",  # A, B, or C
                "2025-01-15",
            )
        )

    conn.executemany(
        "INSERT INTO inventory (inventory_id, material_id, quantity, location, last_restock_date) VALUES (?, ?, ?, ?, ?)",
        inventory,
    )

    # Insert mailing lists
    mailing_lists = [
        (None, "Monthly Newsletter", "Subscribers to monthly newsletter", "admin"),
        (None, "Special Offers", "Customers interested in special offers", "marketing"),
        (None, "Product Updates", "Customers interested in product updates", "product"),
    ]
    conn.executemany(
        "INSERT INTO mailing_lists (list_id, name, description, created_by) VALUES (?, ?, ?, ?)",
        mailing_lists,
    )

    # Get list IDs and address IDs
    cursor.execute("SELECT list_id FROM mailing_lists")
    list_ids = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT address_id, customer_id FROM addresses")
    address_data = [(row[0], row[1]) for row in cursor.fetchall()]

    # Insert list members
    list_members = []
    for list_id in list_ids:
        for i, (address_id, customer_id) in enumerate(address_data):
            # Add some customers to each list (not all customers on all lists)
            if i % len(list_ids) == list_id % len(list_ids):
                list_members.append((None, list_id, customer_id, address_id, "active"))

    conn.executemany(
        "INSERT INTO list_members (member_id, list_id, customer_id, address_id, status) VALUES (?, ?, ?, ?, ?)",
        list_members,
    )

    # Insert mailing campaigns
    campaigns = []
    for i, list_id in enumerate(list_ids):
        start_date = f"2025-0{i+1}-01"
        end_date = f"2025-0{i+1}-28"
        status = "active" if i < 2 else "draft"

        campaigns.append(
            (
                None,
                f"Campaign {i+1}",
                f"Description for campaign {i+1}",
                list_id,
                start_date,
                end_date,
                status,
            )
        )

    conn.executemany(
        "INSERT INTO mailing_campaigns (campaign_id, name, description, list_id, start_date, end_date, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        campaigns,
    )

    # Get campaign IDs
    cursor.execute("SELECT campaign_id, list_id FROM mailing_campaigns")
    campaign_data = [(row[0], row[1]) for row in cursor.fetchall()]

    # Insert mail items
    mail_items = []
    for campaign_id, list_id in campaign_data:
        # Get members of this list
        cursor.execute(
            "SELECT customer_id, address_id FROM list_members WHERE list_id = ?",
            (list_id,),
        )
        members = cursor.fetchall()

        for customer_id, address_id in members:
            mail_items.append(
                (
                    None,
                    campaign_id,
                    customer_id,
                    address_id,
                    f"template_{campaign_id}",
                    "pending",
                )
            )

    conn.executemany(
        "INSERT INTO mail_items (item_id, campaign_id, customer_id, address_id, content_template, status) VALUES (?, ?, ?, ?, ?, ?)",
        mail_items,
    )

    # Get mail item IDs
    cursor.execute("SELECT item_id FROM mail_items")
    mail_item_ids = [row[0] for row in cursor.fetchall()]

    # Insert print jobs
    print_jobs = [
        (
            None,
            "January Newsletter Batch",
            "First batch of January newsletter",
            "queued",
            "2025-01-10",
            None,
            None,
        ),
        (
            None,
            "Winter Sale Preview",
            "Preview batch for winter sale",
            "queued",
            "2025-01-12",
            None,
            None,
        ),
    ]
    conn.executemany(
        "INSERT INTO print_jobs (job_id, name, description, status, scheduled_date, started_date, completed_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
        print_jobs,
    )

    # Get print job IDs
    cursor.execute("SELECT job_id FROM print_jobs")
    job_ids = [row[0] for row in cursor.fetchall()]

    # Insert print queue
    print_queue = []
    for i, item_id in enumerate(mail_item_ids):
        # Assign items to print jobs
        job_id = job_ids[i % len(job_ids)]
        print_queue.append((None, job_id, item_id, i + 1, "queued", None))

    conn.executemany(
        "INSERT INTO print_queue (queue_id, job_id, item_id, print_order, status, printed_at) VALUES (?, ?, ?, ?, ?, ?)",
        print_queue,
    )

    # Commit all changes
    conn.commit()


def create_sample_data(db_path: Union[str, Path]) -> None:
    """
    Create sample data in a SQLite database file.
    This function is used by the Taskfile to create sample data.

    Args:
        db_path: Path to the SQLite database file
    """
    conn = get_connection(db_path)
    insert_sample_data(conn)
    conn.close()
    print(f"Sample data created in {db_path}")


def generate_sample_data_for_tests(conn, record_count=3):
    """
    Generate sample data for tests using the connection provided by the fixture.
    This is a wrapper around the helper functions from sample_data.py,
    adapted for use with in-memory databases in tests.

    Args:
        conn: SQLite connection (in-memory)
        record_count: Number of records to generate (smaller for faster tests)
    """
    # Clear any existing data first
    tables = [
        "delivery_tracking",
        "print_queue",
        "mail_items",
        "print_jobs",
        "mailing_campaigns",
        "list_members",
        "mailing_lists",
        "inventory",
        "materials",
        "addresses",
        "customers",
    ]

    # Disable foreign key constraints temporarily for clean deletion
    conn.execute("PRAGMA foreign_keys = OFF")
    for table in tables:
        conn.execute(f"DELETE FROM {table}")
    conn.execute("PRAGMA foreign_keys = ON")

    # Reset auto-increment counters
    for table in tables:
        conn.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")

    # Import the helper functions from sample_data.py
    from data.sample_data import (
        generate_and_insert_addresses,
        generate_and_insert_campaigns,
        generate_and_insert_customers,
        generate_and_insert_delivery_tracking,
        generate_and_insert_inventory,
        generate_and_insert_list_members,
        generate_and_insert_mail_items,
        generate_and_insert_mailing_lists,
        generate_and_insert_materials,
        generate_and_insert_print_jobs,
        generate_and_insert_print_queue,
    )

    try:
        # Generate and insert data for each entity type
        # We use a smaller record count for faster test execution
        customer_ids = generate_and_insert_customers(conn, record_count)
        address_data = generate_and_insert_addresses(conn, customer_ids)
        material_ids = generate_and_insert_materials(conn)
        generate_and_insert_inventory(conn, material_ids)
        list_ids = generate_and_insert_mailing_lists(conn)
        list_members = generate_and_insert_list_members(
            conn, list_ids, customer_ids, address_data
        )
        campaign_ids = generate_and_insert_campaigns(conn, list_ids)
        mail_item_ids = generate_and_insert_mail_items(conn, campaign_ids, list_members)
        job_ids = generate_and_insert_print_jobs(conn)
        generate_and_insert_print_queue(conn, job_ids, mail_item_ids)
        generate_and_insert_delivery_tracking(conn, mail_item_ids)

        # Commit all changes
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e


def create_sample_data_legacy(db_path):
    """
    Create a database with sample data for external use.
    This function is maintained for backward compatibility but now uses
    the sample_data.py module's generate_sample_data function.

    Args:
        db_path: Path to the SQLite database file
    """
    # Import here to avoid circular imports
    from data.sample_data import generate_sample_data as gen_sample_data
    gen_sample_data(db_path)
    print(f"Sample data created in {db_path}")


@pytest.fixture(scope="function")
def migration_db():
    """
    Create an in-memory SQLite database for testing migrations.
    """
    # Create in-memory database
    conn = get_connection(":memory:", in_memory=True)

    # Create initial schema
    create_tables(conn)

    # Insert minimal data needed for migration tests
    customers = [
        (1, "John Smith", "john.smith@example.com", "555-123-4567"),
        (2, "Jane Doe", "jane.doe@example.com", None),  # Missing phone
    ]
    conn.executemany(
        "INSERT INTO customers (customer_id, name, email, phone) VALUES (?, ?, ?, ?)",
        customers,
    )

    # Insert addresses with mixed-case states
    addresses = [
        (1, 1, "home", "123 Main St", None, "Anytown", "oh", "12345", "USA", 1),
        (2, 2, "home", "789 Residential Rd", None, "Hometown", "Oh", "23456", "USA", 1),
    ]
    conn.executemany(
        "INSERT INTO addresses (address_id, customer_id, address_type, street_line1, street_line2, city, state, postal_code, country, is_verified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        addresses,
    )

    yield conn

    # Close connection after test
    conn.close()
