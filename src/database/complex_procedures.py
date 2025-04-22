"""
Complex chained stored procedures for PostgreSQL.

This module provides utilities for creating and testing complex chained stored procedures
with branching execution paths for the mail printing and stuffing system.
"""
from typing import List, Optional

from src.database.db_interface import DatabaseInterface


def create_complex_procedures(db: DatabaseInterface) -> None:
    """
    Create complex chained stored procedures with branching execution paths.

    This function creates a set of interconnected stored procedures that demonstrate
    complex workflow processing with conditional branching.

    Args:
        db: Database interface (must be PostgreSQL)

    Raises:
        ValueError: If the database is not PostgreSQL
    """
    # Verify that the database is PostgreSQL
    if db.__class__.__name__ != "PostgreSQLInterface":
        raise ValueError("Complex stored procedures can only be created in PostgreSQL databases")

    # Create all the procedures in the chain
    _create_process_campaign_procedure(db)
    _create_process_priority_mail_procedure(db)
    _create_process_standard_mail_procedure(db)
    _create_assign_to_print_job_procedure(db)
    _create_schedule_delivery_procedure(db)
    _create_audit_logging_function(db)
    _create_audit_trigger(db)


def _create_process_campaign_procedure(db: DatabaseInterface) -> None:
    """
    Create the main procedure that processes a campaign and branches based on campaign status.

    Args:
        db: Database interface
    """
    procedure = """
    CREATE OR REPLACE PROCEDURE process_campaign(
        p_campaign_id INTEGER
    )
    LANGUAGE plpgsql
    AS $$
    DECLARE
        v_campaign_status TEXT;
        v_campaign_name TEXT;
        v_list_id INTEGER;
        v_priority BOOLEAN;
    BEGIN
        -- First, check if the campaign exists and get its status
        SELECT status, name, list_id INTO v_campaign_status, v_campaign_name, v_list_id
        FROM mailing_campaigns
        WHERE campaign_id = p_campaign_id;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Campaign with ID % not found', p_campaign_id;
        END IF;

        -- Log the start of campaign processing
        INSERT INTO audit_log (action, related_id, details)
        VALUES ('CAMPAIGN_PROCESSING_STARTED', p_campaign_id,
                format('Started processing campaign %s with status %s', v_campaign_name, v_campaign_status));

        -- First branch: Only process active campaigns
        IF v_campaign_status != 'active' THEN
            -- Log the skipped campaign
            INSERT INTO audit_log (action, related_id, details)
            VALUES ('CAMPAIGN_PROCESSING_SKIPPED', p_campaign_id,
                    format('Campaign %s skipped because status is %s', v_campaign_name, v_campaign_status));
            RETURN;
        END IF;

        -- Update campaign status to processing
        UPDATE mailing_campaigns
        SET status = 'processing', updated_at = CURRENT_TIMESTAMP
        WHERE campaign_id = p_campaign_id;

        -- Second branch: Determine if this is a priority campaign
        v_priority := (v_campaign_name LIKE '%Priority%' OR v_campaign_name LIKE '%Urgent%');

        -- Process mail items based on priority
        IF v_priority THEN
            -- Call priority mail procedure
            CALL process_priority_mail(p_campaign_id);
        ELSE
            -- Call standard mail procedure
            CALL process_standard_mail(p_campaign_id);
        END IF;

        -- Update campaign status to processed
        UPDATE mailing_campaigns
        SET status = 'processed', updated_at = CURRENT_TIMESTAMP
        WHERE campaign_id = p_campaign_id;

        -- Log the completion of campaign processing
        INSERT INTO audit_log (action, related_id, details)
        VALUES ('CAMPAIGN_PROCESSING_COMPLETED', p_campaign_id,
                format('Completed processing campaign %s', v_campaign_name));
    END;
    $$;
    """
    db.execute(procedure)


