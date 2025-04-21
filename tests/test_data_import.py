"""
Tests for data import functionality.
"""
import json
import sqlite3

import pytest

from src.database.connection import execute_query


def test_connection_creation(db_connection):
    """Test that the database connection is created successfully."""
    # Simply check that the connection is a SQLite connection
    assert isinstance(db_connection, sqlite3.Connection)

    # Verify foreign keys are enabled
    cursor = db_connection.cursor()
    cursor.execute("PRAGMA foreign_keys")
    result = cursor.fetchone()
    cursor.close()

    assert result[0] == 1


def test_tables_exist(db_connection):
    """Test that all expected tables are created in the database."""
    # Get list of all tables
    cursor = db_connection.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()

    # Check for expected tables
    expected_tables = [
        "customers",
        "addresses",
        "materials",
        "inventory",
        "mailing_lists",
        "list_members",
        "mailing_campaigns",
        "mail_items",
        "print_jobs",
        "print_queue",
        "delivery_tracking",
    ]

    for table in expected_tables:
        assert table in tables, f"Table {table} not found in database"


def test_sample_data_import(db_with_sample_data):
    """Test that sample data is imported correctly."""
    # Check customer count
    cursor = db_with_sample_data.cursor()
    cursor.execute("SELECT COUNT(*) FROM customers")
    count = cursor.fetchone()[0]
    cursor.close()

    assert count == 5, "Expected 5 customers in sample data"

    # Check that customers have the expected structure
    result = execute_query(db_with_sample_data, "SELECT * FROM customers LIMIT 1")

    assert len(result) == 1, "Expected to find at least one customer"

    # Verify customer has all required fields
    customer = result[0]
    assert "name" in customer and customer["name"], "Customer should have a name"
    assert "email" in customer and customer["email"], "Customer should have an email"
    assert (
        "phone" in customer and customer["phone"]
    ), "Customer should have a phone number"
    assert "@" in customer["email"], "Email should be in valid format"

    # Check that email addresses are unique
    cursor = db_with_sample_data.cursor()
    cursor.execute("SELECT COUNT(DISTINCT email) FROM customers")
    unique_emails = cursor.fetchone()[0]
    cursor.close()

    assert unique_emails == count, "All customer emails should be unique"


def test_foreign_key_constraints(db_with_sample_data):
    """Test that foreign key constraints are enforced."""
    # Make sure foreign keys are enabled
    db_with_sample_data.execute("PRAGMA foreign_keys = ON")

    # Try to insert an address with a non-existent customer_id
    with pytest.raises(sqlite3.IntegrityError) as excinfo:
        db_with_sample_data.execute(
            "INSERT INTO addresses (customer_id, address_type, street_line1, city, state, postal_code, country) "
            "VALUES (999, 'home', '123 Test St', 'Test City', 'TS', '12345', 'USA')"
        )
        db_with_sample_data.commit()  # Need to commit to trigger the constraint

    # Verify the error is due to foreign key constraint
    assert "FOREIGN KEY constraint failed" in str(excinfo.value)


def test_import_from_json(db_connection, tmp_path):
    """Test importing data from a JSON file."""
    # Create a temporary JSON file with customer data
    customers_data = [
        {
            "name": "Test Customer 1",
            "email": "test1@example.com",
            "phone": "555-111-2222",
        },
        {
            "name": "Test Customer 2",
            "email": "test2@example.com",
            "phone": "555-333-4444",
        },
    ]

    json_file = tmp_path / "test_customers.json"
    with open(json_file, "w") as f:
        json.dump(customers_data, f)

    # Import the data
    cursor = db_connection.cursor()

    # Read JSON file
    with open(json_file, "r") as f:
        data = json.load(f)

    # Insert data
    for customer in data:
        cursor.execute(
            "INSERT INTO customers (name, email, phone) VALUES (?, ?, ?)",
            (customer["name"], customer["email"], customer["phone"]),
        )

    db_connection.commit()
    cursor.close()

    # Verify the data was imported
    result = execute_query(db_connection, "SELECT * FROM customers")

    assert len(result) == 2, "Expected 2 customers to be imported"
    assert result[0]["name"] == "Test Customer 1"
    assert result[1]["email"] == "test2@example.com"


def test_multiple_table_relationships(db_with_sample_data):
    """Test relationships between multiple tables."""
    # First, find a campaign ID that has mail items
    query_campaign = """
    SELECT campaign_id, COUNT(item_id) as item_count
    FROM mail_items
    GROUP BY campaign_id
    ORDER BY item_count DESC
    LIMIT 1
    """

    campaign_results = execute_query(db_with_sample_data, query_campaign)
    assert (
        len(campaign_results) > 0
    ), "Should have at least one campaign with mail items"

    campaign_id = campaign_results[0]["campaign_id"]

    # Query to join customers, addresses, and mail_items
    query = f"""
    SELECT c.name, a.city, a.state, mi.content_template
    FROM mail_items mi
    JOIN customers c ON mi.customer_id = c.customer_id
    JOIN addresses a ON mi.address_id = a.address_id
    WHERE mi.campaign_id = {campaign_id}
    """

    results = execute_query(db_with_sample_data, query)

    # Verify we have results
    assert len(results) > 0, f"Expected mail items for campaign {campaign_id}"

    # Check that we can access data across related tables
    for result in results:
        assert result["name"] is not None, "Customer name should not be null"
        assert result["city"] is not None, "City should not be null"
        assert result["state"] is not None, "State should not be null"
        assert (
            result["content_template"] is not None
        ), "Content template should not be null"
