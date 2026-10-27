
CREATE TABLE IF NOT EXISTS gold_branch_daily (
    branch_id TEXT NOT NULL,
    transaction_date TEXT NOT NULL,
    transaction_type TEXT NOT NULL
        CHECK (transaction_type IN ('CREDIT', 'DEBIT')),
    transaction_count INTEGER NOT NULL
        CHECK (transaction_count > 0),
    total_amount REAL NOT NULL
        CHECK (total_amount >= 0),
    published_run_id TEXT NOT NULL,

    PRIMARY KEY (
        branch_id,
        transaction_date,
        transaction_type
    )
);

CREATE TABLE IF NOT EXISTS gold_run_audit (
    run_id TEXT PRIMARY KEY,
    status TEXT NOT NULL
        CHECK (status IN ('SUCCESS', 'FAILED')),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    source_rows INTEGER NOT NULL DEFAULT 0,
    gold_groups INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);
