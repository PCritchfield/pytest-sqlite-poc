"""
Tests for database migrations.
"""
import os
import sqlite3
from pathlib import Path

import pytest

from src.database.connection import execute_query, execute_script
from src.migrations.schema_migrations import SchemaMigration, add_column, rename_table, create_index
from src.migrations.data_migrations import DataMigration, transform_addresses


def test_add_column_migration(migration_db):
    """Test adding a column to an existing table."""
    # Verify the column doesn't exist yet
    cursor = migration_db.cursor()
    cursor.execute("PRAGMA table_info(customers)")
    columns = [row[1] for row in cursor.fetchall()]
    cursor.close()
    
    assert "contact_preference" not in columns, "Column should not exist before migration"
    
    # Add the column
    add_column(migration_db, "customers", "contact_preference", "TEXT DEFAULT 'email'")
    
    # Verify the column was added
    cursor = migration_db.cursor()
    cursor.execute("PRAGMA table_info(customers)")
    columns = [row[1] for row in cursor.fetchall()]
    cursor.close()
    
    assert "contact_preference" in columns, "Column should exist after migration"
    
    # Verify the default value is set
    result = execute_query(migration_db, "SELECT contact_preference FROM customers LIMIT 1")
    assert result[0]["contact_preference"] == "email", "Default value should be 'email'"


def test_rename_table_migration(migration_db):
    """Test renaming a table."""
    # Verify the original table exists
    cursor = migration_db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mailing_lists'")
    exists = cursor.fetchone() is not None
    cursor.close()
    
    assert exists, "Original table should exist before migration"
    
    # Rename the table
    rename_table(migration_db, "mailing_lists", "contact_lists")
    
    # Verify the table was renamed
    cursor = migration_db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='contact_lists'")
    new_exists = cursor.fetchone() is not None
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mailing_lists'")
    old_exists = cursor.fetchone() is not None
    cursor.close()
    
    assert new_exists, "New table name should exist after migration"
    assert not old_exists, "Old table name should not exist after migration"


def test_create_index_migration(migration_db):
    """Test creating an index on a table."""
    # Verify the index doesn't exist yet
    cursor = migration_db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_customers_name'")
    exists = cursor.fetchone() is not None
    cursor.close()
    
    assert not exists, "Index should not exist before migration"
    
    # Create the index
    create_index(migration_db, "customers", ["name"])
    
    # Verify the index was created
    cursor = migration_db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_customers_name'")
    exists = cursor.fetchone() is not None
    cursor.close()
    
    assert exists, "Index should exist after migration"


def test_schema_migration_tracking(migration_db):
    """Test that schema migrations are tracked properly."""
    # Create the migration manager
    migration_manager = SchemaMigration(migration_db)
    
    # Verify the migrations table exists
    cursor = migration_db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'")
    exists = cursor.fetchone() is not None
    cursor.close()
    
    assert exists, "Migrations table should be created"
    
    # Create a temporary migration file
    tmp_dir = Path("./tmp_migrations")
    tmp_dir.mkdir(exist_ok=True)
    
    migration_file = tmp_dir / "001_test_migration.sql"
    with open(migration_file, "w") as f:
        f.write("ALTER TABLE customers ADD COLUMN test_column TEXT;")
    
    # Apply the migration
    result = migration_manager.apply_migration(migration_file, "Test migration")
    
    # Verify the migration was applied
    assert result, "Migration should be applied successfully"
    
    # Verify the migration was recorded
    applied = migration_manager.get_applied_migrations()
    assert "001_test_migration" in applied, "Migration should be recorded"
    
    # Try to apply the same migration again
    result = migration_manager.apply_migration(migration_file)
    
    # Verify the migration was not applied again
    assert not result, "Migration should not be applied twice"
    
    # Clean up
    migration_file.unlink()
    tmp_dir.rmdir()


