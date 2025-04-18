-- Migration: Add new columns to existing tables

-- Add priority field to mail_items
ALTER TABLE mail_items ADD COLUMN priority TEXT DEFAULT 'standard';

-- Add contact_preference to customers
ALTER TABLE customers ADD COLUMN contact_preference TEXT DEFAULT 'email';

-- Add cost_center to print_jobs
ALTER TABLE print_jobs ADD COLUMN cost_center TEXT;

-- Add notes field to delivery_tracking
ALTER TABLE delivery_tracking ADD COLUMN notes TEXT;
