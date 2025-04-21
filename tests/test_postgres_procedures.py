"""
Tests for PostgreSQL stored procedures and functions.

This module contains tests for the PostgreSQL-specific stored procedures and functions.
These tests will be skipped if running with SQLite.
"""
import pytest

from src.database.postgres_procedures import (
    call_update_customer,
    create_stored_procedures,
    get_campaign_stats,
    validate_address,
)


def is_postgres(db_interface):
    """Check if the database is PostgreSQL."""
    # Check the class name first (most reliable)
    if db_interface.__class__.__name__ == "PostgreSQLInterface":
        return True
    # Fall back to the connection module check
    return hasattr(db_interface.connection, "__module__") and "psycopg2" in db_interface.connection.__module__


@pytest.fixture(scope="function")
def postgres_procedures(db_interface):
    """Create PostgreSQL stored procedures for testing."""
    if is_postgres(db_interface):
        create_stored_procedures(db_interface)


@pytest.mark.postgres_only
def test_update_customer_procedure(db_interface, postgres_procedures, sample_data, enable_postgres_tests):
    """Test the update_customer stored procedure."""
    if not is_postgres(db_interface):
        pytest.skip("Test requires PostgreSQL")

    # Skip if PostgreSQL tests are not explicitly enabled
    if not enable_postgres_tests:
        pytest.skip("Use --enable-postgres-tests to run this test")

    # Get a customer to update
    results = db_interface.query("SELECT customer_id, name, email, phone FROM customers LIMIT 1")
    customer = results[0]
    customer_id = customer["customer_id"]

    # Update the customer's name
    new_name = "Updated Customer Name"
    call_update_customer(db_interface, customer_id, name=new_name)

    # Verify the update
    results = db_interface.query("SELECT name FROM customers WHERE customer_id = %s", (customer_id,))
    assert results[0]["name"] == new_name

    # Update email and phone
    new_email = "updated@example.com"
    new_phone = "555-UPDATED"
    call_update_customer(db_interface, customer_id, email=new_email, phone=new_phone)

    # Verify the updates
    results = db_interface.query("SELECT email, phone FROM customers WHERE customer_id = %s", (customer_id,))
    # Check each field individually to better identify any issues
    actual_email = results[0]["email"]
    actual_phone = results[0]["phone"]
    assert actual_email == new_email, f"Expected email '{new_email}', got '{actual_email}'"
    assert actual_phone == new_phone, f"Expected phone '{new_phone}', got '{actual_phone}'"


@pytest.mark.postgres_only
def test_address_validation_function(db_interface, postgres_procedures, enable_postgres_tests):
    """Test the validate_address function."""
    if not is_postgres(db_interface):
        pytest.skip("Test requires PostgreSQL")

    # Skip if PostgreSQL tests are not explicitly enabled
    if not enable_postgres_tests:
        pytest.skip("Use --enable-postgres-tests to run this test")

    # Test valid address
    is_valid = validate_address(db_interface, "123 Main St", "Anytown", "OH", "12345")
    assert is_valid is True

    # Test invalid state (too long)
    is_valid = validate_address(db_interface, "123 Main St", "Anytown", "OHIO", "12345")
    assert is_valid is False

    # Test invalid postal code
    is_valid = validate_address(db_interface, "123 Main St", "Anytown", "OH", "1234")  # Too short
    assert is_valid is False


@pytest.mark.postgres_only
def test_state_normalization_trigger(db_interface, postgres_procedures, enable_postgres_tests):
    """Test the state normalization trigger."""
    if not is_postgres(db_interface):
        pytest.skip("Test requires PostgreSQL")

    # Skip if PostgreSQL tests are not explicitly enabled
    if not enable_postgres_tests:
        pytest.skip("Use --enable-postgres-tests to run this test")

    # Insert a customer first
    db_interface.execute(
        "INSERT INTO customers (name, email, phone) VALUES (%s, %s, %s)",
        ("Trigger Test", "trigger@example.com", "555-TRIG"),
    )

    # Get the customer ID
    results = db_interface.query("SELECT customer_id FROM customers WHERE email = %s", ("trigger@example.com",))
    customer_id = results[0]["customer_id"]

    # Insert an address with lowercase state
    db_interface.execute(
        """
        INSERT INTO addresses
        (customer_id, address_type, street_line1, city, state, postal_code, country, is_verified)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (customer_id, "home", "123 Trigger St", "Triggertown", "oh", "12345", "USA", True),
    )
    db_interface.commit()

    # Query for the address
    results = db_interface.query("SELECT state FROM addresses WHERE customer_id = %s", (customer_id,))

    # Verify the state was normalized to uppercase
    assert results[0]["state"] == "OH"


@pytest.mark.postgres_only
def test_campaign_stats_function(db_interface, postgres_procedures, sample_data, enable_postgres_tests):
    """Test the get_campaign_stats function."""
    if not is_postgres(db_interface):
        pytest.skip("Test requires PostgreSQL")

    # Skip if PostgreSQL tests are not explicitly enabled
    if not enable_postgres_tests:
        pytest.skip("Use --enable-postgres-tests to run this test")

    # Get a campaign ID
    results = db_interface.query("SELECT campaign_id FROM mailing_campaigns LIMIT 1")
    campaign_id = results[0]["campaign_id"]

    # Get the campaign stats
    stats = get_campaign_stats(db_interface, campaign_id)

    # Verify the structure of the stats
    assert "campaign_name" in stats
    assert "total_items" in stats
    assert "pending_items" in stats
    assert "printed_items" in stats
    assert "delivered_items" in stats
    assert "success_rate" in stats

    # Verify that the total items matches what we expect
    mail_items_count = db_interface.query(
        "SELECT COUNT(*) as count FROM mail_items WHERE campaign_id = %s", (campaign_id,)
    )
    assert stats["total_items"] == mail_items_count[0]["count"]