def _create_process_priority_mail_procedure(db: DatabaseInterface) -> None:
    """
    Create procedure for processing priority mail items.

    Args:
        db: Database interface
    """
    procedure = """
    CREATE OR REPLACE PROCEDURE process_priority_mail(
        p_campaign_id INTEGER
    )
    LANGUAGE plpgsql
    AS $$
    DECLARE
        v_item_cursor CURSOR FOR
            SELECT item_id, customer_id, address_id
            FROM mail_items
            WHERE campaign_id = p_campaign_id AND status = 'pending';
        v_item_record RECORD;
        v_job_id INTEGER;
    BEGIN
        -- Log the start of priority mail processing
        INSERT INTO audit_log (action, related_id, details)
        VALUES ('PRIORITY_MAIL_PROCESSING_STARTED', p_campaign_id,
                'Started processing priority mail items');

        -- Create a high-priority print job for this campaign
        INSERT INTO print_jobs (name, description, status, scheduled_date)
        VALUES (
            format('Priority Job for Campaign %s', p_campaign_id),
            'High priority mail items that need expedited processing',
            'pending',
            CURRENT_DATE
        )
        RETURNING job_id INTO v_job_id;

        -- Process each mail item
        OPEN v_item_cursor;
        LOOP
            FETCH v_item_cursor INTO v_item_record;
            EXIT WHEN NOT FOUND;

            -- Update mail item status
            UPDATE mail_items
            SET status = 'processing', updated_at = CURRENT_TIMESTAMP
            WHERE item_id = v_item_record.item_id;

            -- Assign to print job with high priority (low print_order number)
            CALL assign_to_print_job(v_item_record.item_id, v_job_id, 10);

            -- Schedule expedited delivery
            CALL schedule_delivery(v_item_record.item_id, 'expedited');
        END LOOP;
        CLOSE v_item_cursor;

        -- Log the completion of priority mail processing
        INSERT INTO audit_log (action, related_id, details)
        VALUES ('PRIORITY_MAIL_PROCESSING_COMPLETED', p_campaign_id,
                format('Completed processing priority mail items for job %s', v_job_id));
    END;
    $$;
    """
    db.execute(procedure)


def _create_process_standard_mail_procedure(db: DatabaseInterface) -> None:
    """
    Create procedure for processing standard mail items.

    Args:
        db: Database interface
    """
    procedure = """
    CREATE OR REPLACE PROCEDURE process_standard_mail(
        p_campaign_id INTEGER
    )
    LANGUAGE plpgsql
    AS $$
    DECLARE
        v_item_cursor CURSOR FOR
            SELECT item_id, customer_id, address_id
            FROM mail_items
            WHERE campaign_id = p_campaign_id AND status = 'pending';
        v_item_record RECORD;
        v_job_id INTEGER;
        v_batch_size INTEGER := 0;
        v_current_batch INTEGER := 0;
    BEGIN
        -- Log the start of standard mail processing
        INSERT INTO audit_log (action, related_id, details)
        VALUES ('STANDARD_MAIL_PROCESSING_STARTED', p_campaign_id,
                'Started processing standard mail items');

        -- Create a standard print job for this campaign
        INSERT INTO print_jobs (name, description, status, scheduled_date)
        VALUES (
            format('Standard Job for Campaign %s', p_campaign_id),
            'Standard mail items for regular processing',
            'pending',
            CURRENT_DATE + 1  -- Schedule for tomorrow
        )
        RETURNING job_id INTO v_job_id;

        -- Count total items to process
        SELECT COUNT(*) INTO v_batch_size
        FROM mail_items
        WHERE campaign_id = p_campaign_id AND status = 'pending';

        -- Process each mail item
        OPEN v_item_cursor;
        LOOP
            FETCH v_item_cursor INTO v_item_record;
            EXIT WHEN NOT FOUND;

            v_current_batch := v_current_batch + 1;

            -- Update mail item status
            UPDATE mail_items
            SET status = 'processing', updated_at = CURRENT_TIMESTAMP
            WHERE item_id = v_item_record.item_id;

            -- Assign to print job with standard priority (higher print_order number)
            CALL assign_to_print_job(v_item_record.item_id, v_job_id, 100 + v_current_batch);

            -- Schedule standard delivery
            CALL schedule_delivery(v_item_record.item_id, 'standard');
        END LOOP;
        CLOSE v_item_cursor;

        -- Log the completion of standard mail processing
        INSERT INTO audit_log (action, related_id, details)
        VALUES ('STANDARD_MAIL_PROCESSING_COMPLETED', p_campaign_id,
                format('Completed processing %s standard mail items for job %s', v_batch_size, v_job_id));
    END;
    $$;
    """
    db.execute(procedure)


def _create_assign_to_print_job_procedure(db: DatabaseInterface) -> None:
    """
    Create procedure for assigning mail items to print jobs.

    Args:
        db: Database interface
    """
    procedure = """
    CREATE OR REPLACE PROCEDURE assign_to_print_job(
        p_item_id INTEGER,
        p_job_id INTEGER,
        p_print_order INTEGER
    )
    LANGUAGE plpgsql
    AS $$
    BEGIN
        -- Add the item to the print queue
        INSERT INTO print_queue (job_id, item_id, print_order, status)
        VALUES (p_job_id, p_item_id, p_print_order, 'queued');

        -- Log the assignment
        INSERT INTO audit_log (action, related_id, details)
        VALUES ('ITEM_ASSIGNED_TO_PRINT_JOB', p_item_id,
                format('Mail item assigned to print job %s with order %s', p_job_id, p_print_order));
    END;
    $$;
    """
    db.execute(procedure)


