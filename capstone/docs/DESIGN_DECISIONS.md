# Design Decisions

## 1. Duplicate Transaction Policy

If a transaction ID appears two or more times within the same incoming batch, **all occurrences of that ID are rejected** and recorded in Exceptions with the reason `DUPLICATE_TRANSACTION_ID`.

This prevents ambiguous duplicate records from contributing to Silver and Gold aggregates.

## 2. Correction Policy

The `transaction_id` is the business key used to identify an existing transaction.

If an already accepted transaction ID appears in a later batch, the new record is treated as a correction. The existing Silver record is updated, and the old and new values are recorded in `silver_correction_audit`.

This policy assumes transaction IDs are globally unique. If uniqueness is only guaranteed within a branch, a composite key such as `(branch_id, transaction_id)` would be required.

## 3. Idempotency Strategy

The pipeline uses file hashes and a Bronze file registry to identify unchanged files and skip their re-ingestion.

Silver tracks processed Bronze records to avoid processing the same Bronze record repeatedly. Transaction IDs identify existing records for correction handling, while Gold is rebuilt from accepted Silver data.

These mechanisms support safe reruns without manually deleting databases or previously published outputs.

## 4. SQL vs. PySpark

**SQLite and SQL** are used for persistent storage, audit records, data verification and direct aggregation checks. SQLite keeps the project self-contained and easy to inspect.

**PySpark** is used for the Gold aggregation, grouping accepted transactions by `branch_id`, `transaction_date` and `transaction_type`, and calculating transaction counts and total amounts.

Using both allows the pipeline to demonstrate SQL-based verification alongside a DataFrame-based transformation. SQL and PySpark aggregation results are compared to verify that they produce equivalent business results for the same accepted Silver data.

The current implementation runs PySpark locally; using PySpark does not by itself mean the pipeline is deployed on a distributed cluster.


## 5. Branch ID and Date Handling

### Branch ID Determination

The branch ID is extracted from the transaction filename using the naming convention:

`BRANCHID_YYYYMMDD_TRANSACTION.csv`

For example, `BR001_20260906_TRANSACTION.csv` identifies branch `BR001` and file date `2026-09-06`.

The extracted branch ID is stored as source metadata in Bronze. During Silver validation, the transaction's `account_id` is checked against `account_reference.csv`, and the account's registered branch is compared with the branch identified by the source filename. Records with inconsistent branch information are rejected.

### Filename Date vs. Transaction Date

The filename date represents the file's business or processing date, while `transaction_date` represents the date on which the transaction occurred. These dates serve different purposes and are not required to match.

The pipeline preserves both values: the filename date is stored as `file_date` for lineage, while the row-level `transaction_date` is validated and used for Gold aggregation.

A disagreement between these dates is not, by itself, treated as a validation failure. The row is evaluated using the transaction date and the other validation rules. This allows transactions from earlier business dates to arrive in later files without incorrectly changing their transaction dates.

If the row-level transaction date is invalid, the record is rejected with the applicable validation reason.