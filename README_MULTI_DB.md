# Multi-Database Testing Support

This document explains how to use the new multi-database testing functionality in the pytest-sqlite-poc project.

## Overview

The project now supports testing against both SQLite and PostgreSQL databases. This allows you to:

1. Test your code against multiple database backends
2. Ensure database portability
3. Verify that your SQL is compatible with both database types

## Architecture

The multi-database support is implemented through several key components:

1. **Database Interface Abstraction** - A common interface for working with different database backends
2. **Schema Managers** - Database-specific schema creation and management
3. **Test Fixtures** - PyTest fixtures for creating and managing test databases
4. **Test Data Helper** - Functions for inserting test data into any database type

## Requirements

To use PostgreSQL testing, you'll need:

- PostgreSQL server installed and running
- psycopg2-binary Python package (added to dependencies)
- A PostgreSQL user with permissions to create and drop databases

## Usage

### Running Tests with SQLite (Default)

```bash
# Run tests with SQLite (default)
poetry run pytest
```

### Running Tests with PostgreSQL

```bash
# Run tests with PostgreSQL using default connection settings
poetry run pytest --db-type=postgres

# Run tests with custom PostgreSQL connection settings
poetry run pytest --db-type=postgres --pg-host=localhost --pg-port=5432 --pg-user=postgres --pg-password=postgres --pg-dbname=test_mail_system
```

### Command Line Options

The following command line options are available:

- `--db-type`: Database type to test against (`sqlite` or `postgres`, default: `sqlite`)
- `--pg-host`: PostgreSQL host (default: `localhost`)
- `--pg-port`: PostgreSQL port (default: `5432`)
- `--pg-user`: PostgreSQL username (default: `postgres`)
- `--pg-password`: PostgreSQL password (default: `postgres`)
- `--pg-dbname`: PostgreSQL database name (default: `test_mail_system`)

## Writing Multi-Database Tests

To write tests that work with both database types:

1. Use the `db_interface` fixture instead of the `db_connection` fixture
2. Use parameterized queries with `%s` placeholders (works for both SQLite and PostgreSQL)
3. Use the database interface methods (`execute`, `query`, etc.) instead of direct connection methods

Example:

```python
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
```

## Database Differences to Be Aware Of

When writing SQL that works with both databases, keep these differences in mind:

1. **Auto-increment columns**: SQLite uses `INTEGER PRIMARY KEY AUTOINCREMENT`, PostgreSQL uses `SERIAL`
2. **Boolean values**: SQLite uses `0`/`1`, PostgreSQL uses `TRUE`/`FALSE`
3. **Date/Time handling**: Different default formats and functions
4. **Case sensitivity**: PostgreSQL is case-sensitive for identifiers unless quoted
5. **Constraint handling**: Different syntax for some constraints

The database interface and schema managers handle most of these differences for you.

## Implementation Details

### Database Interface

The `DatabaseInterface` class provides a common interface for both database types:

- `connect()` - Establish a connection
- `close()` - Close the connection
- `execute()` - Execute a SQL query
- `execute_many()` - Execute a SQL query multiple times with different parameters
- `query()` - Execute a SQL query and return results as dictionaries
- `execute_script()` - Execute a SQL script
- `commit()` - Commit the current transaction
- `rollback()` - Roll back the current transaction

### Schema Managers

The schema managers handle database-specific schema creation:

- `SQLiteSchemaManager` - Creates tables with SQLite-specific syntax
- `PostgreSQLSchemaManager` - Creates tables with PostgreSQL-specific syntax

## Future Improvements

Potential future enhancements:

1. Add support for MySQL/MariaDB
2. Create migration tools that work across database types
3. Add performance comparison tests
4. Implement database-specific optimizations behind the common interface
