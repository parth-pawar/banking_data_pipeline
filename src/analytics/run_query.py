import sqlite3
from pathlib import Path

connection = sqlite3.connect(
    Path(__file__).resolve().parents[2] / "database" / "analytics.db"
)

query = """
SELECT
    'dim_customer' AS table_name,
    COUNT(*) AS row_count
FROM dim_customer

UNION ALL

SELECT
    'dim_branch',
    COUNT(*)
FROM dim_branch

UNION ALL

SELECT
    'dim_account',
    COUNT(*)
FROM dim_account

UNION ALL

SELECT
    'dim_date',
    COUNT(*)
FROM dim_date

UNION ALL

SELECT
    'fact_transaction',
    COUNT(*)
FROM fact_transaction;
"""

rows = connection.execute(query).fetchall()

for row in rows:
    print(row)

connection.close()