def test_data_migration(migration_db):
    """Test data migration functionality."""
    # Create the data migration manager
    migration_manager = DataMigration(migration_db)
    
    # Verify the data migrations table exists
    cursor = migration_db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='data_migrations'")
    exists = cursor.fetchone() is not None
    cursor.close()
    
    assert exists, "Data migrations table should be created"
    
    # Check initial state - states should be mixed case
    results = execute_query(migration_db, "SELECT state FROM addresses")
    assert any(r["state"] != r["state"].upper() for r in results), "States should be mixed case initially"
    
    # Apply the data migration
    result = migration_manager.apply_migration(
        "001_transform_addresses",
        transform_addresses,
        "Standardize address data"
    )
    
    # Verify the migration was applied
    assert result, "Migration should be applied successfully"
    
    # Verify the data was transformed
    results = execute_query(migration_db, "SELECT state FROM addresses")
    assert all(r["state"] == r["state"].upper() for r in results), "All states should be uppercase after migration"
    
    # Verify the migration was recorded
    applied = migration_manager.get_applied_migrations()
    assert "001_transform_addresses" in applied, "Migration should be recorded"


def test_sql_migration_file(migration_db, tmp_path):
    """Test applying a migration from a SQL file."""
    # Create a temporary migration file
    migration_dir = tmp_path / "migrations"
    migration_dir.mkdir()
    
    migration_file = migration_dir / "002_add_priority.sql"
    with open(migration_file, "w") as f:
        f.write("ALTER TABLE mail_items ADD COLUMN priority TEXT DEFAULT 'standard';")
    
    # Create the migration manager
    migration_manager = SchemaMigration(migration_db)
    
    # Apply the migration
    result = migration_manager.apply_migration(migration_file)
    
    # Verify the migration was applied
    assert result, "Migration should be applied successfully"
    
    # Verify the column was added
    cursor = migration_db.cursor()
    cursor.execute("PRAGMA table_info(mail_items)")
    columns = [row[1] for row in cursor.fetchall()]
    cursor.close()
    
    assert "priority" in columns, "Column should be added by the migration"


def test_multiple_migrations(migration_db, tmp_path):
    """Test applying multiple migrations in sequence."""
    # Create temporary migration files
    migration_dir = tmp_path / "migrations"
    migration_dir.mkdir()
    
    # First migration
    with open(migration_dir / "001_add_contact_preference.sql", "w") as f:
        f.write("ALTER TABLE customers ADD COLUMN contact_preference TEXT DEFAULT 'email';")
    
    # Second migration
    with open(migration_dir / "002_add_priority.sql", "w") as f:
        f.write("ALTER TABLE mail_items ADD COLUMN priority TEXT DEFAULT 'standard';")
    
    # Third migration
    with open(migration_dir / "003_add_cost_center.sql", "w") as f:
        f.write("ALTER TABLE print_jobs ADD COLUMN cost_center TEXT DEFAULT 'GENERAL';")
    
    # Create the migration manager
    migration_manager = SchemaMigration(migration_db)
    
    # Apply all migrations
    count = migration_manager.apply_migrations_from_directory(migration_dir)
    
    # Verify all migrations were applied
    assert count == 3, "All three migrations should be applied"
    
    # Verify all columns were added
    cursor = migration_db.cursor()
    
    cursor.execute("PRAGMA table_info(customers)")
    customer_columns = [row[1] for row in cursor.fetchall()]
    
    cursor.execute("PRAGMA table_info(mail_items)")
    mail_item_columns = [row[1] for row in cursor.fetchall()]
    
    cursor.execute("PRAGMA table_info(print_jobs)")
    print_job_columns = [row[1] for row in cursor.fetchall()]
    
    cursor.close()
    
    assert "contact_preference" in customer_columns, "Customer column should be added"
    assert "priority" in mail_item_columns, "Mail item column should be added"
    assert "cost_center" in print_job_columns, "Print job column should be added"
    
    # Verify migrations were recorded in the correct order
    applied = migration_manager.get_applied_migrations()
    assert applied == ["001_add_contact_preference", "002_add_priority", "003_add_cost_center"], \
        "Migrations should be recorded in the correct order"
