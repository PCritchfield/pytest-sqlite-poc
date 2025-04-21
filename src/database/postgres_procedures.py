"""
PostgreSQL stored procedures and functions.

This module provides utilities for creating and managing PostgreSQL stored procedures
and functions for the mail printing and stuffing system.
"""
from typing import List, Optional, Union

from src.database.db_interface import DatabaseInterface


def create_stored_procedures(db: DatabaseInterface) -> None:
    """
    Create PostgreSQL stored procedures and functions.

    This function creates stored procedures and functions for the mail printing
    and stuffing system. It only works with PostgreSQL databases.

    Args:
        db: Database interface (must be PostgreSQL)

    Raises:
        ValueError: If the database is not PostgreSQL
    """
    # Verify that the database is PostgreSQL
    # First check the class name (most reliable)
    if db.__class__.__name__ == "PostgreSQLInterface":
        pass  # This is a PostgreSQL database
    # Fall back to the connection module check
    elif not hasattr(db.connection, "__module__") or "psycopg2" not in db.connection.__module__:
        raise ValueError("Stored procedures can only be created in PostgreSQL databases")

    # Create the stored procedures and functions
    _create_update_customer_procedure(db)
    _create_address_validation_function(db)
    _create_campaign_stats_function(db)
    _create_state_normalization_trigger(db)

    # Commit the changes
    db.commit()


def _create_update_customer_procedure(db: DatabaseInterface) -> None:
    """
    Create a stored procedure for updating customer information.

    Args:
        db: Database interface
    """
    procedure = """
    CREATE OR REPLACE PROCEDURE update_customer(
        p_customer_id INTEGER,
        p_name TEXT DEFAULT NULL,
        p_email TEXT DEFAULT NULL,
        p_phone TEXT DEFAULT NULL
    )
    LANGUAGE plpgsql
    AS $$
    BEGIN
        -- Update only the provided fields
        UPDATE customers
        SET
            name = COALESCE(p_name, name),
            email = COALESCE(p_email, email),
            phone = COALESCE(p_phone, phone),
            updated_at = CURRENT_TIMESTAMP
        WHERE customer_id = p_customer_id;

        -- Raise notice if no rows were updated
        IF NOT FOUND THEN
            RAISE NOTICE 'Customer with ID % not found', p_customer_id;
        END IF;
    END;
    $$;
    """
    db.execute(procedure)


def _create_address_validation_function(db: DatabaseInterface) -> None:
    """
    Create a function for validating addresses.

    Args:
        db: Database interface
    """
    function = """
    CREATE OR REPLACE FUNCTION validate_address(
        p_street_line1 TEXT,
        p_city TEXT,
        p_state TEXT,
        p_postal_code TEXT
    ) RETURNS BOOLEAN
    LANGUAGE plpgsql
    AS $$
    BEGIN
        -- Basic validation rules (simplified for example)
        -- In a real system, this would be more comprehensive

        -- Check for empty values
        IF p_street_line1 IS NULL OR p_street_line1 = '' THEN
            RETURN FALSE;
        END IF;

        IF p_city IS NULL OR p_city = '' THEN
            RETURN FALSE;
        END IF;

        IF p_state IS NULL OR p_state = '' THEN
            RETURN FALSE;
        END IF;

        IF p_postal_code IS NULL OR p_postal_code = '' THEN
            RETURN FALSE;
        END IF;

        -- Check state format (2 letters)
        IF LENGTH(p_state) != 2 THEN
            RETURN FALSE;
        END IF;

        -- Check postal code format (5 digits or 5+4)
        IF NOT (p_postal_code ~ '^[0-9]{5}$' OR p_postal_code ~ '^[0-9]{5}-[0-9]{4}$') THEN
            RETURN FALSE;
        END IF;

        -- All checks passed
        RETURN TRUE;
    END;
    $$;
    """
    db.execute(function)


def _create_campaign_stats_function(db: DatabaseInterface) -> None:
    """
    Create a function for calculating campaign statistics.

    Args:
        db: Database interface
    """
    # First drop the existing function if it exists
    drop_function = """DROP FUNCTION IF EXISTS get_campaign_stats(INTEGER);"""
    db.execute(drop_function)

    # Now create the function with the correct return types
    function = """
    CREATE OR REPLACE FUNCTION get_campaign_stats(p_campaign_id INTEGER)
    RETURNS TABLE (
        campaign_name TEXT,
        total_items BIGINT,
        pending_items BIGINT,
        printed_items BIGINT,
        delivered_items BIGINT,
        success_rate NUMERIC
    )
    LANGUAGE plpgsql
    AS $$
    BEGIN
        RETURN QUERY
        WITH campaign_data AS (
            SELECT
                c.name AS campaign_name,
                COUNT(mi.item_id) AS total_items,
                SUM(CASE WHEN mi.status = 'pending' THEN 1 ELSE 0 END) AS pending_items,
                SUM(CASE WHEN pq.status = 'printed' THEN 1 ELSE 0 END) AS printed_items,
                SUM(CASE WHEN dt.status = 'delivered' THEN 1 ELSE 0 END) AS delivered_items
            FROM mailing_campaigns c
            LEFT JOIN mail_items mi ON c.campaign_id = mi.campaign_id
            LEFT JOIN print_queue pq ON mi.item_id = pq.item_id
            LEFT JOIN delivery_tracking dt ON mi.item_id = dt.item_id
            WHERE c.campaign_id = p_campaign_id
            GROUP BY c.name
        )
        SELECT
            cd.campaign_name,
            cd.total_items,
            cd.pending_items,
            cd.printed_items,
            cd.delivered_items,
            CASE
                WHEN cd.total_items > 0 THEN (cd.delivered_items::NUMERIC / cd.total_items) * 100
                ELSE 0
            END AS success_rate
        FROM campaign_data cd;
    END;
    $$;
    """
    db.execute(function)


