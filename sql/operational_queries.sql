
-- Query 1: Transactions with customer, account, and branch details
--
-- Purpose:
-- Show each transaction together with the customer, account,
-- and branch associated with it.

SELECT
    t.transaction_id,
    c.customer_name,
    a.account_id,
    b.branch_name,
    t.transaction_type,
    t.amount,
    t.currency,
    t.transaction_date
FROM transactions t
JOIN account a
    ON t.account_id = a.account_id
JOIN customer c
    ON a.customer_id = c.customer_id
JOIN branch b
    ON a.branch_id = b.branch_id
ORDER BY t.transaction_id;

-- Result:
-- ('T1001', 'Maya Patel', 'A1001', 'Downtown Branch', 'CREDIT', 500.0, 'USD', '2026-09-06')
-- ('T1002', 'Maya Patel', 'A1002', 'Downtown Branch', 'DEBIT', 125.5, 'USD', '2026-09-06')
-- ('T1007', 'Daniel Kim', 'A1007', 'Downtown Branch', 'DEBIT', 40.0, 'USD', '2026-09-06')
-- ('T2001', 'Sofia Martinez', 'A2001', 'North Branch', 'CREDIT', 900.0, 'USD', '2026-09-06')
-- ('T2005', 'Sofia Martinez', 'A2005', 'North Branch', 'CREDIT', 225.0, 'USD', '2026-09-06')
-- ('T2007', 'Noah Williams', 'A2007', 'North Branch', 'DEBIT', 60.0, 'USD', '2026-09-06')
-- ('T3001', 'Ava Thompson', 'A3001', 'Lake Branch', 'CREDIT', 1000.0, 'USD', '2026-09-06')
-- ('T3002', 'Ava Thompson', 'A3002', 'Lake Branch', 'DEBIT', 200.0, 'USD', '2026-09-06')
-- ('T3004', 'Ethan Brown', 'A3004', 'Lake Branch', 'CREDIT', 350.0, 'USD', '2026-09-06')
-- ('T3007', 'Ethan Brown', 'A3007', 'Lake Branch', 'DEBIT', 25.0, 'USD', '2026-09-06')


-- Query 2: Number of accounts by customer
--
-- Purpose:
-- Count how many accounts belong to each customer.

SELECT
    c.customer_id,
    c.customer_name,
    COUNT(a.account_id) AS account_count
FROM customer c
JOIN account a
    ON c.customer_id = a.customer_id
GROUP BY
    c.customer_id,
    c.customer_name
ORDER BY c.customer_id;

-- Result:
-- ('C1001', 'Maya Patel', 2)
-- ('C1002', 'Daniel Kim', 1)
-- ('C1003', 'Sofia Martinez', 2)
-- ('C1004', 'Noah Williams', 1)
-- ('C1005', 'Ava Thompson', 2)
-- ('C1006', 'Ethan Brown', 2)




-- Query 3: Transactions by branch
--
-- Purpose:
-- Count transactions and calculate total transaction value
-- for each branch.

SELECT
    b.branch_id,
    b.branch_name,
    COUNT(t.transaction_id) AS transaction_count,
    SUM(t.amount) AS total_amount
FROM branch b
JOIN account a
    ON b.branch_id = a.branch_id
JOIN transactions t
    ON a.account_id = t.account_id
GROUP BY
    b.branch_id,
    b.branch_name
ORDER BY b.branch_id;

-- Result:
-- ('BR001', 'Downtown Branch', 3, 665.5)
-- ('BR002', 'North Branch', 3, 1185.0)
-- ('BR003', 'Lake Branch', 4, 1575.0)



-- Query 4: Transaction count and total amount by customer
--
-- Purpose:
-- Calculate the number of transactions and total transaction
-- amount for each customer.

SELECT
    c.customer_id,
    c.customer_name,
    COUNT(t.transaction_id) AS transaction_count,
    SUM(t.amount) AS total_amount
FROM customer c
JOIN account a
    ON c.customer_id = a.customer_id
JOIN transactions t
    ON a.account_id = t.account_id
GROUP BY
    c.customer_id,
    c.customer_name
