SELECT
    CAST(customer_id AS VARCHAR) AS customer_id,
    CAST(customer_name AS VARCHAR) AS customer_name,
    CAST(city AS VARCHAR) AS city,
    CAST(customer_segment AS VARCHAR) AS customer_segment
FROM {{ ref('customers') }}