import logging
import boto3
import pandas as pd
import pymysql
from os import environ
from dotenv import load_dotenv
import awswrangler as aw

logger = logging.getLogger(__name__)

load_dotenv()

# Connect to the database
conn = pymysql.connect(host=environ.get("DB_HOST"),
                       user=environ.get("DB_USER"),
                       password=environ.get("DB_PASSWORD"),
                       charset='utf8mb4',
                       database=environ.get("DB_NAME"),
                       cursorclass=pymysql.cursors.DictCursor)

session = boto3.Session()


def get_last_transaction_id() -> int:
    """Returns the last transaction ID to be processed. Returns -1 if no last transaction ID is found."""
    # Connects to s3 bucket
    try:
        df = aw.s3.read_csv(
            path=f"s3://{environ.get('BUCKET')}/last_transaction_id.csv",
            boto3_session=session
        )
        if df.empty:
            return -1
        return int(df.iloc[0]["last_transaction_id"])
    except aw.exceptions.NoFilesFound:
        logger.info(
            "No files found for last transaction ID in S3, setting it to -1")
        return -1


def extract_all_transaction_data() -> pd.DataFrame:
    """Returns all rows of FACT_Transaction as a dataframe."""
    logger.info("Extracting FACT_Transaction")
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM FACT_Transaction")
        result = cursor.fetchall()
        df = pd.DataFrame(result)
    logger.info("Extracted %d rows from FACT_Transaction", len(df))
    return df


def extract_last_batch_transaction_data(last_id: int) -> pd.DataFrame:
    """Returns the most recent batch of rows from FACT_Transaction as a dataframe, starting after the given last_id."""
    logger.info("Extracting last batch from FACT_Transaction")
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM FACT_Transaction WHERE transaction_id > %s", (last_id,))
        result = cursor.fetchall()
        df = pd.DataFrame(result)
    logger.info("Extracted %d rows from last batch of FACT_Transaction", len(df))
    return df


def extract_truck_data() -> pd.DataFrame:
    """Returns all rows of DIM_Truck as a dataframe."""
    logger.info("Extracting DIM_Truck")
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM DIM_Truck")
        result = cursor.fetchall()
        df = pd.DataFrame(result)
    logger.info("Extracted %d rows from DIM_Truck", len(df))
    return df


def extract_payment_method_data() -> pd.DataFrame:
    """Returns all rows of DIM_Payment_Method as a dataframe."""
    logger.info("Extracting DIM_Payment_Method")
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM DIM_Payment_Method")
        result = cursor.fetchall()
        df = pd.DataFrame(result)
    logger.info("Extracted %d rows from DIM_Payment_Method", len(df))
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    last_transaction_id = get_last_transaction_id()
    print(last_transaction_id)
    df = extract_last_batch_transaction_data(last_id=last_transaction_id)
