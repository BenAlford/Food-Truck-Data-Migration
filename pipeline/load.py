import logging
from os import environ
from dotenv import load_dotenv
import awswrangler as wr
import boto3
import pandas as pd

logger = logging.getLogger(__name__)

load_dotenv()

session = boto3.Session(
)


def upload_transaction_data(df: pd.DataFrame, bucket: str) -> None:
    """Uploads a batch of cleaned transactions to S3, partitioned by date."""

    path = f"s3://{bucket}/transactions/"
    logger.info("Uploading %d transactions to %s", len(df), path)

    wr.s3.to_parquet(
        df=df.assign(date=df["at"].dt.strftime("%Y-%m-%d")),
        path=path,
        index=False,
        dataset=True,
        partition_cols=["date"],
        mode="append",
        filename_prefix="FACT_Transaction_",
        boto3_session=session
    )


def upload_dimension_data(truck_df: pd.DataFrame, payment_method_df: pd.DataFrame,
                          bucket: str) -> None:
    """Uploads the truck and payment method dimension tables to S3 as parquet."""

    truck_path = f"s3://{bucket}/truck/DIM_Truck.parquet"
    logger.info("Uploading %d trucks to %s", len(truck_df), truck_path)
    wr.s3.to_parquet(
        df=truck_df,
        path=truck_path,
        index=False,
        boto3_session=session
    )

    payment_path = f"s3://{bucket}/payment_method/DIM_Payment_Method.parquet"
    logger.info("Uploading %d payment methods to %s",
                len(payment_method_df), payment_path)
    wr.s3.to_parquet(
        df=payment_method_df,
        path=payment_path,
        index=False,
        boto3_session=session
    )


def write_last_transaction_id(last_id: int):
    """Writes the new last transaction ID to an s3 bucket."""
    path = f"s3://{environ.get('BUCKET')}/last_transaction_id.csv"
    logger.info("Writing last transaction ID %d to %s", last_id, path)
    wr.s3.to_csv(
        df=pd.DataFrame({"last_transaction_id": [last_id]}),
        path=path,
        index=False,
        boto3_session=session
    )


if __name__ == "__main__":
    pass
    # upload_transaction_data(pd.read_csv("historical_data.csv"))
