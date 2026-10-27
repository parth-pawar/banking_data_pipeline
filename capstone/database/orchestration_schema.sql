
CREATE TABLE IF NOT EXISTS pipeline_run_audit (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    overall_status TEXT NOT NULL
        CHECK (overall_status IN ('SUCCESS', 'FAILED')),
    bronze_status TEXT NOT NULL,
    silver_status TEXT NOT NULL,
    gold_status TEXT NOT NULL,
    bronze_ingested_files INTEGER NOT NULL DEFAULT 0,
    bronze_skipped_files INTEGER NOT NULL DEFAULT 0,
    bronze_failed_files INTEGER NOT NULL DEFAULT 0,
    silver_source_rows INTEGER NOT NULL DEFAULT 0,
    error_stage TEXT,
    error_message TEXT
);
