-- Initial database schema for mail printing and stuffing operations

-- Customers table
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    phone TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Addresses table
CREATE TABLE IF NOT EXISTS addresses (
    address_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    address_type TEXT NOT NULL,
    street_line1 TEXT NOT NULL,
    street_line2 TEXT,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'USA',
    is_verified BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE
);

-- Materials table
CREATE TABLE IF NOT EXISTS materials (
    material_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    unit_cost REAL NOT NULL,
    unit_type TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inventory table
CREATE TABLE IF NOT EXISTS inventory (
    inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    location TEXT,
    last_restock_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (material_id) REFERENCES materials (material_id) ON DELETE CASCADE
);

-- Mailing Lists table
CREATE TABLE IF NOT EXISTS mailing_lists (
    list_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- List Members table
CREATE TABLE IF NOT EXISTS list_members (
    member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    list_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    address_id INTEGER NOT NULL,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (list_id) REFERENCES mailing_lists (list_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE,
    FOREIGN KEY (address_id) REFERENCES addresses (address_id) ON DELETE CASCADE
);

-- Mailing Campaigns table
CREATE TABLE IF NOT EXISTS mailing_campaigns (
    campaign_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    list_id INTEGER NOT NULL,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (list_id) REFERENCES mailing_lists (list_id) ON DELETE CASCADE
);

-- Mail Items table
CREATE TABLE IF NOT EXISTS mail_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    address_id INTEGER NOT NULL,
    content_template TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES mailing_campaigns (campaign_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE,
    FOREIGN KEY (address_id) REFERENCES addresses (address_id) ON DELETE CASCADE
);

-- Print Jobs table
CREATE TABLE IF NOT EXISTS print_jobs (
    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'queued',
    scheduled_date TIMESTAMP,
    completed_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Print Queue table
CREATE TABLE IF NOT EXISTS print_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    print_order INTEGER,
    status TEXT DEFAULT 'queued',
    printed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES print_jobs (job_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES mail_items (item_id) ON DELETE CASCADE
);

-- Delivery Tracking table
CREATE TABLE IF NOT EXISTS delivery_tracking (
    tracking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    tracking_number TEXT,
    carrier TEXT,
    status TEXT DEFAULT 'pending',
    shipped_date TIMESTAMP,
    estimated_delivery TIMESTAMP,
    actual_delivery TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES mail_items (item_id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_addresses_customer_id ON addresses(customer_id);
CREATE INDEX IF NOT EXISTS idx_inventory_material_id ON inventory(material_id);
CREATE INDEX IF NOT EXISTS idx_list_members_list_id ON list_members(list_id);
CREATE INDEX IF NOT EXISTS idx_list_members_customer_id ON list_members(customer_id);
CREATE INDEX IF NOT EXISTS idx_mailing_campaigns_list_id ON mailing_campaigns(list_id);
CREATE INDEX IF NOT EXISTS idx_mail_items_campaign_id ON mail_items(campaign_id);
CREATE INDEX IF NOT EXISTS idx_mail_items_customer_id ON mail_items(customer_id);
CREATE INDEX IF NOT EXISTS idx_print_queue_job_id ON print_queue(job_id);
CREATE INDEX IF NOT EXISTS idx_print_queue_item_id ON print_queue(item_id);
CREATE INDEX IF NOT EXISTS idx_delivery_tracking_item_id ON delivery_tracking(item_id);

-- Create triggers for automatic updates
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
