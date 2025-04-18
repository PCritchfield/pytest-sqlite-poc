-- Function to validate an address
-- This is a SQL implementation of the Python function we defined earlier

-- Note: In SQLite, we can't directly create stored procedures like in other databases
-- Instead, we'll define the logic in SQL that can be executed as a query

-- Validate address
-- Parameters:
--   street_line1: First line of street address
--   city: City name
--   state: State code
--   postal_code: Postal/ZIP code
-- Returns: 1 if valid, 0 if invalid

SELECT
    CASE
        WHEN :street_line1 IS NULL OR LENGTH(TRIM(:street_line1)) = 0 THEN 0
        WHEN :city IS NULL OR LENGTH(TRIM(:city)) = 0 THEN 0
        WHEN :state IS NULL OR LENGTH(TRIM(:state)) = 0 THEN 0
        WHEN :postal_code IS NULL OR LENGTH(TRIM(:postal_code)) = 0 THEN 0
        -- Simple US postal code validation (5 digits or 5+4 format)
        WHEN :postal_code NOT REGEXP '^[0-9]{5}(-[0-9]{4})?$' THEN 0
        ELSE 1
    END AS is_valid;
