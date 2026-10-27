# Runbook — Banking Data Pipeline Capstone

## 1. Purpose

This runbook describes how to execute the Banking Data Pipeline, rerun it safely, diagnose failed runs and recover from failures.

The pipeline consists of three processing stages:

1. **Bronze:** Ingests raw branch transaction CSV files and records source lineage.
2. **Silver:** Validates and standardizes transactions, records rejected rows and handles corrections.
3. **Gold:** Aggregates accepted transactions by branch, transaction date and transaction type.

The orchestrator coordinates the stages and records execution status and failure information.

## 2. Prerequisites

Before executing the pipeline, confirm that:

- Python is installed and the project virtual environment is available.
- Java is installed and compatible with the installed PySpark version.
- Required Python dependencies are installed.
- Transaction CSV files follow the expected filename and column conventions.
- `account_reference.csv` exists in the configured input directory.
- The landing, database and output directories are accessible.

Run the following commands from the repository root in PowerShell:

```powershell
python --version
java -version
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the Capstone-specific dependencies, if required:

```powershell
python -m pip install -r requirements-capstone.txt
```

## 3. Normal Execution

### Step 1 — Prepare input files

Place the branch transaction CSV files in:

```text
capstone/landing/
```

Example filenames:

```text
BR001_20260906_TRANSACTION.csv
BR002_20260906_TRANSACTION.csv
BR003_20260906_TRANSACTION.csv
```

Ensure the supporting account reference file is present:

```text
capstone/input/account_reference.csv
```

Each transaction CSV must contain the required columns in the expected order:

```csv
transaction_id,account_id,transaction_date,transaction_type,amount,currency
```

### Step 2 — Run the pipeline

Execute:

```powershell
python .\capstone\orchestration\run_pipeline.py
```

The orchestrator runs Bronze, Silver and Gold in sequence.

### Step 3 — Verify the result

Confirm that the terminal output indicates successful execution and that no stage failed.

Inspect the published Gold report:

```text
capstone/output/gold/gold_branch_daily.csv
```

The Gold results should contain:

- `branch_id`
- `transaction_date`
- `transaction_type`
- `transaction_count`
- `total_amount`

Check the SQLite databases and audit records if further verification is needed.

## 4. Rerun Procedure

The pipeline supports rerunning without manually deleting all databases and output files.

### Step 1 — Review the previous run

Check the terminal output and orchestration audit records. Identify whether the run succeeded, failed or skipped unchanged input files.

### Step 2 — Decide whether input has changed

- If the input files are unchanged, rerunning should skip files already registered as unchanged.
- If a file has changed, its hash can cause it to be ingested again.
- If an already accepted transaction ID appears again, the current policy treats it as a correction.
- If the same transaction ID occurs multiple times within one incoming batch, all occurrences are rejected.

### Step 3 — Rerun the pipeline

```powershell
python .\capstone\orchestration\run_pipeline.py
```

### Step 4 — Verify the rerun

Check that:

- The pipeline status is successful.
- Unchanged files are skipped as expected.
- Corrected transactions are reflected in Silver and Gold.
- Rejected records have recorded reasons.
- Gold counts and totals match the expected results.

Do not reset databases merely to make a rerun succeed. Resetting them can remove useful lineage, correction history and audit evidence.

## 5. Failed-Run Diagnosis

When a pipeline run fails, do not immediately delete databases or published reports.

### Step 1 — Identify the failing stage

Use the terminal output and orchestration audit database to identify the failure stage.

The normal orchestration database is:

```text
capstone/database/orchestration.db
```

The audit table is:

```text
pipeline_run_audit
```

Review the overall status, stage statuses, error stage and error message for the relevant run.

### Step 2 — Diagnose Bronze failures

Typical symptoms:

- The CSV header is missing or malformed.
- The filename does not follow the expected pattern.
- The input file cannot be read.
- A file-level ingestion error is recorded.

Inspect:

```text
capstone/database/bronze.db
```

Relevant tables include:

- `bronze_transactions`
- `bronze_file_audit`
- `bronze_file_registry`

Check the input filename, required columns, file accessibility and Bronze audit message.

### Step 3 — Diagnose Silver failures

Typical symptoms:

- The account reference file is missing required columns.
- The reference data cannot be loaded.
- Unexpected processing errors occur.

Inspect:

```text
capstone/database/silver.db
```

Relevant tables include:

- `silver_transactions`
- `transaction_exceptions`
- `silver_file_audit`
- `silver_correction_audit`

Distinguish a pipeline-level processing failure from record-level validation rejections. Rejected transactions can be expected behavior and do not necessarily indicate that the entire pipeline failed.

### Step 4 — Diagnose Gold failures

Typical symptoms:

- No accepted Silver transactions are available.
- Gold aggregation or reconciliation fails.
- Gold database operations or CSV publication fail.

Inspect:

```text
capstone/database/gold.db
```

Relevant tables include:

- `gold_branch_daily`
- `gold_run_audit`

Check the error message and confirm whether the previous Gold output remains available.

### Step 5 — Preserve evidence

Before making changes, capture:

- The failed run identifier.
- The failure stage and error message.
- The affected filename, if applicable.
- Relevant audit records.
- The existing Gold CSV and database results.

This evidence helps distinguish the original failure from subsequent recovery attempts.

## 6. Recovery Procedure

### Step 1 — Preserve the last published Gold results

Do not manually delete the Gold database or report.

The pipeline's Gold failure test verifies that a failed Gold build preserves previously published Gold results for the tested failure scenario.

### Step 2 — Correct the underlying problem

Examples:

- Fix a malformed CSV header.
- Correct an invalid reference-data schema.
- Restore a missing input file.
- Correct invalid transaction data when the intended business value is known.

Avoid changing unrelated files or clearing databases.

### Step 3 — Rerun the pipeline

```powershell
python .\capstone\orchestration\run_pipeline.py
```

Use the same normal pipeline paths so the pipeline can reuse its existing database state and audit history.

### Step 4 — Verify recovery

Confirm that:

- The new run succeeds.
- The corrected input is processed.
- Gold contains the expected counts and totals.
- Previous audit history remains available.
- No unexpected duplicate transactions were introduced.
- The published report matches the Gold database.

The recovery regression test demonstrates the sequence:

```text
SUCCESS → FAILED → SUCCESS
```

It establishes that a malformed Bronze input can be corrected and successfully reprocessed without resetting the databases or deleting the Gold report.

## 7. Run Isolated Test Scenarios

Scenario runs use isolated directories under `capstone/test/` rather than the normal production-style Capstone paths.

For example:

```powershell
python .\capstone\orchestration\run_pipeline.py --test normal_input
python .\capstone\orchestration\run_pipeline.py --test invalid_records
python .\capstone\orchestration\run_pipeline.py --test duplicate_handling
python .\capstone\orchestration\run_pipeline.py --test late_arrival
python .\capstone\orchestration\run_pipeline.py --test failed_validation
python .\capstone\orchestration\run_pipeline.py --test rerun_safety
```

These commands are intended for scenario testing and evidence collection. Confirm that the scenario directory exists and contains the expected inputs before running it.

## 8. Regression Testing

Run the automated test suite:

```powershell
python -m pytest .\capstone\tests -v
```

Run a specific failure or recovery test:

```powershell
python -m pytest .\capstone\tests\test_bronze_failure.py -v
python -m pytest .\capstone\tests\test_silver_failure.py -v
python -m pytest .\capstone\tests\test_gold_failure.py -v
python -m pytest .\capstone\tests\test_pipeline_recovery.py -v
```

A successful test result confirms that the tested behavior passed. Review warnings separately; a warning does not necessarily mean that a test failed.

## 9. Operational Precautions

- Do not delete normal Capstone databases to resolve an ordinary rerun issue.
- Do not overwrite a previous Gold report manually during diagnosis.
- Keep test scenarios isolated from the normal landing, database and output directories.
- Preserve audit records when investigating failures.
- Do not treat record-level validation rejections as pipeline failures unless the orchestration status indicates a failed stage.
- Verify both the Gold database and CSV after recovery.
- If a failure persists after correcting the input, inspect the stage error and relevant audit tables before making further changes.

## 10. Recovery Success Criteria

A recovery is considered successful when:

1. The underlying issue has been corrected.
2. The rerun completes successfully.
3. Expected transactions appear in Silver and Gold.
4. Gold counts and totals match the expected results.
5. The previous failed run remains recorded in the audit history.
6. Previously published Gold output was not unnecessarily deleted during recovery.

This runbook provides a repeatable procedure for normal execution, safe reruns, failure investigation and operational recovery.