-- Migration: Modify constraints and add indexes

-- Create a new customers table with NOT NULL constraint on phone
CREATE TABLE customers_new (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    phone TEXT NOT NULL DEFAULT 'Unknown',  -- Adding NOT NULL constraint with default
    contact_preference TEXT DEFAULT 'email',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Copy data from old table to new table
INSERT INTO customers_new (customer_id, name, email, phone, contact_preference, created_at, updated_at)
SELECT customer_id, name, email, COALESCE(phone, 'Unknown'), contact_preference, created_at, updated_at
FROM customers;

-- Drop the old table
DROP TABLE customers;

-- Rename the new table to the original name
ALTER TABLE customers_new RENAME TO customers;

-- Add new indexes for performance
CREATE INDEX idx_customers_name ON customers(name);
CREATE INDEX idx_mail_items_priority ON mail_items(priority);
CREATE INDEX idx_print_jobs_status ON print_jobs(status);