ORDER BY c.customer_id;

-- Result:
-- ('C1001', 'Maya Patel', 2, 625.5)
-- ('C1002', 'Daniel Kim', 1, 40.0)
-- ('C1003', 'Sofia Martinez', 2, 1125.0)
-- ('C1004', 'Noah Williams', 1, 60.0)
-- ('C1005', 'Ava Thompson', 2, 1200.0)
-- ('C1006', 'Ethan Brown', 2, 375.0)




-- Query 5: Transaction totals by branch and transaction type
--
-- Purpose:
-- Compare the number and total value of CREDIT and DEBIT
-- transactions at each branch.

SELECT
    b.branch_id,
    b.branch_name,
    t.transaction_type,
    COUNT(t.transaction_id) AS transaction_count,
    SUM(t.amount) AS total_amount
FROM branch b
JOIN account a
    ON b.branch_id = a.branch_id
JOIN transactions t
    ON a.account_id = t.account_id
GROUP BY
    b.branch_id,
    b.branch_name,
    t.transaction_type
ORDER BY
    b.branch_id,
    t.transaction_type;

-- Result:
-- ('BR001', 'Downtown Branch', 'CREDIT', 1, 500.0)
-- ('BR001', 'Downtown Branch', 'DEBIT', 2, 165.5)
-- ('BR002', 'North Branch', 'CREDIT', 2, 1125.0)
-- ('BR002', 'North Branch', 'DEBIT', 1, 60.0)
-- ('BR003', 'Lake Branch', 'CREDIT', 2, 1350.0)
-- ('BR003', 'Lake Branch', 'DEBIT', 2, 225.0)




-- Query 6: CREDIT and DEBIT transaction totals
--
-- Purpose:
-- Compare the number and total value of CREDIT and DEBIT
-- transactions across the entire database.

SELECT
    transaction_type,
    COUNT(transaction_id) AS transaction_count,
    SUM(amount) AS total_amount
FROM transactions
GROUP BY transaction_type
ORDER BY transaction_type;

-- Result:
-- ('CREDIT', 5, 2975.0)
-- ('DEBIT', 5, 450.5)





-- Query 7: Classify transactions into amount bands
--
-- Purpose:
-- Categorize each transaction as Small, Medium, or Large
-- based on its amount.

SELECT
    transaction_id,
    amount,
    CASE
        WHEN amount < 100 THEN 'Small'
        WHEN amount < 500 THEN 'Medium'
        ELSE 'Large'
    END AS amount_band
FROM transactions
ORDER BY amount;

-- Result:
-- ('T3007', 25.0, 'Small')
-- ('T1007', 40.0, 'Small')
-- ('T2007', 60.0, 'Small')
-- ('T1002', 125.5, 'Medium')
-- ('T3002', 200.0, 'Medium')
-- ('T2005', 225.0, 'Medium')
-- ('T3004', 350.0, 'Medium')
-- ('T1001', 500.0, 'Large')
-- ('T2001', 900.0, 'Large')
-- ('T3001', 1000.0, 'Large')




-- Query 8: Customers with total transaction amount above $500
--
-- Purpose:
-- Use a CTE to calculate each customer's total transaction
-- amount, then filter the derived results where the total is greater than $500.

WITH customer_totals AS (
    SELECT
        c.customer_id,
        c.customer_name,
        SUM(t.amount) AS total_amount
    FROM customer c
    JOIN account a
        ON c.customer_id = a.customer_id
    JOIN transactions t
        ON a.account_id = t.account_id
    GROUP BY
        c.customer_id,
        c.customer_name
)
SELECT
    customer_id,
    customer_name,
    total_amount
FROM customer_totals
WHERE total_amount > 500
ORDER BY total_amount DESC;

-- Result:
-- ('C1005', 'Ava Thompson', 1200.0)
-- ('C1003', 'Sofia Martinez', 1125.0)
-- ('C1001', 'Maya Patel', 625.5)




-- Query 9: Rank transactions within each customer
--
-- Purpose:
-- Rank each customer's transactions by transaction amount,
-- from highest to lowest.

