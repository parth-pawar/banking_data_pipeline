import sqlite3
from pathlib import Path

connection = sqlite3.connect(
    Path(__file__).resolve().parents[2] / "database" / "analytics.db"
)

query = """
SELECT
    f.transaction_id,
    c.customer_name,
    b.branch_name,
    f.transaction_type,
    f.amount,
    f.transaction_date
FROM fact_transaction f
JOIN dim_customer c
    ON f.customer_id = c.customer_id
JOIN dim_branch b
    ON f.branch_id = b.branch_id
ORDER BY
    f.amount DESC
LIMIT 5;

"""

rows = connection.execute(query).fetchall()

for row in rows:
    print(row)

connection.close()