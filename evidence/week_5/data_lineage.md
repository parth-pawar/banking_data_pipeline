# Architecture and Data Lineage

The Week 5 pipeline processes raw branch transaction files through validation, loads trusted transactions into the operational database, and then transforms the trusted relational data into a separate analytical database.

```mermaid
flowchart TD

    A["data/raw/<br/>Branch Transaction CSVs"] --> B["src/ingestion<br/>Read + Validate"]

    B --> C["data/validated/<br/>valid_transactions.csv"]
    B --> D["data/validated/<br/>invalid_transactions.csv"]

    B --> E["output/<br/>DQ + Summaries + Logs"]

    C --> F["Initial Operational Load<br/>src/operational"]

    R["data/reference/<br/>customers.csv<br/>branches.csv<br/>accounts.csv"] --> F

    F --> G[("database/banking.db<br/>Operational Database")]

    H["data/daily/<br/>Daily Transaction CSVs"] --> I["src/operational/<br/>incremental_load.py"]

    I -->|"INSERT new rows<br/>UPSERT corrections<br/>rerun-safe"| G

    G --> J["src/analytics/<br/>Analytical Transformation"]

    J --> K[("database/analytics.db<br/>Analytical Database")]

    K --> L["dim_customer"]
    K --> M["dim_account"]
    K --> N["dim_branch"]
    K --> O["dim_date"]
    K --> P["fact_transaction"]

    K --> Q["sql/analytical_queries.sql<br/>7 Analytical Queries"]

    Q --> S["Query Results + Interpretations"]

    T["tests/"] --> U["pytest<br/>Week 5 Tests"]

    U -.-> G
    U -.-> K
```

## Data Flow

1. **Raw branch files** are read by the ingestion layer.
2. The ingestion layer validates the records and separates valid and invalid transactions.
3. Trusted transactions and reference data are loaded into `banking.db`.
4. New daily transaction files are processed separately through the incremental loader.
5. New transaction IDs are inserted, while later corrections for existing transaction IDs are applied using UPSERT.
6. The trusted operational data in `banking.db` is used as the source for the analytical transformation.
7. The analytical transformation creates `analytics.db` containing dimensions and the `fact_transaction` table.
8. The analytical queries operate on `analytics.db` rather than directly on the raw CSV files.
9. Pytest verifies incremental processing and analytical-layer integrity.
