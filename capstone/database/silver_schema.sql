PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS silver_transactions (
    transaction_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    branch_id TEXT NOT NULL,
    transaction_date TEXT NOT NULL,
    transaction_type TEXT NOT NULL
        CHECK (transaction_type IN ('CREDIT', 'DEBIT')),
    amount REAL NOT NULL CHECK (amount > 0),
    currency TEXT NOT NULL CHECK (currency = 'USD'),
    source_filename TEXT NOT NULL,
    file_date TEXT NOT NULL,
    source_row_number INTEGER NOT NULL,
    bronze_id INTEGER NOT NULL,
    accepted_run_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transaction_exceptions (
    exception_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bronze_id INTEGER NOT NULL,
    run_id TEXT NOT NULL,
    source_filename TEXT NOT NULL,
    branch_id TEXT NOT NULL,
    file_date TEXT NOT NULL,
    source_row_number INTEGER NOT NULL,
    transaction_id TEXT,
    rejection_reasons TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS silver_file_audit (
    run_id TEXT NOT NULL,
    source_filename TEXT NOT NULL,
    source_rows INTEGER NOT NULL DEFAULT 0,
    accepted_rows INTEGER NOT NULL DEFAULT 0,
    rejected_rows INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    error_message TEXT,
    PRIMARY KEY (run_id, source_filename)
);

CREATE TABLE IF NOT EXISTS silver_bronze_registry (
    bronze_id INTEGER PRIMARY KEY,
    first_processed_run_id TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (
    outcome IN ('ACCEPTED', 'REJECTED', 'CORRECTED')
)
);


CREATE TABLE IF NOT EXISTS silver_correction_audit (
    correction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT NOT NULL,
    old_account_id TEXT NOT NULL,
    new_account_id TEXT NOT NULL,
    old_branch_id TEXT NOT NULL,
    new_branch_id TEXT NOT NULL,
    old_transaction_date TEXT NOT NULL,
    new_transaction_date TEXT NOT NULL,
    old_transaction_type TEXT NOT NULL,
    new_transaction_type TEXT NOT NULL,
    old_amount REAL NOT NULL,
    new_amount REAL NOT NULL,
    old_currency TEXT NOT NULL,
    new_currency TEXT NOT NULL,
    old_bronze_id INTEGER NOT NULL,
    new_bronze_id INTEGER NOT NULL,
    correction_run_id TEXT NOT NULL,
    correction_timestamp TEXT NOT NULL,
    correction_reason TEXT NOT NULL
);