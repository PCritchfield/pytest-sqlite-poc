"""
Test data helper for multi-database testing.

This module provides functions to insert test data into different database types
using the database interface abstraction.
"""
from typing import List, Optional, Tuple

from src.database.db_interface import DatabaseInterface

# Define the type for address tuples to match conftest.py
AddressTuple = Tuple[Optional[int], int, str, str, Optional[str], str, str, str, str, bool]


def insert_test_data(db: DatabaseInterface) -> None:
    """
    Insert sample data into the database for testing.

    This function inserts a standard set of test data into the database
    using the database interface abstraction, which works with both
    SQLite and PostgreSQL.

    Args:
        db: Database interface
    """
    # Clear any existing data first
    clear_tables(db)

    # Insert data in the correct order to maintain relationships
    customer_ids = insert_customers(db)
    address_data = insert_addresses(db, customer_ids)
    material_ids = insert_materials(db)
    insert_inventory(db, material_ids)
    list_ids = insert_mailing_lists(db)
    insert_list_members(db, list_ids, address_data)
    campaign_data = insert_campaigns(db, list_ids)
    mail_item_ids = insert_mail_items(db, campaign_data)
    job_ids = insert_print_jobs(db)
    insert_print_queue(db, job_ids, mail_item_ids)

    # Commit all changes
    db.commit()


def clear_tables(db: DatabaseInterface) -> None:
    """
    Clear all data from the specified tables.

    Args:
        db: Database interface
    """
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

    # SQLite-specific handling
    if hasattr(db.connection, "__module__") and "sqlite3" in db.connection.__module__:
        # Disable foreign key constraints temporarily for clean deletion
        db.execute("PRAGMA foreign_keys = OFF")

        for table in tables:
            db.execute(f"DELETE FROM {table}")

        # Reset auto-increment counters
        for table in tables:
            db.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")

        # Re-enable foreign key constraints
        db.execute("PRAGMA foreign_keys = ON")
    else:
        # PostgreSQL handling
        for table in tables:
            db.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")


def insert_customers(db: DatabaseInterface) -> List[int]:
    """
    Insert sample customer data and return their IDs.

    Args:
        db: Database interface

    Returns:
        List of customer IDs
    """
    customers = [
        (None, "John Smith", "john.smith@example.com", "555-123-4567"),
        (None, "Jane Doe", "jane.doe@example.com", "555-234-5678"),
        (None, "Bob Johnson", "bob.johnson@example.com", "555-345-6789"),
        (None, "Alice Brown", "alice.brown@example.com", "555-789-0123"),
        (None, "Charlie Davis", "charlie.davis@example.com", "555-321-6540"),
    ]

    # Insert customers - handle different database types
    db_type = db.__class__.__name__

    for customer in customers:
        if db_type == "PostgreSQLInterface":
            # For PostgreSQL, let the database generate the customer_id
            _, name, email, phone = customer
            db.execute("INSERT INTO customers (name, email, phone) VALUES (%s, %s, %s)", (name, email, phone))
        else:
            # For SQLite, use the provided customer_id (or NULL to auto-generate)
            db.execute("INSERT INTO customers (customer_id, name, email, phone) VALUES (%s, %s, %s, %s)", customer)

    # Get customer IDs - query approach works for both SQLite and PostgreSQL
    results = db.query("SELECT customer_id FROM customers")
    customer_ids = [row["customer_id"] for row in results]
    return customer_ids


