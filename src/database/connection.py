"""
Database connection utilities for SQLite.
This module provides functions to create, connect to, and manage SQLite databases.
"""
import sqlite3
from pathlib import Path
from typing import Optional, Union


def get_connection(db_path: Union[str, Path], in_memory: bool = False) -> sqlite3.Connection:
    """
    Get a connection to a SQLite database.
    
    Args:
        db_path: Path to the SQLite database file
        in_memory: If True, create an in-memory database instead of using the file
        
    Returns:
        A SQLite connection object
    """
    if in_memory:
        conn = sqlite3.connect(":memory:")
    else:
        db_path = Path(db_path)
        conn = sqlite3.connect(str(db_path))
    
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Return rows as dictionaries
    conn.row_factory = sqlite3.Row
    
    return conn


def execute_script(conn: sqlite3.Connection, script_path: Union[str, Path]) -> None:
    """
    Execute a SQL script file on a database connection.
    
    Args:
        conn: SQLite connection
        script_path: Path to the SQL script file
    """
    script_path = Path(script_path)
    with open(script_path, 'r') as f:
        script = f.read()
    
    conn.executescript(script)
    conn.commit()


def execute_query(
    conn: sqlite3.Connection, 
    query: str, 
    params: Optional[tuple] = None
) -> list:
    """
    Execute a SQL query and return the results.
    
    Args:
        conn: SQLite connection
        query: SQL query string
        params: Query parameters
        
    Returns:
        List of results as dictionaries
    """
    cursor = conn.cursor()
    
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    
    results = cursor.fetchall()
    cursor.close()
    
    # Convert row objects to dictionaries
    return [dict(row) for row in results]
