import sqlite3
from pathlib import Path

connection = sqlite3.connect(
    Path(__file__).resolve().parents[2] / "database" / "banking.db"
)

query = """
SELECT
    'customer' AS table_name,
    COUNT(*) AS row_count
FROM customer

UNION ALL

SELECT
    'branch',
    COUNT(*)
FROM branch

UNION ALL

SELECT
    'account',
    COUNT(*)
FROM account

UNION ALL

SELECT
    'transactions',
    COUNT(*)
FROM transactions;
"""
rows = connection.execute(query).fetchall()

for row in rows:
    print(row)

connection.close()