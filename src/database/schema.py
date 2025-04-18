"""
Database schema utilities for SQLite.
This module provides functions to create and manage database schemas.
"""
import os
import sqlite3
from pathlib import Path
from typing import Union

from src.database.connection import execute_script


def init_schema(conn: sqlite3.Connection, schema_path: Union[str, Path]) -> None:
    """
    Initialize the database schema from a SQL script.
    
    Args:
        conn: SQLite connection
        schema_path: Path to the schema SQL script
    """
    execute_script(conn, schema_path)


def create_tables(conn: sqlite3.Connection) -> None:
    """
    Create all tables for the mail printing and stuffing database.
    This is an alternative to using a schema file.
    
    Args:
        conn: SQLite connection
    """
    # Create tables in order of dependencies
    
    # Customers table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS customers (
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        phone TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Addresses table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS addresses (
        address_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        address_type TEXT NOT NULL,
        street_line1 TEXT NOT NULL,
        street_line2 TEXT,
        city TEXT NOT NULL,
        state TEXT NOT NULL,
        postal_code TEXT NOT NULL,
        country TEXT NOT NULL DEFAULT 'USA',
        is_verified BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE
    )
    ''')
    
    # Materials table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS materials (
        material_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        unit_cost REAL NOT NULL,
        unit_type TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Inventory table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS inventory (
        inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
        material_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 0,
        location TEXT,
        last_restock_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (material_id) REFERENCES materials (material_id) ON DELETE CASCADE
    )
    ''')
    
    # Mailing Lists table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS mailing_lists (
        list_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        created_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # List Members table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS list_members (
        member_id INTEGER PRIMARY KEY AUTOINCREMENT,
        list_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        address_id INTEGER NOT NULL,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (list_id) REFERENCES mailing_lists (list_id) ON DELETE CASCADE,
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE,
        FOREIGN KEY (address_id) REFERENCES addresses (address_id) ON DELETE CASCADE
    )
    ''')
    
    # Mailing Campaigns table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS mailing_campaigns (
        campaign_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        list_id INTEGER NOT NULL,
        start_date TIMESTAMP,
        end_date TIMESTAMP,
        status TEXT DEFAULT 'draft',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (list_id) REFERENCES mailing_lists (list_id) ON DELETE CASCADE
    )
    ''')
    
    # Mail Items table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS mail_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        address_id INTEGER NOT NULL,
        content_template TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (campaign_id) REFERENCES mailing_campaigns (campaign_id) ON DELETE CASCADE,
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE,
        FOREIGN KEY (address_id) REFERENCES addresses (address_id) ON DELETE CASCADE
    )
    ''')
    
    # Print Jobs table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS print_jobs (
        job_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'queued',
        scheduled_date TIMESTAMP,
        completed_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Print Queue table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS print_queue (
        queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        print_order INTEGER,
        status TEXT DEFAULT 'queued',
        printed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (job_id) REFERENCES print_jobs (job_id) ON DELETE CASCADE,
        FOREIGN KEY (item_id) REFERENCES mail_items (item_id) ON DELETE CASCADE
    )
    ''')
    
    # Delivery Tracking table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS delivery_tracking (
        tracking_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        tracking_number TEXT,
        carrier TEXT,
        status TEXT DEFAULT 'pending',
        shipped_date TIMESTAMP,
        estimated_delivery TIMESTAMP,
        actual_delivery TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (item_id) REFERENCES mail_items (item_id) ON DELETE CASCADE
    )
    ''')
    
    # Commit all changes
    conn.commit()


def drop_tables(conn: sqlite3.Connection) -> None:
    """
    Drop all tables from the database.
    
    Args:
        conn: SQLite connection
    """
    tables = [
        'delivery_tracking',
        'print_queue',
        'print_jobs',
        'mail_items',
        'mailing_campaigns',
        'list_members',
        'mailing_lists',
        'inventory',
        'materials',
        'addresses',
        'customers'
    ]
    
    for table in tables:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    
    conn.commit()


def export_schema_to_file(conn: sqlite3.Connection, output_path: Union[str, Path]) -> None:
    """
    Export the current database schema to a SQL file.
    
    Args:
        conn: SQLite connection
        output_path: Path to save the schema SQL
    """
    output_path = Path(output_path)
    
    # Get schema for all tables
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = cursor.fetchall()
    
    with open(output_path, 'w') as f:
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE name = '{table_name}'")
            create_statement = cursor.fetchone()[0]
            f.write(f"{create_statement};\n\n")
    
    cursor.close()
