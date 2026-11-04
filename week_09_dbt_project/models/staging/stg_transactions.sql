SELECT
    CAST(transaction_id AS VARCHAR) AS transaction_id,
    CAST(account_id AS VARCHAR) AS account_id,
    CAST(transaction_date AS DATE) AS transaction_date,
    CAST(amount AS DECIMAL(12, 2)) AS amount,
    CAST(transaction_type AS VARCHAR) AS transaction_type,
    CAST(currency AS VARCHAR) AS currency
FROM {{ ref('transactions') }}