"""
Tests for complex chained stored procedures with branching execution paths.

This module tests the complex stored procedures that demonstrate chained execution
with branching paths for the mail printing and stuffing system.
"""
from datetime import date, timedelta

import pytest

from src.database.complex_procedures import call_process_campaign, create_complex_procedures, get_audit_logs


def clear_audit_logs(db_interface):
    """Clear all audit logs from the database."""
    # First check if the table exists (it's created by the complex_procedures fixture)
    tables = db_interface.query(
        """SELECT table_name FROM information_schema.tables
           WHERE table_schema = 'public' AND table_name = 'audit_log'"""
    )

    if tables and len(tables) > 0:
        # Table exists, clear it
        db_interface.execute("DELETE FROM audit_log")


def setup_campaign_data(db_interface, campaign_name, status="active"):
    """Set up test data for a campaign with mail items."""
    # Create a customer
    db_interface.execute(
        "INSERT INTO customers (name, email, phone) VALUES (%s, %s, %s)",
        ("Test Customer", "test@example.com", "555-TEST"),
    )
    customer_id = db_interface.query("SELECT customer_id FROM customers LIMIT 1")[0]["customer_id"]

    # Create an address
    db_interface.execute(
        """
        INSERT INTO addresses
        (customer_id, address_type, street_line1, city, state, postal_code, country)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (customer_id, "shipping", "123 Test St", "Testville", "TS", "12345", "USA"),
    )
    address_id = db_interface.query("SELECT address_id FROM addresses LIMIT 1")[0]["address_id"]

    # Create a mailing list
    db_interface.execute(
        "INSERT INTO mailing_lists (name, description, created_by) VALUES (%s, %s, %s)",
        ("Test List", "List for testing", "Test User"),
    )
    list_id = db_interface.query("SELECT list_id FROM mailing_lists LIMIT 1")[0]["list_id"]

    # Add the customer to the mailing list
    db_interface.execute(
        "INSERT INTO list_members (list_id, customer_id, address_id, status) VALUES (%s, %s, %s, %s)",
        (list_id, customer_id, address_id, "active"),
    )

    # Create a campaign
    db_interface.execute(
        """
        INSERT INTO mailing_campaigns
        (name, description, list_id, start_date, end_date, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            campaign_name,
            "Campaign for testing complex procedures",
            list_id,
            date.today(),
            date.today() + timedelta(days=30),
            status,
        ),
    )
    campaign_id = db_interface.query("SELECT campaign_id FROM mailing_campaigns LIMIT 1")[0]["campaign_id"]

    # Create mail items for the campaign
    for i in range(5):
        db_interface.execute(
            """
            INSERT INTO mail_items
            (campaign_id, customer_id, address_id, content_template, status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (campaign_id, customer_id, address_id, f"Test content template {i}", "pending"),
        )

    return campaign_id


@pytest.fixture(scope="function")
def complex_procedures(db_interface):
    """Create complex stored procedures for testing."""
    # Check if we're using PostgreSQL directly by class name
    if db_interface.__class__.__name__ == "PostgreSQLInterface":
        create_complex_procedures(db_interface)


@pytest.mark.postgres_only
def test_process_standard_campaign(db_interface, complex_procedures, enable_postgres_tests):
    """Test processing a standard campaign through the chained procedures."""
    # Check if we're using PostgreSQL directly by class name
    if db_interface.__class__.__name__ != "PostgreSQLInterface":
        pytest.skip("Test requires PostgreSQL")

    if not enable_postgres_tests:
        pytest.skip("Use --enable-postgres-tests to run this test")

    # Clear audit logs before test
    clear_audit_logs(db_interface)

    # Set up test data for a standard campaign
    campaign_id = setup_campaign_data(db_interface, "Standard Test Campaign")

    # Process the campaign
    call_process_campaign(db_interface, campaign_id)

    # Verify the campaign status was updated
    campaign = db_interface.query("SELECT status FROM mailing_campaigns WHERE campaign_id = %s", (campaign_id,))[0]
    assert campaign["status"] == "processed", "Campaign status should be 'processed'"

    # Verify mail items were processed
    mail_items = db_interface.query("SELECT status FROM mail_items WHERE campaign_id = %s", (campaign_id,))
    for item in mail_items:
        assert item["status"] == "processing", "Mail items should be in 'processing' status"

    # Verify print job was created
    print_jobs = db_interface.query("SELECT * FROM print_jobs WHERE name LIKE %s", (f"%Campaign {campaign_id}%",))
    assert len(print_jobs) == 1, "A print job should be created"
    assert print_jobs[0]["status"] == "pending", "Print job status should be 'pending'"
    assert print_jobs[0]["scheduled_date"] == date.today() + timedelta(
        days=1
    ), "Standard job should be scheduled for tomorrow"

    # Verify items were added to print queue
    print_queue = db_interface.query("SELECT * FROM print_queue WHERE job_id = %s", (print_jobs[0]["job_id"],))
    assert len(print_queue) == 5, "All 5 mail items should be in the print queue"

    # Verify delivery tracking was created
    delivery_tracking = db_interface.query(
        """
        SELECT dt.* FROM delivery_tracking dt
        JOIN mail_items mi ON dt.item_id = mi.item_id
        WHERE mi.campaign_id = %s
        """,
        (campaign_id,),
    )
    assert len(delivery_tracking) == 5, "All 5 mail items should have delivery tracking"

    # Verify all items have standard delivery
    for tracking in delivery_tracking:
        assert tracking["carrier"] == "Standard Post", "Standard campaign should use Standard Post"
        assert tracking["estimated_delivery_date"] == date.today() + timedelta(
            days=5
        ), "Standard delivery should take 5 days"

    # Verify audit logs were created
    audit_logs = get_audit_logs(db_interface, campaign_id)

    # Check for specific log entries in the correct sequence
    log_actions = [log["action"] for log in audit_logs]
    assert "CAMPAIGN_PROCESSING_STARTED" in log_actions, "Campaign processing started should be logged"
    assert "STANDARD_MAIL_PROCESSING_STARTED" in log_actions, "Standard mail processing should be logged"
    assert "STANDARD_MAIL_PROCESSING_COMPLETED" in log_actions, "Standard mail completion should be logged"
    assert "CAMPAIGN_PROCESSING_COMPLETED" in log_actions, "Campaign completion should be logged"


@pytest.mark.postgres_only
def test_process_priority_campaign(db_interface, complex_procedures, enable_postgres_tests):
    """Test processing a priority campaign through the chained procedures."""
    # Check if we're using PostgreSQL directly by class name
    if db_interface.__class__.__name__ != "PostgreSQLInterface":
        pytest.skip("Test requires PostgreSQL")

    if not enable_postgres_tests:
        pytest.skip("Use --enable-postgres-tests to run this test")

    # Clear audit logs before test
    clear_audit_logs(db_interface)

    # Set up test data for a priority campaign
    campaign_id = setup_campaign_data(db_interface, "Priority Test Campaign")

    # Process the campaign
    call_process_campaign(db_interface, campaign_id)

    # Verify the campaign status was updated
    campaign = db_interface.query("SELECT status FROM mailing_campaigns WHERE campaign_id = %s", (campaign_id,))[0]
    assert campaign["status"] == "processed", "Campaign status should be 'processed'"

    # Verify print job was created with priority settings
    print_jobs = db_interface.query("SELECT * FROM print_jobs WHERE name LIKE %s", (f"%Campaign {campaign_id}%",))
    assert len(print_jobs) == 1, "A print job should be created"
    assert print_jobs[0]["scheduled_date"] == date.today(), "Priority job should be scheduled for today"

    # Verify items were added to print queue with priority order
    print_queue = db_interface.query(
        "SELECT * FROM print_queue WHERE job_id = %s ORDER BY print_order", (print_jobs[0]["job_id"],)
    )
    assert len(print_queue) == 5, "All 5 mail items should be in the print queue"
    assert print_queue[0]["print_order"] == 10, "Priority items should have low print_order values"

    # Verify delivery tracking was created with expedited shipping
    delivery_tracking = db_interface.query(
        """
        SELECT dt.* FROM delivery_tracking dt
        JOIN mail_items mi ON dt.item_id = mi.item_id
        WHERE mi.campaign_id = %s
        """,
        (campaign_id,),
    )
    assert len(delivery_tracking) == 5, "All 5 mail items should have delivery tracking"

    # Verify all items have expedited delivery
    for tracking in delivery_tracking:
        assert tracking["carrier"] == "Express Courier", "Priority campaign should use Express Courier"
        assert tracking["estimated_delivery_date"] == date.today() + timedelta(
            days=1
        ), "Expedited delivery should take 1 day"

    # Verify audit logs show priority processing
    audit_logs = get_audit_logs(db_interface, campaign_id)
    log_actions = [log["action"] for log in audit_logs]
    assert "PRIORITY_MAIL_PROCESSING_STARTED" in log_actions, "Priority mail processing should be logged"


@pytest.mark.postgres_only
def test_inactive_campaign_skipped(db_interface, complex_procedures, enable_postgres_tests):
    """Test that inactive campaigns are skipped by the procedure chain."""
    # Check if we're using PostgreSQL directly by class name
    if db_interface.__class__.__name__ != "PostgreSQLInterface":
        pytest.skip("Test requires PostgreSQL")

    if not enable_postgres_tests:
        pytest.skip("Use --enable-postgres-tests to run this test")

    # Clear audit logs before test
    clear_audit_logs(db_interface)

    # Set up test data for an inactive campaign
    campaign_id = setup_campaign_data(db_interface, "Inactive Campaign", status="draft")

    # Process the campaign
    call_process_campaign(db_interface, campaign_id)

    # Verify the campaign status was not changed
    campaign = db_interface.query("SELECT status FROM mailing_campaigns WHERE campaign_id = %s", (campaign_id,))[0]
    assert campaign["status"] == "draft", "Inactive campaign status should remain 'draft'"

    # Verify no print jobs were created
    print_jobs = db_interface.query(
        "SELECT COUNT(*) as count FROM print_jobs WHERE name LIKE %s", (f"%Campaign {campaign_id}%",)
    )
    assert print_jobs[0]["count"] == 0, "No print jobs should be created for inactive campaigns"

    # Verify audit logs show campaign was skipped
    audit_logs = get_audit_logs(db_interface, campaign_id)
    skipped_logs = [log for log in audit_logs if log["action"] == "CAMPAIGN_PROCESSING_SKIPPED"]
    assert len(skipped_logs) == 1, "Campaign skipping should be logged"
    assert (
        "skipped because status is draft" in skipped_logs[0]["details"]
    ), "Log should explain why campaign was skipped"


@pytest.mark.postgres_only
def test_error_handling_invalid_campaign(db_interface, complex_procedures, enable_postgres_tests):
    """Test error handling when processing an invalid campaign ID."""
    # Check if we're using PostgreSQL directly by class name
    if db_interface.__class__.__name__ != "PostgreSQLInterface":
        pytest.skip("Test requires PostgreSQL")

    if not enable_postgres_tests:
        pytest.skip("Use --enable-postgres-tests to run this test")

    # Clear audit logs before test
    clear_audit_logs(db_interface)

    # Try to process a non-existent campaign
    with pytest.raises(Exception) as exc_info:
        call_process_campaign(db_interface, 9999)  # Non-existent ID

    # Verify the correct error was raised
    assert "not found" in str(exc_info.value).lower(), "Should raise exception for non-existent campaign"

    # Verify no side effects occurred
    print_jobs_count = db_interface.query("SELECT COUNT(*) as count FROM print_jobs")[0]["count"]
    assert print_jobs_count == 0, "No print jobs should be created when error occurs"
