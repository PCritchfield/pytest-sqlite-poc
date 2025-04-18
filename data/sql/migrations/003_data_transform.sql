-- Migration: Transform existing data

-- Standardize state codes to uppercase
UPDATE addresses
SET state = UPPER(state);

-- Set priority based on campaign status
UPDATE mail_items
SET priority = 'high'
WHERE campaign_id IN (
    SELECT campaign_id 
    FROM mailing_campaigns 
    WHERE status = 'active' AND end_date <= date('now', '+7 days')
);

-- Update contact preference based on available data
UPDATE customers
SET contact_preference = 'phone'
WHERE phone IS NOT NULL AND email IS NULL;

-- Set default cost center for existing print jobs
UPDATE print_jobs
SET cost_center = 'GENERAL'
WHERE cost_center IS NULL;
