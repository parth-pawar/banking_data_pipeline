import pandas as pd

from config.config import (
    ALLOWED_TRANSACTION_TYPES,
    REQUIRED_CURRENCY,
)

# validate_amount is a function that checks if the amount is a valid number greater than 0.
def validate_amount(amount):
    try:
        numeric_amount = float(amount)
    except (ValueError, TypeError):
        return False

    return numeric_amount > 0


# validate_date is a function that checks if the date is in the correct format (YYYY-MM-DD) and is a valid date.
def validate_date(date):
    date_as_string = str(date)

    if not pd.Series([date_as_string]).str.match(
        r"^\d{4}-\d{2}-\d{2}$"
    ).iloc[0]:
        return False

    parsed_date = pd.to_datetime(
        date_as_string,
        format="%Y-%m-%d",
        errors="coerce"
    )

    return not pd.isna(parsed_date)


# validate_transaction_type is a function that checks if the transaction type is one of the allowed types.
def validate_transaction_type(transaction_type):
    return transaction_type in ALLOWED_TRANSACTION_TYPES


# validate_currency is a function that checks if the currency is the required currency (USD).
def validate_currency(currency):
    return currency == REQUIRED_CURRENCY





# validate_transactions is a function that validates the transactions in the given DataFrame and adds an "error_reason" column to indicate any validation errors.
def validate_transactions(data):
    data["error_reason"] = ""

    mask = data["transaction_id"].isna()
    data.loc[mask, "error_reason"] += "transaction_id is missing; "

    mask = data["account_id"].isna()
    data.loc[mask, "error_reason"] += "account_id is missing; "

    mask = ~data["transaction_type"].apply(validate_transaction_type)
    data.loc[mask, "error_reason"] += "invalid transaction_type; "

    data["amount"] = pd.to_numeric(
    data["amount"],
    errors="coerce"
    )

    mask = data["amount"].isna()
    data.loc[mask, "error_reason"] += "amount is missing or not numeric; "

    mask = data["amount"].notna() & ~data["amount"].apply(validate_amount)
    data.loc[mask, "error_reason"] += "amount must be greater than 0; "

    mask = ~data["currency"].apply(validate_currency)
    data.loc[mask, "error_reason"] += "currency must be USD; "

    mask = ~data["transaction_date"].apply(validate_date)
    data.loc[mask, "error_reason"] += "invalid transaction_date; "

    duplicate_ids = (
    data["transaction_id"].notna()
    & data["transaction_id"].duplicated(keep=False)
    )

    data.loc[duplicate_ids, "error_reason"] += (
        "duplicate transaction_id; "
    )

    return data