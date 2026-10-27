import csv
import uuid
import sqlite3
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

CAPSTONE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_BRONZE_DB = CAPSTONE_DIR / "database" / "bronze.db"
DEFAULT_SILVER_DB = CAPSTONE_DIR / "database" / "silver.db"
DEFAULT_ACCOUNT_REFERENCE = CAPSTONE_DIR / "input" / "account_reference.csv"


def load_account_reference(account_reference=DEFAULT_ACCOUNT_REFERENCE):
    accounts = {}

    with Path(account_reference).open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            account_id = row["account_id"].strip()
            accounts[account_id] = {
                "branch_id": row["branch_id"].strip(),
                "account_status": row["account_status"].strip(),
            }

    return accounts


def load_bronze_records(bronze_db=DEFAULT_BRONZE_DB):
    with sqlite3.connect(bronze_db) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            """
            SELECT
                bronze_id,
                transaction_id,
                account_id,
                transaction_date,
                transaction_type,
                amount,
                currency,
                source_filename,
                branch_id,
                file_date,
                source_row_number,
                run_id
            FROM bronze_transactions
            ORDER BY bronze_id
            """
        ).fetchall()

    return rows


def validate_record(row, accounts):
    reasons = []
    standardized_date = None

    # 1. Check required fields
    required_fields = [
        "transaction_id",
        "account_id",
        "transaction_date",
        "transaction_type",
        "amount",
        "currency",
    ]

    for field in required_fields:
        value = row[field]

        if value is None or not str(value).strip():
            reasons.append(f"MISSING_{field.upper()}")

    # 2. Validate and standardize the transaction date
    raw_date = row["transaction_date"]

    if raw_date is not None and str(raw_date).strip():
        raw_date = str(raw_date).strip()

        
        for date_format in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                parsed_date = datetime.strptime(
                    raw_date, date_format
                ).date()

                # Accept only the exact documented format.
                if parsed_date.strftime(date_format) == raw_date:
                    standardized_date = parsed_date.isoformat()
                    break
            except ValueError:
                continue


        if standardized_date is None:
            reasons.append("INVALID_TRANSACTION_DATE")

    # 3. Validate the amount
    raw_amount = row["amount"]

    if raw_amount is not None and str(raw_amount).strip():
        try:
            amount = Decimal(str(raw_amount).strip())

            if not amount.is_finite() or amount <= 0:
                reasons.append("INVALID_AMOUNT")
        except (InvalidOperation, ValueError):
            reasons.append("INVALID_AMOUNT")

    # 4. Validate the transaction type
    raw_type = row["transaction_type"]

    if raw_type is not None and str(raw_type).strip():
        transaction_type = str(raw_type).strip().upper()

        if transaction_type not in {"CREDIT", "DEBIT"}:
            reasons.append("UNSUPPORTED_TRANSACTION_TYPE")

    # 5. Validate the currency
    raw_currency = row["currency"]

    if raw_currency is not None and str(raw_currency).strip():
        currency = str(raw_currency).strip().upper()

        if currency != "USD":
            reasons.append("UNSUPPORTED_CURRENCY")

    # 6. Validate account existence, status, and branch
    raw_account_id = row["account_id"]

    if raw_account_id is not None and str(raw_account_id).strip():
        account_id = str(raw_account_id).strip()
        account = accounts.get(account_id)

        if account is None:
            reasons.append("UNKNOWN_ACCOUNT")
        else:
            if account["account_status"].upper() != "ACTIVE":
                reasons.append("INACTIVE_ACCOUNT")

            if (
                row["branch_id"] is None
                or account["branch_id"].upper() != str(row["branch_id"]).strip().upper()
            ):
                reasons.append("ACCOUNT_BRANCH_MISMATCH")

    return reasons, standardized_date







