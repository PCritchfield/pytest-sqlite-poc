"""
Integration tests for SQLite database operations.
"""
import json
import sqlite3
from pathlib import Path

import pytest

from src.database.connection import execute_query
from src.database.functions import register_functions


def test_end_to_end_mailing_process(db_with_sample_data):
    """
    Test the entire mailing process from campaign creation to delivery tracking.
    This tests interactions between multiple tables and operations.
    """
    # 1. Create a new campaign
    db_with_sample_data.execute("""
    INSERT INTO mailing_campaigns (name, description, list_id, start_date, end_date, status)
    VALUES ('Test Campaign', 'Integration test campaign', 1, date('now'), date('now', '+30 days'), 'active')
    """)
    
    # Get the campaign ID
    result = execute_query(
        db_with_sample_data,
        "SELECT campaign_id FROM mailing_campaigns WHERE name = 'Test Campaign'"
    )
    campaign_id = result[0]['campaign_id']
    
    # 2. Create mail items for all members of the mailing list
    db_with_sample_data.execute("""
    INSERT INTO mail_items (campaign_id, customer_id, address_id, content_template, status)
    SELECT 
        ?, 
        lm.customer_id, 
        lm.address_id, 
        'test_template', 
        'pending'
    FROM list_members lm
    WHERE lm.list_id = 1
    """, (campaign_id,))
    
    # 3. Create a print job
    db_with_sample_data.execute("""
    INSERT INTO print_jobs (name, description, status, scheduled_date)
    VALUES ('Test Print Job', 'Integration test print job', 'queued', date('now'))
    """)
    
    # Get the print job ID
    result = execute_query(
        db_with_sample_data,
        "SELECT job_id FROM print_jobs WHERE name = 'Test Print Job'"
    )
    job_id = result[0]['job_id']
    
    # 4. Add mail items to the print queue
    db_with_sample_data.execute("""
    INSERT INTO print_queue (job_id, item_id, print_order, status)
    SELECT 
        ?,
        item_id,
        ROW_NUMBER() OVER (ORDER BY item_id),
        'queued'
    FROM mail_items
    WHERE campaign_id = ?
    """, (job_id, campaign_id))
    
    # 5. Mark items as printed
    db_with_sample_data.execute("""
    UPDATE print_queue
    SET status = 'completed', printed_at = datetime('now')
    WHERE job_id = ?
    """, (job_id,))
    
    # 6. Create delivery tracking entries
    db_with_sample_data.execute("""
    INSERT INTO delivery_tracking (item_id, tracking_number, carrier, status, shipped_date)
    SELECT 
        mi.item_id,
        generate_tracking('USPS') AS tracking_number,
        'USPS',
        'shipped',
        datetime('now')
    FROM mail_items mi
    WHERE mi.campaign_id = ?
    """, (campaign_id,))
    
    # Commit all changes
    db_with_sample_data.commit()
    
    # Verify the end-to-end process
    # 1. Check that mail items were created
    result = execute_query(
        db_with_sample_data,
        "SELECT COUNT(*) AS count FROM mail_items WHERE campaign_id = ?",
        (campaign_id,)
    )
    mail_item_count = result[0]['count']
    assert mail_item_count > 0, "Mail items should be created for the campaign"
    
    # 2. Check that print queue entries were created
    result = execute_query(
        db_with_sample_data,
        "SELECT COUNT(*) AS count FROM print_queue WHERE job_id = ?",
        (job_id,)
    )
    queue_count = result[0]['count']
    assert queue_count == mail_item_count, "Print queue should have entries for all mail items"
    
    # 3. Check that the print job was marked as completed
    result = execute_query(
        db_with_sample_data,
        "SELECT status, completed_date FROM print_jobs WHERE job_id = ?",
        (job_id,)
    )
    assert result[0]['status'] == 'completed', "Print job should be marked as completed"
    assert result[0]['completed_date'] is not None, "Completed date should be set"
    
    # 4. Check that tracking entries were created
    result = execute_query(
        db_with_sample_data,
        "SELECT COUNT(*) AS count FROM delivery_tracking WHERE item_id IN (SELECT item_id FROM mail_items WHERE campaign_id = ?)",
        (campaign_id,)
    )
    tracking_count = result[0]['count']
    assert tracking_count == mail_item_count, "Tracking entries should exist for all mail items"