def insert_addresses(db: DatabaseInterface, customer_ids: List[int]) -> List[Tuple[int, int]]:
    """
    Insert sample address data for customers and return address data.

    Args:
        db: Database interface
        customer_ids: List of customer IDs to create addresses for

    Returns:
        List of (address_id, customer_id) tuples
    """
    addresses: List[AddressTuple] = []

    for customer_id in customer_ids:
        # Home address for every customer
        home_address = (
            None,
            customer_id,
            "home",
            f"{customer_id*123} Main St",
            None,  # street_line2 can be None
            "Anytown",
            "OH",
            f"{customer_id+10000}",
            "USA",
            True,  # is_verified is boolean
        )
        addresses.append(home_address)

        # Work address for some customers
        if customer_id % 2 == 0:
            work_address = (
                None,
                customer_id,
                "work",
                f"{customer_id*100} Business Ave",
                f"Suite {customer_id*10}",  # street_line2 has a value
                "Workville",
                "OH",
                f"{customer_id+20000}",
                "USA",
                True,  # is_verified is boolean
            )
            addresses.append(work_address)

    # Insert addresses - handle different database types
    db_type = db.__class__.__name__

    for address in addresses:
        if db_type == "PostgreSQLInterface":
            # For PostgreSQL, let the database generate the address_id
            (
                _,
                customer_id,
                address_type,
                street_line1,
                street_line2,
                city,
                state,
                postal_code,
                country,
                is_verified,
            ) = address
            db.execute(
                """
                INSERT INTO addresses
                (customer_id, address_type, street_line1, street_line2,
                 city, state, postal_code, country, is_verified)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (customer_id, address_type, street_line1, street_line2, city, state, postal_code, country, is_verified),
            )
        else:
            # For SQLite, use the provided address_id (or NULL to auto-generate)
            db.execute(
                """
                INSERT INTO addresses
                (address_id, customer_id, address_type, street_line1, street_line2,
                 city, state, postal_code, country, is_verified)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                address,
            )

    # Get address data
    results = db.query("SELECT address_id, customer_id FROM addresses")
    address_data = [(row["address_id"], row["customer_id"]) for row in results]
    return address_data


def insert_materials(db: DatabaseInterface) -> List[int]:
    """
    Insert sample materials data and return their IDs.

    Args:
        db: Database interface

    Returns:
        List of material IDs
    """
    materials = [
        (None, "Standard Envelope", "Standard #10 business envelope", 0.05, "each"),
        (None, "Large Envelope", "9x12 manila envelope", 0.15, "each"),
        (None, "Standard Paper", "20lb 8.5x11 white paper", 0.02, "sheet"),
        (None, "Premium Paper", "24lb 8.5x11 ivory paper", 0.04, "sheet"),
        (None, "Ink - Black", "Black printer ink", 0.10, "page"),
    ]

    # Insert materials - handle different database types
    db_type = db.__class__.__name__

    for material in materials:
        if db_type == "PostgreSQLInterface":
            # For PostgreSQL, let the database generate the material_id
            _, name, description, unit_cost, unit_type = material
            db.execute(
                "INSERT INTO materials (name, description, unit_cost, unit_type) VALUES (%s, %s, %s, %s)",
                (name, description, unit_cost, unit_type),
            )
        else:
            # For SQLite, use the provided material_id (or NULL to auto-generate)
            db.execute(
                "INSERT INTO materials (material_id, name, description, unit_cost, unit_type) VALUES (%s, %s, %s, %s, %s)",
                material,
            )

    # Get material IDs
    results = db.query("SELECT material_id FROM materials")
    material_ids = [row["material_id"] for row in results]
    return material_ids


def insert_inventory(db: DatabaseInterface, material_ids: List[int]) -> None:
    """
    Insert sample inventory data.

    Args:
        db: Database interface
        material_ids: List of material IDs
    """
    for i, material_id in enumerate(material_ids):
        inventory_item = (
            None,
            material_id,
            (i + 1) * 1000,
            f"Warehouse {chr(65 + i % 3)}",  # A, B, or C
            "2025-01-15",  # last_restock_date
        )

        # Handle different database types
        db_type = db.__class__.__name__

        if db_type == "PostgreSQLInterface":
            # For PostgreSQL, let the database generate the inventory_id
            _, material_id, quantity, location, last_restock_date = inventory_item
            db.execute(
                """
                INSERT INTO inventory
                (material_id, quantity, location, last_restock_date)
                VALUES (%s, %s, %s, %s)
                """,
                (material_id, quantity, location, last_restock_date),
            )
        else:
            # For SQLite, use the provided inventory_id (or NULL to auto-generate)
            db.execute(
                """
                INSERT INTO inventory
                (inventory_id, material_id, quantity, location, last_restock_date)
                VALUES (%s, %s, %s, %s, %s)
                """,
                inventory_item,
            )