def save_silver_results(results, run_id, silver_db=DEFAULT_SILVER_DB):
    with sqlite3.connect(silver_db) as connection:
        existing_ids = {
            row[0]
            for row in connection.execute(
                "SELECT transaction_id FROM silver_transactions"
            ).fetchall()
        }

        accepted_count = 0
        rejected_count = 0
        corrected_count = 0
        file_counts = {}

        for result in results:
            filename = result["row"]["source_filename"]
            if filename not in file_counts:
                file_counts[filename] = {
                    "source_rows": 0,
                    "accepted_rows": 0,
                    "rejected_rows": 0,
                }
            file_counts[filename]["source_rows"] += 1

        for result in results:
            row = result["row"]
            reasons = list(result["reasons"])
            transaction_id = row["transaction_id"]
            filename = row["source_filename"]

            clean_id = (
                str(transaction_id).strip()
                if transaction_id is not None
                else ""
            )
            # Convert validated values to their standardized form.
            account_id = str(row["account_id"] or "").strip()
            branch_id = row["branch_id"]
            transaction_date = result["standardized_date"]
            transaction_type = str(row["transaction_type"] or "").strip().upper()
            currency = str(row["currency"] or "").strip().upper()

            if reasons:
                outcome = "REJECTED"
                rejected_count += 1
                file_counts[filename]["rejected_rows"] += 1

                connection.execute(
                    """
                    INSERT INTO transaction_exceptions (
                        bronze_id, run_id, source_filename,
                        branch_id, file_date, source_row_number,
                        transaction_id, rejection_reasons
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["bronze_id"],
                        run_id,
                        filename,
                        branch_id,
                        row["file_date"],
                        row["source_row_number"],
                        transaction_id,
                        ", ".join(sorted(set(reasons))),
                    ),
                )

                # Skip correction or insertion for rejected rows.
                connection.execute(
                    """
                    INSERT INTO silver_bronze_registry (
                        bronze_id, first_processed_run_id, outcome
                    )
                    VALUES (?, ?, ?)
                    """,
                    (row["bronze_id"], run_id, outcome),
                )
                continue

            # Only valid rows reach this point.
            amount = float(Decimal(str(row["amount"]).strip()))

            if clean_id in existing_ids:
                # This ID already exists: treat the incoming row as a correction.
                old_row = connection.execute(
                    """
                    SELECT account_id, branch_id, transaction_date,
                           transaction_type, amount, currency, bronze_id
                    FROM silver_transactions
                    WHERE transaction_id = ?
                    """,
                    (clean_id,),
                ).fetchone()

                connection.execute(
                    """
                    INSERT INTO silver_correction_audit (
                        transaction_id,
                        old_account_id, new_account_id,
                        old_branch_id, new_branch_id,
                        old_transaction_date, new_transaction_date,
                        old_transaction_type, new_transaction_type,
                        old_amount, new_amount,
                        old_currency, new_currency,
                        old_bronze_id, new_bronze_id,
                        correction_run_id, correction_timestamp,
                        correction_reason
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        clean_id,
                        old_row[0], account_id,
                        old_row[1], branch_id,
                        old_row[2], transaction_date,
                        old_row[3], transaction_type,
                        old_row[4], amount,
                        old_row[5], currency,
                        old_row[6], row["bronze_id"],
                        run_id,
                        datetime.now().isoformat(timespec="seconds"),
                        "Existing transaction ID received again; treated as correction",
                    ),
                )

                connection.execute(
                    """
                    UPDATE silver_transactions
                    SET account_id = ?,
                        branch_id = ?,
                        transaction_date = ?,
                        transaction_type = ?,
                        amount = ?,
                        currency = ?,
                        source_filename = ?,
                        file_date = ?,
                        source_row_number = ?,
                        bronze_id = ?,
                        accepted_run_id = ?
                    WHERE transaction_id = ?
                    """,
                    (
                        account_id,
                        branch_id,
                        transaction_date,
                        transaction_type,
                        amount,
                        currency,
                        filename,
                        row["file_date"],
                        row["source_row_number"],
                        row["bronze_id"],
                        run_id,
                        clean_id,
                    ),
                )

                outcome = "CORRECTED"
                corrected_count += 1
                file_counts[filename]["accepted_rows"] += 1

            else:
                # A new transaction ID: insert it into Silver.
                connection.execute(
                    """
                    INSERT INTO silver_transactions (
                        transaction_id, account_id, branch_id,
                        transaction_date, transaction_type, amount,
                        currency, source_filename, file_date,
                        source_row_number, bronze_id, accepted_run_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        clean_id,
                        account_id,
                        branch_id,
                        transaction_date,
                        transaction_type,
                        amount,
                        currency,
                        filename,
                        row["file_date"],
                        row["source_row_number"],
                        row["bronze_id"],
                        run_id,
                    ),
                )

                outcome = "ACCEPTED"
                accepted_count += 1
                file_counts[filename]["accepted_rows"] += 1
                existing_ids.add(clean_id)

            connection.execute(
                """
                INSERT INTO silver_bronze_registry (
                    bronze_id, first_processed_run_id, outcome
                )
                VALUES (?, ?, ?)
                """,
                (row["bronze_id"], run_id, outcome),
            )

        for filename, counts in file_counts.items():
            assert counts["source_rows"] == (
                counts["accepted_rows"] + counts["rejected_rows"]
            )

            connection.execute(
                """
                INSERT INTO silver_file_audit (
                    run_id, source_filename, source_rows,
                    accepted_rows, rejected_rows, status, error_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    filename,
                    counts["source_rows"],
                    counts["accepted_rows"],
                    counts["rejected_rows"],
                    "SUCCESS",
                    None,
                ),
            )

        print(f"Silver run ID: {run_id}")
        print(f"Bronze rows evaluated: {len(results)}")
        print(f"New transactions accepted: {accepted_count}")
        print(f"Corrections applied: {corrected_count}")
        print(f"Rejected rows: {rejected_count}")

        for filename, counts in file_counts.items():
            print(
                f"{filename}: "
                f"source={counts['source_rows']}, "
                f"accepted={counts['accepted_rows']}, "
                f"rejected={counts['rejected_rows']}"
            )