def test_complex_query_performance(db_with_sample_data):
    """
    Test a complex query that joins multiple tables and uses functions.
    This tests the performance and correctness of complex database operations.
    """
    # First, make sure we have at least one active campaign
    campaign_check = execute_query(db_with_sample_data, "SELECT COUNT(*) as count FROM mailing_campaigns WHERE status = 'active'")
    
    # If no active campaigns, update one to be active
    if campaign_check[0]['count'] == 0:
        db_with_sample_data.execute(
            "UPDATE mailing_campaigns SET status = 'active' WHERE campaign_id IN (SELECT campaign_id FROM mailing_campaigns LIMIT 1)"
        )
        db_with_sample_data.commit()
    
    # Create a complex query that:
    # 1. Joins multiple tables
    # 2. Uses aggregation
    # 3. Uses a custom function
    # 4. Uses subqueries
    query = """
    SELECT 
        c.name AS customer_name,
        a.city,
        a.state,
        COUNT(mi.item_id) AS total_mailings,
        SUM(calculate_postage(0.5, 3)) AS total_postage,
        (
            SELECT COUNT(*)
            FROM delivery_tracking dt
            JOIN mail_items mi2 ON dt.item_id = mi2.item_id
            WHERE mi2.customer_id = c.customer_id
            AND dt.status IN ('pending', 'shipped', 'delivered')
        ) AS shipped_count
    FROM customers c
    JOIN addresses a ON c.customer_id = a.customer_id
    JOIN mail_items mi ON c.customer_id = mi.customer_id AND mi.address_id = a.address_id
    JOIN mailing_campaigns mc ON mi.campaign_id = mc.campaign_id
    WHERE mc.status = 'active'
    GROUP BY c.customer_id, a.address_id
    ORDER BY total_mailings DESC
    """
    
    # Execute the query
    results = execute_query(db_with_sample_data, query)
    
    # Verify the results
    assert len(results) > 0, "Query should return results"
    
    # Check that all expected columns are present
    expected_columns = ['customer_name', 'city', 'state', 'total_mailings', 'total_postage', 'shipped_count']
    for column in expected_columns:
        assert column in results[0], f"Column {column} should be present in results"
    
    # Verify that the postage calculation is working
    for result in results:
        assert result['total_postage'] > 0, "Postage calculation should return positive values"


def test_transaction_rollback(db_with_sample_data):
    """
    Test that transactions can be rolled back to maintain data integrity.
    """
    # Get initial counts
    result = execute_query(db_with_sample_data, "SELECT COUNT(*) AS count FROM customers")
    initial_customer_count = result[0]['count']
    
    result = execute_query(db_with_sample_data, "SELECT COUNT(*) AS count FROM addresses")
    initial_address_count = result[0]['count']
    
    # Start a transaction
    db_with_sample_data.execute("BEGIN TRANSACTION")
    
    # Insert a new customer
    db_with_sample_data.execute("""
    INSERT INTO customers (name, email, phone)
    VALUES ('Transaction Test', 'transaction@example.com', '555-999-8888')
    """)
    
    # Get the customer ID
    result = execute_query(
        db_with_sample_data,
        "SELECT customer_id FROM customers WHERE name = 'Transaction Test'"
    )
    customer_id = result[0]['customer_id']
    
    # Insert an address for the customer
    db_with_sample_data.execute("""
    INSERT INTO addresses (customer_id, address_type, street_line1, city, state, postal_code, country)
    VALUES (?, 'home', '123 Transaction St', 'Test City', 'TS', '12345', 'USA')
    """, (customer_id,))
    
    # Verify the data was inserted
    result = execute_query(db_with_sample_data, "SELECT COUNT(*) AS count FROM customers")
    assert result[0]['count'] == initial_customer_count + 1, "Customer should be inserted"
    
    result = execute_query(db_with_sample_data, "SELECT COUNT(*) AS count FROM addresses")
    assert result[0]['count'] == initial_address_count + 1, "Address should be inserted"
    
    # Rollback the transaction
    db_with_sample_data.rollback()
    
    # Verify the data was rolled back
    result = execute_query(db_with_sample_data, "SELECT COUNT(*) AS count FROM customers")
    assert result[0]['count'] == initial_customer_count, "Customer insert should be rolled back"
    
    result = execute_query(db_with_sample_data, "SELECT COUNT(*) AS count FROM addresses")
    assert result[0]['count'] == initial_address_count, "Address insert should be rolled back"


def test_database_consistency(db_with_sample_data):
    """
    Test database consistency by checking referential integrity.
    """
    # Check that all foreign keys are valid
    tables_with_fks = [
        ('addresses', 'customer_id', 'customers', 'customer_id'),
        ('inventory', 'material_id', 'materials', 'material_id'),
        ('list_members', 'list_id', 'mailing_lists', 'list_id'),
        ('list_members', 'customer_id', 'customers', 'customer_id'),
        ('list_members', 'address_id', 'addresses', 'address_id'),
        ('mailing_campaigns', 'list_id', 'mailing_lists', 'list_id'),
        ('mail_items', 'campaign_id', 'mailing_campaigns', 'campaign_id'),
        ('mail_items', 'customer_id', 'customers', 'customer_id'),
        ('mail_items', 'address_id', 'addresses', 'address_id'),
        ('print_queue', 'job_id', 'print_jobs', 'job_id'),
        ('print_queue', 'item_id', 'mail_items', 'item_id'),
        ('delivery_tracking', 'item_id', 'mail_items', 'item_id')
    ]
    
    for child_table, fk_column, parent_table, pk_column in tables_with_fks:
        # Check that all foreign keys reference existing primary keys
        query = f"""
        SELECT COUNT(*) AS invalid_count
        FROM {child_table} c
        LEFT JOIN {parent_table} p ON c.{fk_column} = p.{pk_column}
        WHERE p.{pk_column} IS NULL
        """
        
        result = execute_query(db_with_sample_data, query)
        assert result[0]['invalid_count'] == 0, f"All {fk_column} in {child_table} should reference valid {pk_column} in {parent_table}"
