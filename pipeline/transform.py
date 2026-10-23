import logging
from extract import extract_all_transaction_data
import pandas as pd

logger = logging.getLogger(__name__)


def clean_transaction_data(df: pd.DataFrame, truck_df: pd.DataFrame, payment_df: pd.DataFrame) -> pd.DataFrame:
    """Returns a copy of the transactions without invalid rows.

    Drops rows with missing or non-numeric/negative totals, unknown payment
    methods or trucks, and timestamps more than 5 minutes in the future.
    """

    df = df.copy()
    rows_before = len(df)

    df["total"] = pd.to_numeric(df["total"], errors="coerce")

    df["at"] = pd.to_datetime(df["at"], errors="coerce")

    df.dropna(inplace=True)

    df = df[df["total"] >= 0]

    # Convert from pence to pounds
    df["total"] = df["total"].apply(lambda x: float(x) / 100)

    df = df[df["payment_method_id"].isin(payment_df["payment_method_id"])]

    df = df[df["truck_id"].isin(truck_df["truck_id"])]

    # Checks transactions are not in the future
    df = df[df["at"] <= pd.Timestamp.now() + pd.Timedelta(minutes=5)]

    logger.info("Cleaned transactions: kept %d of %d rows (%d dropped)",
                len(df), rows_before, rows_before - len(df))

    return df


def split_by_date(df: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    """Yields (date, dataframe) pairs, one per day, with dates as 'YYYY-MM-DD'."""

    dates = df["at"].dt.strftime("%Y-%m-%d")

    return ((date, group.copy()) for date, group in df.groupby(dates))


def transform(df: pd.DataFrame, truck_df: pd.DataFrame, payment_method_df: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    """Cleans the transactions and splits them into per-day dataframes."""
    df = df.copy()
    df = clean_transaction_data(df, truck_df, payment_method_df)
    # df_by_date = split_by_date(df)
    # return df_by_date
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    df = extract_all_transaction_data()
    df_by_date = transform(df, truck_df=pd.DataFrame(),
                           payment_method_df=pd.DataFrame())
