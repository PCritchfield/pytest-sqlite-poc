"""
SQLite user-defined functions and triggers.
This module provides custom functions that can be registered with SQLite.
"""
import re
import sqlite3
from datetime import datetime


def register_functions(conn: sqlite3.Connection) -> None:
    """
    Register all custom functions with the SQLite connection.

    Args:
        conn: SQLite connection
    """
    # Register scalar functions
    conn.create_function("calculate_postage", 2, calculate_postage)
    conn.create_function("validate_address", 1, validate_address)
    conn.create_function("generate_tracking", 1, generate_tracking)

    # Register aggregate functions
    conn.create_aggregate("batch_count", 1, BatchCounter)


def calculate_postage(weight: float, destination_zone: int) -> float:
    """
    Calculate postage cost based on weight and destination zone.

    Args:
        weight: Weight of the mail item in ounces
        destination_zone: Postal zone (1-9)

    Returns:
        Calculated postage cost
    """
    # Base rate
    base_rate = 0.55

    # Additional cost per ounce
    additional_per_ounce = 0.15

    # Zone multiplier (higher zones cost more)
    zone_multiplier = 1.0 + (destination_zone * 0.1)

    # Calculate total
    if weight <= 1.0:
        return base_rate * zone_multiplier
    else:
        additional_weight = weight - 1.0
        additional_cost = additional_weight * additional_per_ounce
        return (base_rate + additional_cost) * zone_multiplier


def validate_address(address_json: str) -> int:
    """
    Validate if an address is properly formatted.

    Args:
        address_json: JSON string containing address fields

    Returns:
        1 if valid, 0 if invalid
    """
    # In a real implementation, this would parse the JSON and validate each field
    # For this POC, we'll do a simple check for required fields

    required_patterns = [
        r'"street_line1"\s*:\s*"[^"]+',
        r'"city"\s*:\s*"[^"]+',
        r'"state"\s*:\s*"[^"]+',
        r'"postal_code"\s*:\s*"[^"]+',
    ]

    # Check if all required patterns are in the address_json
    for pattern in required_patterns:
        if not re.search(pattern, address_json):
            return 0

    # Simple postal code validation (US format)
    postal_match = re.search(r'"postal_code"\s*:\s*"(\d{5}(-\d{4})?)"', address_json)
    if not postal_match:
        return 0

    return 1


def generate_tracking(carrier_code: str) -> str:
    """
    Generate a tracking number for a mail item.

    Args:
        carrier_code: Code for the carrier (USPS, UPS, etc.)

    Returns:
        A tracking number string
    """
    # Get current timestamp for uniqueness
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # Format depends on carrier
    if carrier_code.upper() == "USPS":
        return f"USPS{timestamp}US"
    elif carrier_code.upper() == "UPS":
        return f"1Z{timestamp}UP"
    elif carrier_code.upper() == "FEDEX":
        return f"FDX{timestamp}FX"
    else:
        # Default format
        return f"TRK{timestamp}{carrier_code.upper()[:2]}"


class BatchCounter:
    """SQLite aggregate function to count items in a batch with custom logic."""

    def __init__(self):
        self.count = 0

    def step(self, value):
        """Process each row's value"""
        if value and str(value).strip():
            self.count += 1

    def finalize(self):
        """Return the final result"""
        return self.count


# Example of how to create a trigger using executescript
def create_triggers(conn: sqlite3.Connection) -> None:
    """
    Create database triggers.

    Args:
        conn: SQLite connection
    """
    # Trigger to update timestamps on record updates
    conn.executescript(
        """
    -- Update customer timestamps
    CREATE TRIGGER IF NOT EXISTS update_customer_timestamp
    AFTER UPDATE ON customers
    BEGIN
        UPDATE customers SET updated_at = CURRENT_TIMESTAMP
        WHERE customer_id = NEW.customer_id;
    END;

    -- Update address timestamps
    CREATE TRIGGER IF NOT EXISTS update_address_timestamp
    AFTER UPDATE ON addresses
    BEGIN
        UPDATE addresses SET updated_at = CURRENT_TIMESTAMP
        WHERE address_id = NEW.address_id;
    END;

    -- Auto-update print job status when all items are printed
    CREATE TRIGGER IF NOT EXISTS update_print_job_status
    AFTER UPDATE ON print_queue
    WHEN (SELECT COUNT(*) FROM print_queue
          WHERE job_id = NEW.job_id AND status != 'completed') = 0
    BEGIN
        UPDATE print_jobs
        SET status = 'completed', completed_date = CURRENT_TIMESTAMP
        WHERE job_id = NEW.job_id;
    END;
    """
    )

    conn.commit()
