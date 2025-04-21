# PyTest SQLite POC

A proof of concept demonstrating PyTest with SQLite for database testing in a mail printing and stuffing system context.

## Project Overview

This POC demonstrates how to effectively use PyTest with SQLite for:

1. Testing complex database operations across multiple interconnected tables (10 tables modeling a mail printing system)
2. Managing and testing database migrations (both schema and data migrations)
3. Implementing and testing stored procedure-like functionality (using SQLite's user-defined functions and triggers)
4. Generating realistic test data with Faker
5. Setting up isolated test environments with in-memory databases
6. Implementing code quality practices with linting and formatting tools

## Project Structure

```
pytest-sqlite-poc/
├── src/
│   ├── database/       # Database connection and schema management
│   └── migrations/     # Database migration utilities
├── tests/              # PyTest test cases
├── data/               # Sample data and SQL scripts
│   └── sql/
│       ├── migrations/ # SQL migration scripts
│       └── functions/  # SQL function definitions
├── .flake8            # Flake8 linter configuration
├── .pre-commit-config.yaml # Pre-commit hooks configuration
├── CODE_QUALITY_PLAN.md # Plan for code quality improvements
├── CONTRIBUTING.md    # Contribution guidelines
├── pyproject.toml     # Poetry and tool configurations
└── Taskfile.yml       # Task automation definitions
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.10+ (if running locally)
- Poetry (if running locally)

### Setup with Docker (Recommended)

1. Clone this repository
   ```bash
   git clone https://github.com/yourusername/pytest-sqlite-poc.git
   cd pytest-sqlite-poc
   ```

2. Build and run with Task
   ```bash
   task setup
   ```
   This will:
   - Build the Docker container
   - Initialize the database
   - Apply migrations
   - Create sample data

3. Run the tests
   ```bash
   task test
   ```

### Local Setup (Alternative)

1. Install dependencies
   ```bash
   poetry install
   ```

2. Initialize the database
   ```bash
   poetry run python -c "from src.database.connection import get_connection; from src.database.schema import create_tables; conn = get_connection('data/mail.db'); create_tables(conn); conn.close()"
   ```

3. Apply migrations
   ```bash
   poetry run python -c "from src.database.connection import get_connection; from src.migrations.schema_migrations import SchemaMigration; conn = get_connection('data/mail.db'); migration = SchemaMigration(conn); migration.apply_migrations_from_directory('data/sql/migrations'); conn.close()"
   ```

4. Generate sample data
   ```bash
   poetry run python -c "from data.sample_data import generate_sample_data; generate_sample_data('data/mail.db')"
   ```

5. Run tests
   ```bash
   poetry run pytest
   ```

## Key Features

### Data Generation

- Dynamic sample data generation using Faker
- Realistic customer, address, and mailing data
- Configurable record counts
- Consistent relationships between tables
- Date-aware data generation with proper formatting

### Testing Approach

- In-memory SQLite databases for isolated testing
- Fixtures for different database states
- Comprehensive test coverage for:
  - Database schema validation
  - Data integrity and relationships
  - Custom SQL functions and triggers
  - Complex query performance
  - Migration processes

### Technical Stack

- Python 3.10+
- PyTest for test framework
- Faker for data generation
- SQLite for database
- Poetry for dependency management
- Docker for containerization
- Task for workflow automation

### Code Quality Tools

- **Black**: Code formatter that enforces a consistent style
- **isort**: Sorts and organizes imports
- **Flake8**: Linter that checks for style and potential errors
  - With flake8-docstrings for docstring style checking
- **mypy**: Static type checker
- **Bandit**: Security-focused linter
- **pre-commit**: Git hooks to enforce code quality checks before commits

### Code Quality

This project uses several tools to maintain code quality and consistency. You can run these tools using Task commands:

```bash
# Format code with Black and isort
task fmt

# Check if code is properly formatted without making changes
task fmt:check

# Run all linters (flake8, mypy, bandit)
task lint

# Run specific linter
task lint:flake8
task lint:mypy
task lint:bandit

# Run all code quality checks
task quality

# Fix common issues automatically
task fix:all
```

### Code Quality Plan

We have a phased approach to improving code quality in this project:

1. **Phase 1**: Basic code formatting and linting (completed)
2. **Phase 2**: Type annotations
3. **Phase 3**: Security improvements
4. **Phase 4**: Docstring standardization
5. **Phase 5**: Code complexity reduction

See [CODE_QUALITY_PLAN.md](CODE_QUALITY_PLAN.md) for more details.
```

### Pre-commit Hooks

To ensure code quality checks run automatically before each commit, install the pre-commit hooks:

```bash
# Inside the Docker container
poetry run pre-commit install

# Or locally if you have pre-commit installed
pre-commit install
```

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd pytest-sqlite-poc

# Install dependencies
poetry install

# Run tests
poetry run pytest
```

## Features

- Database schema with 10 interconnected tables for mail printing and stuffing operations
- Data import and validation testing
- Schema and data migration testing
- SQLite user-defined functions and triggers testing
- Integration testing across multiple tables

## Stretch Goal

- React frontend to display database contents and PyTest results
