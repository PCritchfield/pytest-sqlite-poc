"""
Tests for multi-database functionality.

This module contains tests that can be run against both SQLite and PostgreSQL
databases to verify that the application works with both database types.
"""


def test_customer_creation(db_interface):
    """Test that customers can be created in both database types."""
    # Insert a new customer
    db_interface.execute(
        "INSERT INTO customers (name, email, phone) VALUES (%s, %s, %s)",
        ("Test Customer", "test@example.com", "555-TEST"),
    )
    db_interface.commit()

    # Query for the customer
    results = db_interface.query(
        "SELECT customer_id, name, email, phone FROM customers WHERE email = %s",
        ("test@example.com",),
    )

    # Verify the customer was created
    assert len(results) == 1
    customer = results[0]
    assert customer["name"] == "Test Customer"
    assert customer["email"] == "test@example.com"
    assert customer["phone"] == "555-TEST"


def test_address_creation(db_interface):
    """Test that addresses can be created in both database types."""
    # Insert a new customer first
    db_interface.execute(
        "INSERT INTO customers (name, email, phone) VALUES (%s, %s, %s)",
        ("Address Test", "address@example.com", "555-ADDR"),
    )

    # Get the customer ID
    results = db_interface.query(
        "SELECT customer_id FROM customers WHERE email = %s",
        ("address@example.com",),
    )
    customer_id = results[0]["customer_id"]

    # Insert an address for the customer
    db_interface.execute(
        """
        INSERT INTO addresses
        (customer_id, address_type, street_line1, city, state, postal_code, country, is_verified)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (customer_id, "home", "123 Test St", "Testville", "OH", "12345", "USA", True),
    )
    db_interface.commit()

    # Query for the address
    results = db_interface.query(
        "SELECT * FROM addresses WHERE customer_id = %s",
        (customer_id,),
    )

    # Verify the address was created
    assert len(results) == 1
    address = results[0]
    assert address["customer_id"] == customer_id
    assert address["address_type"] == "home"
    assert address["street_line1"] == "123 Test St"
    assert address["city"] == "Testville"
    assert address["state"] == "OH"
    assert address["postal_code"] == "12345"
    assert address["country"] == "USA"
    assert address["is_verified"] is True


def test_relationship_integrity(db_interface):
    """Test that relationships work correctly in both database types."""
    # Insert a customer
    db_interface.execute(
        "INSERT INTO customers (name, email, phone) VALUES (%s, %s, %s)",
        ("Relationship Test", "relation@example.com", "555-REL"),
    )

    # Get the customer ID
    results = db_interface.query(
        "SELECT customer_id FROM customers WHERE email = %s",
        ("relation@example.com",),
    )
    customer_id = results[0]["customer_id"]

    # Insert an address for the customer
    db_interface.execute(
        """
        INSERT INTO addresses
        (customer_id, address_type, street_line1, city, state, postal_code, country, is_verified)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (customer_id, "home", "456 Relation St", "Relationville", "OH", "54321", "USA", True),
    )

    # Get the address ID
    results = db_interface.query(
        "SELECT address_id FROM addresses WHERE customer_id = %s",
        (customer_id,),
    )
    address_id = results[0]["address_id"]

    # Insert a mailing list
    db_interface.execute(
        "INSERT INTO mailing_lists (name, description, created_by) VALUES (%s, %s, %s)",
        ("Test List", "Test mailing list", "test_user"),
    )

    # Get the list ID
    results = db_interface.query(
        "SELECT list_id FROM mailing_lists WHERE name = %s",
        ("Test List",),
    )
    list_id = results[0]["list_id"]

    # Add the customer to the mailing list
    db_interface.execute(
        """
        INSERT INTO list_members
        (list_id, customer_id, address_id, status)
        VALUES (%s, %s, %s, %s)
        """,
        (list_id, customer_id, address_id, "active"),
    )
    db_interface.commit()

    # Query for the list member
    results = db_interface.query(
        """
        SELECT lm.*, c.name as customer_name, a.street_line1, ml.name as list_name
        FROM list_members lm
        JOIN customers c ON lm.customer_id = c.customer_id
        JOIN addresses a ON lm.address_id = a.address_id
        JOIN mailing_lists ml ON lm.list_id = ml.list_id
        WHERE lm.customer_id = %s
        """,
        (customer_id,),
    )

    # Verify the relationships
    assert len(results) == 1
    member = results[0]
    assert member["list_id"] == list_id
    assert member["customer_id"] == customer_id
    assert member["address_id"] == address_id
    assert member["status"] == "active"
    assert member["customer_name"] == "Relationship Test"
    assert member["street_line1"] == "456 Relation St"
    assert member["list_name"] == "Test List"


def test_sample_data(db_interface, sample_data):
    """Test that sample data is correctly inserted in both database types."""
    # Query for customers
    customer_results = db_interface.query("SELECT COUNT(*) as count FROM customers")
    assert customer_results[0]["count"] > 0

    # Query for addresses
    address_results = db_interface.query("SELECT COUNT(*) as count FROM addresses")
    assert address_results[0]["count"] > 0

    # Query for mailing lists
    list_results = db_interface.query("SELECT COUNT(*) as count FROM mailing_lists")
    assert list_results[0]["count"] > 0

    # Query for list members
    member_results = db_interface.query("SELECT COUNT(*) as count FROM list_members")
    assert member_results[0]["count"] > 0

    # Query for campaigns
    campaign_results = db_interface.query("SELECT COUNT(*) as count FROM mailing_campaigns")
    assert campaign_results[0]["count"] > 0

    # Query for mail items
    item_results = db_interface.query("SELECT COUNT(*) as count FROM mail_items")
    assert item_results[0]["count"] > 0

    # Query for print jobs
    job_results = db_interface.query("SELECT COUNT(*) as count FROM print_jobs")
    assert job_results[0]["count"] > 0

    # Query for print queue
    queue_results = db_interface.query("SELECT COUNT(*) as count FROM print_queue")
    assert queue_results[0]["count"] > 0
