-- 1. Transaction count and total amount by branch

-- Shows the number of transactions and total transaction amount for each branch. 
-- This helps compare transaction activity across branches.
SELECT
    b.branch_id,
    b.branch_name,
    COUNT(f.transaction_id) AS transaction_count,
    SUM(f.amount) AS total_amount
FROM fact_transaction f
JOIN dim_account a
    ON f.account_id = a.account_id
JOIN dim_branch b
    ON a.branch_id = b.branch_id
GROUP BY
    b.branch_id,
    b.branch_name
ORDER BY
    b.branch_id;




-- 2. Transaction count and total amount by transaction type

-- Shows the number of transactions and total transaction amount for each transaction type.
SELECT
    transaction_type,
    COUNT(transaction_id) AS transaction_count,
    SUM(amount) AS total_amount
FROM fact_transaction
GROUP BY
    transaction_type
ORDER BY
    transaction_type;





-- 3. Transaction activity by customer

-- Shows the number of transactions and total transaction amount for each customer.
SELECT
    c.customer_id,
    c.customer_name,
    COUNT(f.transaction_id) AS transaction_count,
    SUM(f.amount) AS total_amount
FROM fact_transaction f
JOIN dim_account a
    ON f.account_id = a.account_id
JOIN dim_customer c
    ON a.customer_id = c.customer_id
GROUP BY
    c.customer_id,
    c.customer_name
ORDER BY
    c.customer_id;




-- 4. Transaction activity by date

-- Shows the number of transactions and total transaction amount for each transaction date.
SELECT
    d.date,
    COUNT(f.transaction_id) AS transaction_count,
    SUM(f.amount) AS total_amount
FROM fact_transaction f
JOIN dim_date d
    ON f.transaction_date = d.date
GROUP BY
    d.date
ORDER BY
    d.date;




-- 5. Transaction activity by customer and branch

-- Shows transaction activity for each customer along with the branch associated with their account.
--This demonstrates how the fact table can be analyzed using multiple dimensions.
SELECT
    c.customer_id,
    c.customer_name,
    b.branch_id,
    b.branch_name,
    COUNT(f.transaction_id) AS transaction_count,
    SUM(f.amount) AS total_amount
FROM fact_transaction f
JOIN dim_account a
    ON f.account_id = a.account_id
JOIN dim_customer c
    ON a.customer_id = c.customer_id
JOIN dim_branch b
    ON a.branch_id = b.branch_id
GROUP BY
    c.customer_id,
    c.customer_name,
    b.branch_id,
    b.branch_name
ORDER BY
    c.customer_id;



-- 6. Average transaction amount by account type

-- Calculates the average transaction amount for each account type, such as CHECKING and SAVINGS.
SELECT
    a.account_type,
    COUNT(f.transaction_id) AS transaction_count,
    ROUND(AVG(f.amount), 2) AS average_transaction_amount
FROM fact_transaction f
JOIN dim_account a
    ON f.account_id = a.account_id
GROUP BY
    a.account_type
ORDER BY
    a.account_type;



-- 7. Largest individual transactions

-- Shows the largest individual transactions in the analytical dataset.
SELECT
    f.transaction_id,
    c.customer_name,
    b.branch_name,
    f.transaction_type,
    f.amount,
    f.transaction_date
FROM fact_transaction f
JOIN dim_account a
    ON f.account_id = a.account_id
JOIN dim_customer c
    ON a.customer_id = c.customer_id
JOIN dim_branch b
    ON a.branch_id = b.branch_id
ORDER BY
    f.amount DESC
LIMIT 5;