def insert_mailing_lists(db: DatabaseInterface) -> List[int]:
    """
    Insert sample mailing list data and return list IDs.

    Args:
        db: Database interface

    Returns:
        List of mailing list IDs
    """
    mailing_lists = [
        (None, "Monthly Newsletter", "Subscribers to monthly newsletter", "admin"),
        (None, "Special Offers", "Customers interested in special offers", "marketing"),
        (None, "Product Updates", "Customers interested in product updates", "product"),
    ]

    # Insert mailing lists - handle different database types
    db_type = db.__class__.__name__

    for mailing_list in mailing_lists:
        if db_type == "PostgreSQLInterface":
            # For PostgreSQL, let the database generate the list_id
            _, name, description, created_by = mailing_list
            db.execute(
                "INSERT INTO mailing_lists (name, description, created_by) VALUES (%s, %s, %s)",
                (name, description, created_by),
            )
        else:
            # For SQLite, use the provided list_id (or NULL to auto-generate)
            db.execute(
                "INSERT INTO mailing_lists (list_id, name, description, created_by) VALUES (%s, %s, %s, %s)",
                mailing_list,
            )

    # Get list IDs
    results = db.query("SELECT list_id FROM mailing_lists")
    list_ids = [row["list_id"] for row in results]
    return list_ids


def insert_list_members(db: DatabaseInterface, list_ids: List[int], address_data: List[Tuple[int, int]]) -> None:
    """
    Insert sample list member data.

    Args:
        db: Database interface
        list_ids: List of mailing list IDs
        address_data: List of (address_id, customer_id) tuples
    """
    for list_id in list_ids:
        for i, (address_id, customer_id) in enumerate(address_data):
            # Add some customers to each list (not all customers on all lists)
            if i % len(list_ids) == list_id % len(list_ids):
                list_member = (
                    None,
                    list_id,
                    customer_id,
                    address_id,
                    "active",
                )

                # Handle different database types
                db_type = db.__class__.__name__

                if db_type == "PostgreSQLInterface":
                    # For PostgreSQL, let the database generate the member_id
                    _, list_id, customer_id, address_id, status = list_member
                    db.execute(
                        """
                        INSERT INTO list_members
                        (list_id, customer_id, address_id, status)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (list_id, customer_id, address_id, status),
                    )
                else:
                    # For SQLite, use the provided member_id (or NULL to auto-generate)
                    db.execute(
                        """
                        INSERT INTO list_members
                        (member_id, list_id, customer_id, address_id, status)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        list_member,
                    )


