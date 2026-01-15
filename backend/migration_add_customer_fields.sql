-- Migration script to add city and total_orders to customers table
-- Run this if you already have an existing database

ALTER TABLE customers
ADD COLUMN IF NOT EXISTS city VARCHAR(100),
ADD COLUMN IF NOT EXISTS total_orders INTEGER DEFAULT 0;

-- Update existing customers with sample data
UPDATE customers SET city = 'Hà Nội', total_orders = 5 WHERE id = 1;

UPDATE customers
SET
    city = 'Hồ Chí Minh',
    total_orders = 3
WHERE
    id = 2;

UPDATE customers SET city = 'Đà Nẵng', total_orders = 8 WHERE id = 3;