def _create_state_normalization_trigger(db: DatabaseInterface) -> None:
    """
    Create a trigger for normalizing state codes to uppercase.

    Args:
        db: Database interface
    """
    # First create the trigger function
    trigger_function = """
    CREATE OR REPLACE FUNCTION normalize_state_code()
    RETURNS TRIGGER
    LANGUAGE plpgsql
    AS $$
    BEGIN
        -- Convert state code to uppercase
        NEW.state = UPPER(NEW.state);
        RETURN NEW;
    END;
    $$;
    """
    db.execute(trigger_function)

    # Then create the trigger
    trigger = """
    DROP TRIGGER IF EXISTS normalize_state_trigger ON addresses;
    CREATE TRIGGER normalize_state_trigger
    BEFORE INSERT OR UPDATE ON addresses
    FOR EACH ROW
    EXECUTE FUNCTION normalize_state_code();
    """
    db.execute(trigger)


def call_update_customer(
    db: DatabaseInterface,
    customer_id: int,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
) -> None:
    """
    Call the update_customer stored procedure.

    Args:
        db: Database interface
        customer_id: ID of the customer to update
        name: New name (optional)
        email: New email (optional)
        phone: New phone (optional)

    Raises:
        ValueError: If the database is not PostgreSQL
    """
    # Verify that the database is PostgreSQL
    # First check the class name (most reliable)
    if db.__class__.__name__ == "PostgreSQLInterface":
        pass  # This is a PostgreSQL database
    # Fall back to the connection module check
    elif not hasattr(db.connection, "__module__") or "psycopg2" not in db.connection.__module__:
        raise ValueError("Stored procedures can only be called in PostgreSQL databases")

    # Create a fixed order list of parameters to match the procedure definition
    # The order must match: p_customer_id, p_name, p_email, p_phone
    params: List[Union[int, str]] = [customer_id]

    # Create the SQL statement parts
    sql_parts = ["CALL update_customer(%s"]

    # Add optional parameters in the correct order
    # First p_name
    if name is not None:
        params.append(name)
        sql_parts.append(", %s")
    else:
        sql_parts.append(", NULL")

    # Then p_email
    if email is not None:
        params.append(email)
        sql_parts.append(", %s")
    else:
        sql_parts.append(", NULL")

    # Then p_phone
    if phone is not None:
        params.append(phone)
        sql_parts.append(", %s")
    else:
        sql_parts.append(", NULL")

    # Close the statement
    sql_parts.append(")")

    # Build the complete SQL statement
    call_statement = "".join(sql_parts)

    # Execute the call
    db.execute(call_statement, tuple(params))
    db.commit()


def validate_address(db: DatabaseInterface, street_line1: str, city: str, state: str, postal_code: str) -> bool:
    """
    Call the validate_address function.

    Args:
        db: Database interface
        street_line1: Street address
        city: City
        state: State code
        postal_code: Postal code

    Returns:
        True if the address is valid, False otherwise

    Raises:
        ValueError: If the database is not PostgreSQL
    """
    # Verify that the database is PostgreSQL
    # First check the class name (most reliable)
    if db.__class__.__name__ == "PostgreSQLInterface":
        pass  # This is a PostgreSQL database
    # Fall back to the connection module check
    elif not hasattr(db.connection, "__module__") or "psycopg2" not in db.connection.__module__:
        raise ValueError("Stored functions can only be called in PostgreSQL databases")

    # Call the function
    results = db.query("SELECT validate_address(%s, %s, %s, %s) AS is_valid", (street_line1, city, state, postal_code))

    return results[0]["is_valid"]


def get_campaign_stats(db: DatabaseInterface, campaign_id: int) -> dict:
    """
    Call the get_campaign_stats function.

    Args:
        db: Database interface
        campaign_id: ID of the campaign

    Returns:
        Dictionary with campaign statistics

    Raises:
        ValueError: If the database is not PostgreSQL
    """
    # Verify that the database is PostgreSQL
    # First check the class name (most reliable)
    if db.__class__.__name__ == "PostgreSQLInterface":
        pass  # This is a PostgreSQL database
    # Fall back to the connection module check
    elif not hasattr(db.connection, "__module__") or "psycopg2" not in db.connection.__module__:
        raise ValueError("Stored functions can only be called in PostgreSQL databases")

    # Call the function
    results = db.query("SELECT * FROM get_campaign_stats(%s)", (campaign_id,))

    if results:
        return results[0]
    else:
        return {
            "campaign_name": None,
            "total_items": 0,
            "pending_items": 0,
            "printed_items": 0,
            "delivered_items": 0,
            "success_rate": 0,
        }
