
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS bronze_transactions (
    bronze_id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Original values from the CSV
    transaction_id TEXT,
    account_id TEXT,
    transaction_date TEXT,
    transaction_type TEXT,
    amount TEXT,
    currency TEXT,

    -- Source lineage
    source_filename TEXT NOT NULL,
    branch_id TEXT NOT NULL,
    file_date TEXT NOT NULL,
    source_row_number INTEGER NOT NULL,
    raw_record TEXT NOT NULL,

    -- Ingestion metadata
    load_timestamp TEXT NOT NULL,
    run_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bronze_file_audit (
    run_id TEXT NOT NULL,
    source_filename TEXT NOT NULL,
    branch_id TEXT NOT NULL,
    file_date TEXT NOT NULL,
    source_rows INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    error_message TEXT,
    PRIMARY KEY (run_id, source_filename)
);

CREATE TABLE IF NOT EXISTS bronze_file_registry (
    source_filename TEXT PRIMARY KEY,
    file_hash TEXT NOT NULL,
    first_run_id TEXT NOT NULL,
    last_successful_run_id TEXT NOT NULL
);