SELECT
    c.customer_name,
    t.transaction_id,
    t.amount,
    RANK() OVER (
        PARTITION BY c.customer_id
        ORDER BY t.amount DESC
    ) AS transaction_rank
FROM customer c
JOIN account a
    ON c.customer_id = a.customer_id
JOIN transactions t
    ON a.account_id = t.account_id
ORDER BY
    c.customer_id,
    transaction_rank;

-- Result:
-- ('Maya Patel', 'T1001', 500.0, 1)
-- ('Maya Patel', 'T1002', 125.5, 2)
-- ('Daniel Kim', 'T1007', 40.0, 1)
-- ('Sofia Martinez', 'T2001', 900.0, 1)
-- ('Sofia Martinez', 'T2005', 225.0, 2)
-- ('Noah Williams', 'T2007', 60.0, 1)
-- ('Ava Thompson', 'T3001', 1000.0, 1)
-- ('Ava Thompson', 'T3002', 200.0, 2)
-- ('Ethan Brown', 'T3004', 350.0, 1)
-- ('Ethan Brown', 'T3007', 25.0, 2)





-- Query 10: Running transaction total for each account
--
-- Purpose:
-- Calculate the cumulative transaction amount for each account
-- in transaction date order.

SELECT
    account_id,
    transaction_id,
    transaction_date,
    amount,
    SUM(amount) OVER (
        PARTITION BY account_id
        ORDER BY transaction_date, transaction_id
    ) AS running_total
FROM transactions
ORDER BY
    account_id,
    transaction_date,
    transaction_id;

-- Result:
-- ('A1001', 'T1001', '2026-09-06', 500.0, 500.0)
-- ('A1002', 'T1002', '2026-09-06', 125.5, 125.5)
-- ('A1007', 'T1007', '2026-09-06', 40.0, 40.0)
-- ('A2001', 'T2001', '2026-09-06', 900.0, 900.0)
-- ('A2005', 'T2005', '2026-09-06', 225.0, 225.0)
-- ('A2007', 'T2007', '2026-09-06', 60.0, 60.0)
-- ('A3001', 'T3001', '2026-09-06', 1000.0, 1000.0)
-- ('A3002', 'T3002', '2026-09-06', 200.0, 200.0)
-- ('A3004', 'T3004', '2026-09-06', 350.0, 350.0)
-- ('A3007', 'T3007', '2026-09-06', 25.0, 25.0)



-- Query 11: Accounts with more CREDIT value than DEBIT value
--
-- Business question:
-- Which accounts have received more money through CREDIT
-- transactions than they have through DEBIT transactions?

SELECT
    a.account_id,
    c.customer_name,
    SUM(
        CASE
            WHEN t.transaction_type = 'CREDIT' THEN t.amount
            ELSE 0
        END
    ) AS total_credits,
    SUM(
        CASE
            WHEN t.transaction_type = 'DEBIT' THEN t.amount
            ELSE 0
        END
    ) AS total_debits
FROM account a
JOIN customer c
    ON a.customer_id = c.customer_id
JOIN transactions t
    ON a.account_id = t.account_id
GROUP BY
    a.account_id,
    c.customer_name
HAVING total_credits > total_debits
ORDER BY total_credits - total_debits DESC;

-- Result:
-- ('A3001', 'Ava Thompson', 1000.0, 0)
-- ('A2001', 'Sofia Martinez', 900.0, 0)
-- ('A1001', 'Maya Patel', 500.0, 0)
-- ('A3004', 'Ethan Brown', 350.0, 0)
-- ('A2005', 'Sofia Martinez', 225.0, 0)





-- Query 12: Branch with the highest transaction value
--
-- Business question:
-- Which branch has the highest total transaction value?

SELECT
    b.branch_id,
    b.branch_name,
    SUM(t.amount) AS total_transaction_value
FROM branch b
JOIN account a
    ON b.branch_id = a.branch_id
JOIN transactions t
    ON a.account_id = t.account_id
GROUP BY
    b.branch_id,
    b.branch_name
ORDER BY total_transaction_value DESC
LIMIT 1;

-- Result:
-- ('BR003', 'Lake Branch', 1575.0)
