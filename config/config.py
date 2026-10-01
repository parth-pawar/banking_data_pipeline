# config.py is a configuration file that contains constants and settings used throughout the project.

REQUIRED_COLUMNS = {
    "transaction_id",
    "account_id",
    "transaction_date",
    "transaction_type",
    "amount",
    "currency",
}

ALLOWED_TRANSACTION_TYPES = {
    "CREDIT",
    "DEBIT",
}

REQUIRED_CURRENCY = "USD"
