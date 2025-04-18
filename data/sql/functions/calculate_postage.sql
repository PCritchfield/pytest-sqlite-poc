-- Function to calculate postage based on weight and destination
-- This is a SQL implementation of the Python function we defined earlier

-- Note: In SQLite, we can't directly create stored procedures like in other databases
-- Instead, we'll define the logic in SQL that can be executed as a query

-- Calculate postage cost
-- Parameters:
--   weight: Weight of the mail item in ounces
--   destination_zone: Postal zone (1-9)
-- Returns: Calculated postage cost

SELECT 
    CASE 
        WHEN :weight <= 1.0 THEN 
            0.55 * (1.0 + (:destination_zone * 0.1))
        ELSE 
            (0.55 + ((:weight - 1.0) * 0.15)) * (1.0 + (:destination_zone * 0.1))
    END AS postage_cost;
