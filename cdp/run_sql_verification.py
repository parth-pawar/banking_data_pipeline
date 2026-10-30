
import sqlite3
from pathlib import Path


CDP_DIR = Path(__file__).resolve().parent
DATABASE = CDP_DIR / "database" / "cdp.db"
SQL_FILE = CDP_DIR / "docs" / "sql_verification.sql"


def run_verification():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    sql_text = SQL_FILE.read_text(encoding="utf-8")

    statement = ""

    try:
        for line in sql_text.splitlines():
            statement += line + "\n"

            if sqlite3.complete_statement(statement):
                query = statement.strip()
                statement = ""

                if not query:
                    continue

                cursor = connection.execute(query)

                if cursor.description is not None:
                    print("\nQuery result:")
                    for row in cursor.fetchall():
                        print(dict(row))

        print("\nSQL verification completed.")

    finally:
        connection.close()


if __name__ == "__main__":
    run_verification()
