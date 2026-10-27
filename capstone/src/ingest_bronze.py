
import csv
import hashlib
import re
import sqlite3
import uuid
import json
from datetime import datetime, timezone
from pathlib import Path

CAPSTONE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_LANDING_DIR = CAPSTONE_DIR / "landing"
DEFAULT_DB_FILE = CAPSTONE_DIR / "database" / "bronze.db"

# Expected filename format:
# BR001_20260906_TRANSACTION.csv
FILENAME_PATTERN = re.compile(
    r"^(BR\d+)_(\d{8})_TRANSACTION\.csv$",
    re.IGNORECASE,
)

EXPECTED_COLUMNS = [
    "transaction_id",
    "account_id",
    "transaction_date",
    "transaction_type",
    "amount",
    "currency",
]


def sha256_file(file_path):
    """Return a SHA-256 hash of the file's contents."""
    digest = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            digest.update(chunk)

    return digest.hexdigest()


def parse_filename(filename):
    """Extract branch ID and file date from a recognized filename."""
    match = FILENAME_PATTERN.fullmatch(filename)

    if not match:
        return None

    branch_id, date_text = match.groups()

    try:
        file_date = datetime.strptime(date_text, "%Y%m%d").date()
    except ValueError:
        return None

    return branch_id.upper(), file_date.isoformat()


def new_run_id():
    return str(uuid.uuid4())


def utc_timestamp():
    return datetime.now(timezone.utc).isoformat()



def ingest_file(connection, file_path, run_id, timestamp):
    parsed = parse_filename(file_path.name)

    if parsed is None:
        connection.execute(
            """
            INSERT INTO bronze_file_audit (
                run_id, source_filename, branch_id, file_date,
                source_rows, status, error_message
            )
            VALUES (?, ?, ?, ?, 0, 'UNRECOGNIZED_FILENAME', ?)
            """,
            (
                run_id,
                file_path.name,
                "UNKNOWN",
                "UNKNOWN",
                "Filename does not match the expected pattern "
                "BR001_20260906_TRANSACTION.csv or contains an invalid date.",
            ),
        )
        print(f"Skipped unrecognized filename: {file_path.name}")
        return "SKIPPED"

    branch_id, file_date = parsed
    file_hash = sha256_file(file_path)

    registry = connection.execute(
        """
        SELECT file_hash
        FROM bronze_file_registry
        WHERE source_filename = ?
        """,
        (file_path.name,),
    ).fetchone()

    if registry and registry[0] == file_hash:
        connection.execute(
            """
            INSERT INTO bronze_file_audit (
                run_id, source_filename, branch_id, file_date,
                source_rows, status
            )
            VALUES (?, ?, ?, ?, 0, 'SKIPPED_UNCHANGED')
            """,
            (run_id, file_path.name, branch_id, file_date),
        )
        print(f"Skipped unchanged file: {file_path.name}")
        return "SKIPPED"

    with file_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError(f"{file_path.name}: CSV has no header")

        if reader.fieldnames != EXPECTED_COLUMNS:
            raise ValueError(
                f"{file_path.name}: unexpected columns "
                f"{reader.fieldnames!r}"
            )

        rows = list(reader)

    with connection:
        for row_number, row in enumerate(rows, start=1):
            raw_record = json.dumps(
                {column: row.get(column) for column in EXPECTED_COLUMNS},
                ensure_ascii=False,
            )

            connection.execute(
                """
                INSERT INTO bronze_transactions (
                    transaction_id, account_id, transaction_date,
                    transaction_type, amount, currency,
                    source_filename, branch_id, file_date,
                    source_row_number, raw_record,
                    load_timestamp, run_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("transaction_id"),
                    row.get("account_id"),
                    row.get("transaction_date"),
                    row.get("transaction_type"),
                    row.get("amount"),
                    row.get("currency"),
                    file_path.name,
                    branch_id,
                    file_date,
                    row_number,
                    raw_record,
                    timestamp,
                    run_id,
                ),
            )

        connection.execute(
            """
            INSERT INTO bronze_file_audit (
                run_id, source_filename, branch_id, file_date,
                source_rows, status
            )
            VALUES (?, ?, ?, ?, ?, 'INGESTED')
            """,
            (run_id, file_path.name, branch_id, file_date, len(rows)),
        )

        connection.execute(
            """
            INSERT INTO bronze_file_registry (
                source_filename, file_hash,
                first_run_id, last_successful_run_id
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(source_filename) DO UPDATE SET
                file_hash = excluded.file_hash,
                last_successful_run_id =
                    excluded.last_successful_run_id
            """,
            (file_path.name, file_hash, run_id, run_id),
        )

    print(f"Ingested {len(rows)} rows from {file_path.name}")
    return "INGESTED"




def main(landing_dir=DEFAULT_LANDING_DIR, db_file=DEFAULT_DB_FILE):
    landing_dir = Path(landing_dir)
    db_file = Path(db_file)

    run_id = new_run_id()
    timestamp = utc_timestamp()

    files = sorted(landing_dir.glob("*.csv"))

    if not files:
        print(f"No CSV files found in {landing_dir}")
        return

    ingested = 0
    skipped = 0
    failed = 0

    with sqlite3.connect(db_file) as connection:
        for file_path in files:
            try:
                result = ingest_file(
                    connection, file_path, run_id, timestamp
                )

                if result == "INGESTED":
                    ingested += 1
                else:
                    skipped += 1

            except (OSError, csv.Error, ValueError, sqlite3.Error) as error:
                failed += 1
                parsed = parse_filename(file_path.name)

                if parsed is None:
                    branch_id, file_date = "UNKNOWN", "UNKNOWN"
                else:
                    branch_id, file_date = parsed

                error_message = str(error)

                with connection:
                    connection.execute(
                        """
                        INSERT INTO bronze_file_audit (
                            run_id, source_filename, branch_id, file_date,
                            source_rows, status, error_message
                        )
                        VALUES (?, ?, ?, ?, 0, 'FAILED', ?)
                        """,
                        (
                            run_id,
                            file_path.name,
                            branch_id,
                            file_date,
                            error_message,
                        ),
                    )

                print(f"ERROR processing {file_path.name}: {error}")

    print("\nBronze ingestion summary")
    print(f"Run ID: {run_id}")
    print(f"Ingested files: {ingested}")
    print(f"Skipped files: {skipped}")
    print(f"Failed files: {failed}")
    print(f"Overall status: {'FAILED' if failed else 'SUCCESS'}")
    
    return {
    "run_id": run_id,
    "status": "FAILED" if failed else "SUCCESS",
    "ingested_files": ingested,
    "skipped_files": skipped,
    "failed_files": failed,
}


if __name__ == "__main__":
    main()