def insert_campaigns(db: DatabaseInterface, list_ids: List[int]) -> List[Tuple[int, int]]:
    """
    Insert sample campaign data and return campaign data.

    Args:
        db: DatabaseInterface
        list_ids: List of mailing list IDs

    Returns:
        List of (campaign_id, list_id) tuples
    """
    campaign_ids = []

    for i, list_id in enumerate(list_ids):
        start_date = f"2025-0{i+1}-01"
        end_date = f"2025-0{i+1}-28"
        status = "active" if i < 2 else "draft"

        campaign = (
            None,
            f"Campaign {i+1}",
            f"Description for campaign {i+1}",
            list_id,
            start_date,
            end_date,
            status,
        )

        # Handle different database types
        db_type = db.__class__.__name__

        if db_type == "PostgreSQLInterface":
            # For PostgreSQL, let the database generate the campaign_id
            _, name, description, list_id, start_date, end_date, status = campaign
            db.execute(
                """
                INSERT INTO mailing_campaigns
                (name, description, list_id, start_date, end_date, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (name, description, list_id, start_date, end_date, status),
            )
        else:
            # For SQLite, use the provided campaign_id (or NULL to auto-generate)
            db.execute(
                """
                INSERT INTO mailing_campaigns
                (campaign_id, name, description, list_id, start_date, end_date, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                campaign,
            )

        # Get campaign ID
        result = db.query("SELECT campaign_id FROM mailing_campaigns WHERE name = %s", (f"Campaign {i+1}",))
        campaign_id = result[0]["campaign_id"]
        campaign_ids.append((campaign_id, list_id))

    return campaign_ids


def insert_mail_items(db: DatabaseInterface, campaign_data: List[Tuple[int, int]]) -> List[int]:
    """
    Insert sample mail item data and return mail item IDs.

    Args:
        db: DatabaseInterface
        campaign_data: List of (campaign_id, list_id) tuples

    Returns:
        List of mail item IDs
    """
    mail_item_ids = []

    for campaign_id, list_id in campaign_data:
        # Get members of this list
        results = db.query("SELECT customer_id, address_id FROM list_members WHERE list_id = %s", (list_id,))

        for row in results:
            customer_id = row["customer_id"]
            address_id = row["address_id"]

            mail_item = (
                None,
                campaign_id,
                customer_id,
                address_id,
                f"template_{campaign_id}",
                "pending",
            )

            # Handle different database types
            db_type = db.__class__.__name__

            if db_type == "PostgreSQLInterface":
                # For PostgreSQL, let the database generate the item_id
                _, campaign_id, customer_id, address_id, content_template, status = mail_item
                db.execute(
                    """
                    INSERT INTO mail_items
                    (campaign_id, customer_id, address_id, content_template, status)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (campaign_id, customer_id, address_id, content_template, status),
                )
            else:
                # For SQLite, use the provided item_id (or NULL to auto-generate)
                db.execute(
                    """
                    INSERT INTO mail_items
                    (item_id, campaign_id, customer_id, address_id, content_template, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    mail_item,
                )

            # Get the inserted mail item ID
            result = db.query(
                "SELECT item_id FROM mail_items WHERE campaign_id = %s AND customer_id = %s AND address_id = %s",
                (campaign_id, customer_id, address_id),
            )
            if result:
                mail_item_ids.append(result[0]["item_id"])

    return mail_item_ids


def insert_print_jobs(db: DatabaseInterface) -> List[int]:
    """
    Insert sample print job data and return job IDs.

    Args:
        db: Database interface

    Returns:
        List of print job IDs
    """
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

    # Insert print jobs - handle different database types
    db_type = db.__class__.__name__

    for print_job in print_jobs:
        if db_type == "PostgreSQLInterface":
            # For PostgreSQL, let the database generate the job_id
            _, name, description, status, scheduled_date, started_date, completed_date = print_job
            db.execute(
                """
                INSERT INTO print_jobs
                (name, description, status, scheduled_date, started_date, completed_date)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (name, description, status, scheduled_date, started_date, completed_date),
            )
        else:
            # For SQLite, use the provided job_id (or NULL to auto-generate)
            db.execute(
                """
                INSERT INTO print_jobs
                (job_id, name, description, status, scheduled_date, started_date, completed_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                print_job,
            )

    # Get print job IDs
    results = db.query("SELECT job_id FROM print_jobs")
    job_ids = [row["job_id"] for row in results]
    return job_ids


def insert_print_queue(db: DatabaseInterface, job_ids: List[int], mail_item_ids: List[int]) -> None:
    """
    Insert sample print queue data.

    Args:
        db: Database interface
        job_ids: List of print job IDs
        mail_item_ids: List of mail item IDs
    """
    for i, item_id in enumerate(mail_item_ids):
        # Assign items to print jobs
        job_id = job_ids[i % len(job_ids)]

        queue_item = (
            None,
            job_id,
            item_id,
            i + 1,  # print_order
            "queued",
            None,  # printed_at
        )

        # Handle different database types
        db_type = db.__class__.__name__

        if db_type == "PostgreSQLInterface":
            # For PostgreSQL, let the database generate the queue_id
            _, job_id, item_id, print_order, status, printed_at = queue_item
            db.execute(
                """
                INSERT INTO print_queue
                (job_id, item_id, print_order, status, printed_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (job_id, item_id, print_order, status, printed_at),
            )
        else:
            # For SQLite, use the provided queue_id (or NULL to auto-generate)
            db.execute(
                """
                INSERT INTO print_queue
                (queue_id, job_id, item_id, print_order, status, printed_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                queue_item,
            )
