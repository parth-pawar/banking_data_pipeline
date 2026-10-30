PRAGMA foreign_keys = ON;

-- Grain: one row per customer.
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL
);

-- Grain: one row per account.
-- Account ownership is synthetic for this assignment.
CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
);

-- Grain: one row per recorded validation exception.
CREATE TABLE IF NOT EXISTS exceptions (
    exception_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    reason TEXT NOT NULL
);

-- Grain: one row per customer.
-- This table will be rebuilt from customers, accounts,
-- and accepted transactions in the existing Silver database.
CREATE TABLE IF NOT EXISTS customer_360 (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    account_count INTEGER NOT NULL DEFAULT 0,
    transaction_count INTEGER NOT NULL DEFAULT 0,
    total_transaction_amount REAL NOT NULL DEFAULT 0,
    last_transaction_date TEXT,
    FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
);