def process_silver(
    bronze_db=DEFAULT_BRONZE_DB,
    silver_db=DEFAULT_SILVER_DB,
    account_reference=DEFAULT_ACCOUNT_REFERENCE,
):
    accounts = load_account_reference(account_reference)
    all_rows = load_bronze_records(bronze_db)
    run_id = str(uuid.uuid4())

    # Find Bronze rows that Silver has not processed before.
    with sqlite3.connect(silver_db) as connection:
        processed_ids = {
            row[0]
            for row in connection.execute(
                "SELECT bronze_id FROM silver_bronze_registry"
            ).fetchall()
        }

    new_rows = [
        row for row in all_rows
        if row["bronze_id"] not in processed_ids
    ]

    if not new_rows:
        print(f"Silver run ID: {run_id}")
        print("No new Bronze rows to process.")
        print(f"Bronze rows already processed: {len(all_rows)}")
        return {
        "run_id": run_id,
        "status": "SUCCESS",
        "source_rows": 0,
    }

    # Pass 1: validate only new Bronze rows.
    results = []

    for row in new_rows:
        reasons, standardized_date = validate_record(row, accounts)

        results.append({
            "row": row,
            "reasons": reasons,
            "standardized_date": standardized_date,
        })

    # Pass 2: identify duplicate transaction IDs among new rows.
    transaction_id_counts = {}

    for result in results:
        transaction_id = result["row"]["transaction_id"]

        if transaction_id is not None and str(transaction_id).strip():
            transaction_id = str(transaction_id).strip()
            transaction_id_counts[transaction_id] = (
                transaction_id_counts.get(transaction_id, 0) + 1
            )

    for result in results:
        transaction_id = result["row"]["transaction_id"]

        if transaction_id is not None and str(transaction_id).strip():
            transaction_id = str(transaction_id).strip()

            if transaction_id_counts[transaction_id] > 1:
                result["reasons"].append("DUPLICATE_TRANSACTION_ID")

    # Pass 3: save decisions for the new rows.
    save_silver_results(results, run_id, silver_db)

    return {
        "run_id": run_id,
        "status": "SUCCESS",
        "source_rows": len(new_rows),
    }


if __name__ == "__main__":
    process_silver()