def _create_schedule_delivery_procedure(db: DatabaseInterface) -> None:
    """
    Create procedure for scheduling mail delivery.

    Args:
        db: Database interface
    """
    procedure = """
    CREATE OR REPLACE PROCEDURE schedule_delivery(
        p_item_id INTEGER,
        p_delivery_type TEXT
    )
    LANGUAGE plpgsql
    AS $$
    DECLARE
        v_tracking_number TEXT;
        v_carrier TEXT;
        v_estimated_days INTEGER;
    BEGIN
        -- Generate a fake tracking number
        v_tracking_number := 'TRK' || p_item_id || '-' || floor(random() * 10000)::TEXT;

        -- Third branch: Determine carrier and delivery timeframe based on delivery type
        IF p_delivery_type = 'expedited' THEN
            v_carrier := 'Express Courier';
            v_estimated_days := 1;
        ELSIF p_delivery_type = 'priority' THEN
            v_carrier := 'Priority Mail';
            v_estimated_days := 3;
        ELSE
            v_carrier := 'Standard Post';
            v_estimated_days := 5;
        END IF;

        -- Create delivery tracking record
        INSERT INTO delivery_tracking (
            item_id,
            tracking_number,
            carrier,
            status,
            shipped_date,
            estimated_delivery_date
        )
        VALUES (
            p_item_id,
            v_tracking_number,
            v_carrier,
            'scheduled',
            CURRENT_DATE,
            CURRENT_DATE + v_estimated_days
        );

        -- Log the delivery scheduling
        INSERT INTO audit_log (action, related_id, details)
        VALUES ('DELIVERY_SCHEDULED', p_item_id,
                format('Delivery scheduled via %s with tracking number %s', v_carrier, v_tracking_number));
    END;
    $$;
    """
    db.execute(procedure)


def _create_audit_logging_function(db: DatabaseInterface) -> None:
    """
    Create an audit logging table and function.

    Args:
        db: Database interface
    """
    # First create the audit log table if it doesn't exist
    audit_table = """
    CREATE TABLE IF NOT EXISTS audit_log (
        log_id SERIAL PRIMARY KEY,
        action TEXT NOT NULL,
        related_id INTEGER,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    db.execute(audit_table)

    # Create a function to log changes to mail items
    function = """
    CREATE OR REPLACE FUNCTION log_mail_item_changes()
    RETURNS TRIGGER
    LANGUAGE plpgsql
    AS $$
    BEGIN
        IF TG_OP = 'UPDATE' THEN
            -- Log status changes
            IF OLD.status != NEW.status THEN
                INSERT INTO audit_log (action, related_id, details)
                VALUES (
                    'MAIL_ITEM_STATUS_CHANGED',
                    NEW.item_id,
                    format('Status changed from %s to %s', OLD.status, NEW.status)
                );
            END IF;
        ELSIF TG_OP = 'INSERT' THEN
            -- Log new mail items
            INSERT INTO audit_log (action, related_id, details)
            VALUES (
                'MAIL_ITEM_CREATED',
                NEW.item_id,
                format('New mail item created for campaign %s', NEW.campaign_id)
            );
        END IF;

        RETURN NEW;
    END;
    $$;
    """
    db.execute(function)


def _create_audit_trigger(db: DatabaseInterface) -> None:
    """
    Create triggers for audit logging.

    Args:
        db: Database interface
    """
    # Create a trigger for mail items
    trigger = """
    DROP TRIGGER IF EXISTS mail_item_audit_trigger ON mail_items;
    CREATE TRIGGER mail_item_audit_trigger
    AFTER INSERT OR UPDATE ON mail_items
    FOR EACH ROW
    EXECUTE FUNCTION log_mail_item_changes();
    """
    db.execute(trigger)


def call_process_campaign(db: DatabaseInterface, campaign_id: int) -> None:
    """
    Call the process_campaign stored procedure.

    Args:
        db: Database interface
        campaign_id: ID of the campaign to process

    Raises:
        ValueError: If the database is not PostgreSQL
    """
    # Verify that the database is PostgreSQL
    if db.__class__.__name__ != "PostgreSQLInterface":
        raise ValueError("Complex stored procedures can only be called in PostgreSQL databases")

    # Call the procedure
    db.execute("CALL process_campaign(%s)", (campaign_id,))
    db.commit()


def get_audit_logs(db: DatabaseInterface, related_id: Optional[int] = None) -> List[dict]:
    """
    Get audit logs from the database.

    Args:
        db: Database interface
        related_id: Optional ID to filter logs by

    Returns:
        List of audit log entries

    Raises:
        ValueError: If the database is not PostgreSQL
    """
    # Verify that the database is PostgreSQL
    if db.__class__.__name__ != "PostgreSQLInterface":
        raise ValueError("Audit logs are only available in PostgreSQL databases")

    # Query the logs
    if related_id is not None:
        return db.query("SELECT * FROM audit_log WHERE related_id = %s ORDER BY created_at", (related_id,))
    else:
        return db.query("SELECT * FROM audit_log ORDER BY created_at")
