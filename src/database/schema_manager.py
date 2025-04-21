"""
Schema management for multiple database backends.

This module provides functionality to create and manage database schemas
for different database backends (SQLite and PostgreSQL).
"""
from abc import ABC, abstractmethod

from src.database.db_interface import DatabaseInterface, PostgreSQLInterface, SQLiteInterface


class SchemaManager(ABC):
    """Abstract base class for schema managers."""

    def __init__(self, db: DatabaseInterface):
        """
        Initialize a schema manager.

        Args:
            db: Database interface
        """
        self.db = db

    @abstractmethod
    def create_tables(self) -> None:
        """Create all database tables."""

    @abstractmethod
    def drop_tables(self) -> None:
        """Drop all database tables."""


class SQLiteSchemaManager(SchemaManager):
    """Schema manager for SQLite databases."""

    def create_tables(self) -> None:
        """Create all tables for the mail printing and stuffing database."""
        # Create tables in order of dependencies
        self._create_customers_table()
        self._create_addresses_table()
        self._create_materials_table()
        self._create_inventory_table()
        self._create_mailing_lists_table()
        self._create_list_members_table()
        self._create_mailing_campaigns_table()
        self._create_mail_items_table()
        self._create_print_jobs_table()
        self._create_print_queue_table()
        self._create_delivery_tracking_table()

        # Commit the changes
        self.db.commit()

    def drop_tables(self) -> None:
        """Drop all tables in the database."""
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

        # Disable foreign key constraints temporarily
        self.db.execute("PRAGMA foreign_keys = OFF")

        # Drop each table
        for table in tables:
            self.db.execute(f"DROP TABLE IF EXISTS {table}")

        # Re-enable foreign key constraints
        self.db.execute("PRAGMA foreign_keys = ON")

        # Commit the changes
        self.db.commit()

    def _create_customers_table(self) -> None:
        """Create the customers table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def _create_addresses_table(self) -> None:
        """Create the addresses table."""
        self.db.execute(
            """
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
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            )
            """
        )

    def _create_materials_table(self) -> None:
        """Create the materials table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS materials (
                material_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                unit_cost REAL NOT NULL,
                unit_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def _create_inventory_table(self) -> None:
        """Create the inventory table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory (
                inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                location TEXT,
                last_restock_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (material_id) REFERENCES materials(material_id)
            )
            """
        )

    def _create_mailing_lists_table(self) -> None:
        """Create the mailing_lists table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS mailing_lists (
                list_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def _create_list_members_table(self) -> None:
        """Create the list_members table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS list_members (
                member_id INTEGER PRIMARY KEY AUTOINCREMENT,
                list_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                address_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (list_id) REFERENCES mailing_lists(list_id),
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                FOREIGN KEY (address_id) REFERENCES addresses(address_id)
            )
            """
        )

    def _create_mailing_campaigns_table(self) -> None:
        """Create the mailing_campaigns table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS mailing_campaigns (
                campaign_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                list_id INTEGER NOT NULL,
                start_date TEXT,
                end_date TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (list_id) REFERENCES mailing_lists(list_id)
            )
            """
        )

    def _create_mail_items_table(self) -> None:
        """Create the mail_items table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS mail_items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                address_id INTEGER NOT NULL,
                content_template TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES mailing_campaigns(campaign_id),
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                FOREIGN KEY (address_id) REFERENCES addresses(address_id)
            )
            """
        )

    def _create_print_jobs_table(self) -> None:
        """Create the print_jobs table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS print_jobs (
                job_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                scheduled_date TEXT,
                started_date TEXT,
                completed_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def _create_print_queue_table(self) -> None:
        """Create the print_queue table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS print_queue (
                queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                print_order INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                printed_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES print_jobs(job_id),
                FOREIGN KEY (item_id) REFERENCES mail_items(item_id)
            )
            """
        )

    def _create_delivery_tracking_table(self) -> None:
        """Create the delivery_tracking table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS delivery_tracking (
                tracking_id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                tracking_number TEXT,
                carrier TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                shipped_date TEXT,
                estimated_delivery_date TEXT,
                delivered_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES mail_items(item_id)
            )
            """
        )


