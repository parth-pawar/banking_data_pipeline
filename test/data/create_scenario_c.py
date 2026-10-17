import shutil
import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DATABASE = PROJECT_ROOT / "test" / "data" / "scenario_b.db"
RECOVERY_DATABASE = PROJECT_ROOT / "test" / "data" / "scenario_c.db"


def create_recovery_database():
    if not SOURCE_DATABASE.is_file():
        raise FileNotFoundError(
            f"Scenario B database not found: {SOURCE_DATABASE}"
        )

    if RECOVERY_DATABASE.exists():
        raise FileExistsError(
            f"Scenario C database already exists: {RECOVERY_DATABASE}. "
            "Delete it manually if you want to recreate it."
        )

    # Copy the failed test database, preserving Scenario B.
    shutil.copy2(SOURCE_DATABASE, RECOVERY_DATABASE)

    with sqlite3.connect(RECOVERY_DATABASE) as connection:
        # Remove the deliberately invalid transaction.
        cursor = connection.execute(
            "DELETE FROM transactions WHERE transaction_id = ?",
            ("T_BAD_ACCOUNT",),
        )

        if cursor.rowcount != 1:
            raise RuntimeError(
                f"Expected to remove one invalid transaction; "
                f"removed {cursor.rowcount}."
            )

        transaction_count = connection.execute(
            "SELECT COUNT(*) FROM transactions"
        ).fetchone()[0]

        orphan_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM transactions AS t
            LEFT JOIN account AS a
                ON t.account_id = a.account_id
            WHERE a.account_id IS NULL
            """
        ).fetchone()[0]

        if orphan_count != 0:
            raise RuntimeError(
                f"Recovery database still contains {orphan_count} orphan(s)."
            )

    print(f"Copied from: {SOURCE_DATABASE}")
    print(f"Recovery database: {RECOVERY_DATABASE}")
    print(f"Remaining transactions: {transaction_count}")
    print(f"Orphan transactions: {orphan_count}")


if __name__ == "__main__":
    create_recovery_database()
