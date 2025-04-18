"""
Schema migration utilities for SQLite.
This module provides functions to apply schema changes to the database.
"""
import os
import re
import sqlite3
from pathlib import Path
from typing import List, Optional, Union

from src.database.connection import execute_script


class SchemaMigration:
    """
    Class to handle schema migrations for SQLite databases.
    """
    
    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize the migration manager.
        
        Args:
            conn: SQLite connection
        """
        self.conn = conn
        self._ensure_migrations_table()
    
    def _ensure_migrations_table(self) -> None:
        """Create the migrations tracking table if it doesn't exist."""
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            migration_id TEXT UNIQUE NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
        ''')
        self.conn.commit()
    
    def get_applied_migrations(self) -> List[str]:
        """
        Get a list of already applied migrations.
        
        Returns:
            List of applied migration IDs
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT migration_id FROM schema_migrations ORDER BY id")
        migrations = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return migrations
    
    def apply_migration(self, migration_path: Union[str, Path], description: Optional[str] = None) -> bool:
        """
        Apply a single migration from a SQL file.
        
        Args:
            migration_path: Path to the migration SQL file
            description: Optional description of the migration
            
        Returns:
            True if migration was applied, False if already applied
        """
        migration_path = Path(migration_path)
        migration_id = migration_path.stem
        
        # Check if migration was already applied
        applied = self.get_applied_migrations()
        if migration_id in applied:
            return False
        
        # Apply the migration
        try:
            # Start a transaction
            self.conn.execute("BEGIN TRANSACTION")
            
            # Execute the migration script
            execute_script(self.conn, migration_path)
            
            # Record the migration
            self.conn.execute(
                "INSERT INTO schema_migrations (migration_id, description) VALUES (?, ?)",
                (migration_id, description or f"Applied from {migration_path.name}")
            )
            
            # Commit the transaction
            self.conn.commit()
            return True
            
        except Exception as e:
            # Rollback on error
            self.conn.rollback()
            raise RuntimeError(f"Migration failed: {str(e)}")
    
    def apply_migrations_from_directory(self, directory_path: Union[str, Path]) -> int:
        """
        Apply all migrations from a directory in order.
        
        Args:
            directory_path: Path to directory containing migration SQL files
            
        Returns:
            Number of migrations applied
        """
        directory_path = Path(directory_path)
        
        # Get all SQL files in the directory
        migration_files = sorted([
            f for f in directory_path.glob("*.sql")
            if re.match(r"^\d+_.*\.sql$", f.name)
        ])
        
        # Get already applied migrations
        applied = self.get_applied_migrations()
        
        # Apply each migration that hasn't been applied yet
        count = 0
        for migration_file in migration_files:
            migration_id = migration_file.stem
            if migration_id not in applied:
                self.apply_migration(migration_file)
                count += 1
        
        return count
    
    def rollback_migration(self, migration_id: str) -> bool:
        """
        Rollback a specific migration.
        
        Args:
            migration_id: ID of the migration to rollback
            
        Returns:
            True if rollback was successful, False if migration wasn't applied
        """
        # Check if migration was applied
        applied = self.get_applied_migrations()
        if migration_id not in applied:
            return False
        
        # Look for rollback file
        rollback_path = None
        for ext in [".down.sql", ".rollback.sql"]:
            path = Path(f"{migration_id}{ext}")
            if path.exists():
                rollback_path = path
                break
        
        if not rollback_path:
            raise FileNotFoundError(f"Rollback file for {migration_id} not found")
        
        try:
            # Start a transaction
            self.conn.execute("BEGIN TRANSACTION")
            
            # Execute the rollback script
            execute_script(self.conn, rollback_path)
            
            # Remove the migration record
            self.conn.execute(
                "DELETE FROM schema_migrations WHERE migration_id = ?",
                (migration_id,)
            )
            
            # Commit the transaction
            self.conn.commit()
            return True
            
        except Exception as e:
            # Rollback on error
            self.conn.rollback()
            raise RuntimeError(f"Rollback failed: {str(e)}")


def add_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    """
    Add a column to an existing table.
    
    Args:
        conn: SQLite connection
        table: Table name
        column: Column name
        definition: Column definition (type, constraints, etc.)
    """
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    conn.commit()


def rename_table(conn: sqlite3.Connection, old_name: str, new_name: str) -> None:
    """
    Rename a table.
    
    Args:
        conn: SQLite connection
        old_name: Current table name
        new_name: New table name
    """
    conn.execute(f"ALTER TABLE {old_name} RENAME TO {new_name}")
    conn.commit()


def create_index(conn: sqlite3.Connection, table: str, columns: List[str], index_name: Optional[str] = None) -> None:
    """
    Create an index on a table.
    
    Args:
        conn: SQLite connection
        table: Table name
        columns: List of column names to include in the index
        index_name: Optional custom index name
    """
    if not index_name:
        index_name = f"idx_{table}_{'_'.join(columns)}"
    
    column_str = ', '.join(columns)
    conn.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({column_str})")
    conn.commit()
