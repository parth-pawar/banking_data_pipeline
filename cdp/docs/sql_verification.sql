
-- Attach the trusted Silver database.
ATTACH DATABASE 'capstone/database/silver.db' AS silver;

-- 1. Independently calculate customer-level metrics.
WITH account_metrics AS (
    SELECT
        customer_id,
        COUNT(*) AS account_count
    FROM accounts
    GROUP BY customer_id
),
transaction_metrics AS (
    SELECT
        a.customer_id,
        COUNT(t.transaction_id) AS transaction_count,
        COALESCE(SUM(t.amount), 0) AS total_transaction_amount,
        MAX(t.transaction_date) AS last_transaction_date
    FROM accounts AS a
    LEFT JOIN silver.silver_transactions AS t
        ON t.account_id = a.account_id
    GROUP BY a.customer_id
)
SELECT
    c.customer_id,
    c.customer_name,
    COALESCE(am.account_count, 0) AS account_count,
    COALESCE(tm.transaction_count, 0) AS transaction_count,
    COALESCE(tm.total_transaction_amount, 0) AS total_transaction_amount,
    tm.last_transaction_date
FROM customers AS c
LEFT JOIN account_metrics AS am
    ON am.customer_id = c.customer_id
LEFT JOIN transaction_metrics AS tm
    ON tm.customer_id = c.customer_id
ORDER BY c.customer_id;

-- 2. Compare independently calculated metrics with customer_360.
WITH transaction_metrics AS (
    SELECT
        a.customer_id,
        COUNT(t.transaction_id) AS transaction_count,
        COALESCE(SUM(t.amount), 0) AS total_transaction_amount,
        MAX(t.transaction_date) AS last_transaction_date
    FROM accounts AS a
    LEFT JOIN silver.silver_transactions AS t
        ON t.account_id = a.account_id
    GROUP BY a.customer_id
)
SELECT
    g.customer_id,
    CASE
        WHEN g.account_count = (
            SELECT COUNT(*)
            FROM accounts AS a
            WHERE a.customer_id = g.customer_id
        )
        AND g.transaction_count = COALESCE(tm.transaction_count, 0)
        AND g.total_transaction_amount = COALESCE(tm.total_transaction_amount, 0)
        AND g.last_transaction_date IS tm.last_transaction_date
        THEN 'PASS'
        ELSE 'FAIL'
    END AS verification_status
FROM customer_360 AS g
LEFT JOIN transaction_metrics AS tm
    ON tm.customer_id = g.customer_id
ORDER BY g.customer_id;
