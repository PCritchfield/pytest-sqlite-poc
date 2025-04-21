"""
Data migration utilities for SQLite.
This module provides functions to transform and migrate data within the database.
"""
import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Union

from src.database.connection import execute_query


class DataMigration:
    """
    Class to handle data migrations for SQLite databases.
    """

    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize the data migration manager.

        Args:
            conn: SQLite connection
        """
        self.conn = conn
        self._ensure_migrations_table()

    def _ensure_migrations_table(self) -> None:
        """Create the data migrations tracking table if it doesn't exist."""
        self.conn.execute(
            """
        CREATE TABLE IF NOT EXISTS data_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            migration_id TEXT UNIQUE NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
        """
        )
        self.conn.commit()

    def get_applied_migrations(self) -> List[str]:
        """
        Get a list of already applied data migrations.

        Returns:
            List of applied migration IDs
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT migration_id FROM data_migrations ORDER BY id")
        migrations = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return migrations

    def apply_migration(
        self, migration_id: str, migration_func, description: Optional[str] = None
    ) -> bool:
        """
        Apply a single data migration using a Python function.

        Args:
            migration_id: Unique identifier for the migration
            migration_func: Function that performs the migration
            description: Optional description of the migration

        Returns:
            True if migration was applied, False if already applied
        """
        # Check if migration was already applied
        applied = self.get_applied_migrations()
        if migration_id in applied:
            return False

        # Apply the migration
        try:
            # Start a transaction
            self.conn.execute("BEGIN TRANSACTION")

            # Execute the migration function
            migration_func(self.conn)

            # Record the migration
            self.conn.execute(
                "INSERT INTO data_migrations (migration_id, description) VALUES (?, ?)",
                (migration_id, description or f"Applied migration {migration_id}"),
            )

            # Commit the transaction
            self.conn.commit()
            return True

        except Exception as e:
            # Rollback on error
            self.conn.rollback()
            raise RuntimeError(f"Data migration failed: {str(e)}")


def transform_addresses(conn: sqlite3.Connection) -> None:
    """
    Example data migration: Transform address data format.

    Args:
        conn: SQLite connection
    """
    # Get all addresses
    addresses = execute_query(conn, "SELECT * FROM addresses")

    # Update each address
    for address in addresses:
        # Example transformation: Standardize state codes to uppercase
        state = address["state"].upper()

        # Example transformation: Format postal codes consistently
        postal_code = address["postal_code"].strip()
        if len(postal_code) == 9 and postal_code.isdigit():
            postal_code = f"{postal_code[:5]}-{postal_code[5:]}"

        # Update the record
        conn.execute(
            "UPDATE addresses SET state = ?, postal_code = ? WHERE address_id = ?",
            (state, postal_code, address["address_id"]),
        )

    conn.commit()


def merge_duplicate_customers(conn: sqlite3.Connection) -> None:
    """
    Example data migration: Merge duplicate customer records.

    Args:
        conn: SQLite connection
    """
    # Find potential duplicates based on email
    duplicates = execute_query(
        conn,
        """
    SELECT email, COUNT(*) as count, GROUP_CONCAT(customer_id) as customer_ids
    FROM customers
    WHERE email IS NOT NULL
    GROUP BY email
    HAVING count > 1
    """,
    )

    for dup in duplicates:
        customer_ids = dup["customer_ids"].split(",")
        primary_id = customer_ids[0]  # Keep the first one as primary
        duplicate_ids = customer_ids[1:]  # Others will be merged

        # Update foreign key references to point to the primary customer
        for table, fk_column in [
            ("addresses", "customer_id"),
            ("list_members", "customer_id"),
            ("mail_items", "customer_id"),
        ]:
            for dup_id in duplicate_ids:
                conn.execute(
                    f"UPDATE {table} SET {fk_column} = ? WHERE {fk_column} = ?",
                    (primary_id, dup_id),
                )

        # Delete the duplicate customer records
        for dup_id in duplicate_ids:
            conn.execute("DELETE FROM customers WHERE customer_id = ?", (dup_id,))

    conn.commit()


def update_price_calculations(conn: sqlite3.Connection) -> None:
    """
    Example data migration: Update prices based on new calculation rules.

    Args:
        conn: SQLite connection
    """
    # This would typically update prices or costs based on new business rules
    # For this example, we'll update material costs with a 5% increase

    conn.execute(
        """
    UPDATE materials
    SET unit_cost = unit_cost * 1.05
    """
    )

    conn.commit()


def import_data_from_json(
    conn: sqlite3.Connection, json_file: Union[str, Path], table: str
) -> int:
    """
    Import data from a JSON file into a table.

    Args:
        conn: SQLite connection
        json_file: Path to JSON file containing records
        table: Target table name

    Returns:
        Number of records imported
    """
    json_file = Path(json_file)

    # Load data from JSON file
    with open(json_file, "r") as f:
        data = json.load(f)

    if not data:
        return 0

    # Get column names from the first record
    columns = list(data[0].keys())
    placeholders = ", ".join(["?"] * len(columns))
    columns_str = ", ".join(columns)

    # Insert data
    cursor = conn.cursor()
    count = 0

    for record in data:
        values = [record.get(col) for col in columns]
        cursor.execute(
            f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})", values
        )
        count += 1

    conn.commit()
    cursor.close()

    return count