class PostgreSQLSchemaManager(SchemaManager):
    """Schema manager for PostgreSQL databases."""

    def create_tables(self) -> None:
        """Create all tables for the mail printing and stuffing database."""
        # Create tables in order of dependencies
        self._create_customers_table()
        self._create_addresses_table()
        self._create_materials_table()
        self._create_inventory_table()
        self._create_mailing_lists_table()
        self._create_list_members_table()
        self._create_mailing_campaigns_table()
        self._create_mail_items_table()
        self._create_print_jobs_table()
        self._create_print_queue_table()
        self._create_delivery_tracking_table()

        # Commit the changes
        self.db.commit()

    def drop_tables(self) -> None:
        """Drop all tables in the database."""
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

        # Drop each table with cascade to handle dependencies
        for table in tables:
            self.db.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

        # Commit the changes
        self.db.commit()

    def _create_customers_table(self) -> None:
        """Create the customers table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                customer_id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def _create_addresses_table(self) -> None:
        """Create the addresses table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS addresses (
                address_id SERIAL PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                address_type TEXT NOT NULL,
                street_line1 TEXT NOT NULL,
                street_line2 TEXT,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                postal_code TEXT NOT NULL,
                country TEXT NOT NULL DEFAULT 'USA',
                is_verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            )
            """
        )

    def _create_materials_table(self) -> None:
        """Create the materials table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS materials (
                material_id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                unit_cost REAL NOT NULL,
                unit_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def _create_inventory_table(self) -> None:
        """Create the inventory table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory (
                inventory_id SERIAL PRIMARY KEY,
                material_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                location TEXT,
                last_restock_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (material_id) REFERENCES materials(material_id)
            )
            """
        )

    def _create_mailing_lists_table(self) -> None:
        """Create the mailing_lists table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS mailing_lists (
                list_id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def _create_list_members_table(self) -> None:
        """Create the list_members table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS list_members (
                member_id SERIAL PRIMARY KEY,
                list_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                address_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (list_id) REFERENCES mailing_lists(list_id),
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                FOREIGN KEY (address_id) REFERENCES addresses(address_id)
            )
            """
        )

    def _create_mailing_campaigns_table(self) -> None:
        """Create the mailing_campaigns table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS mailing_campaigns (
                campaign_id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                list_id INTEGER NOT NULL,
                start_date DATE,
                end_date DATE,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (list_id) REFERENCES mailing_lists(list_id)
            )
            """
        )

    def _create_mail_items_table(self) -> None:
        """Create the mail_items table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS mail_items (
                item_id SERIAL PRIMARY KEY,
                campaign_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                address_id INTEGER NOT NULL,
                content_template TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES mailing_campaigns(campaign_id),
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                FOREIGN KEY (address_id) REFERENCES addresses(address_id)
            )
            """
        )

    def _create_print_jobs_table(self) -> None:
        """Create the print_jobs table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS print_jobs (
                job_id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                scheduled_date DATE,
                started_date DATE,
                completed_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def _create_print_queue_table(self) -> None:
        """Create the print_queue table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS print_queue (
                queue_id SERIAL PRIMARY KEY,
                job_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                print_order INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                printed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES print_jobs(job_id),
                FOREIGN KEY (item_id) REFERENCES mail_items(item_id)
            )
            """
        )

    def _create_delivery_tracking_table(self) -> None:
        """Create the delivery_tracking table."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS delivery_tracking (
                tracking_id SERIAL PRIMARY KEY,
                item_id INTEGER NOT NULL,
                tracking_number TEXT,
                carrier TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                shipped_date DATE,
                estimated_delivery_date DATE,
                delivered_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES mail_items(item_id)
            )
            """
        )


def get_schema_manager(db: DatabaseInterface) -> SchemaManager:
    """
    Factory function to create a schema manager for the given database.

    Args:
        db: Database interface

    Returns:
        A SchemaManager implementation
    """
    if hasattr(db, "connection") and hasattr(db.connection, "__module__"):
        if "sqlite3" in db.connection.__module__:
            return SQLiteSchemaManager(db)
        elif "psycopg2" in db.connection.__module__:
            return PostgreSQLSchemaManager(db)

    # Fallback based on class type
    if isinstance(db, SQLiteInterface):
        return SQLiteSchemaManager(db)
    elif isinstance(db, PostgreSQLInterface):
        return PostgreSQLSchemaManager(db)
    else:
        raise ValueError(f"Unsupported database type: {type(db)}")
