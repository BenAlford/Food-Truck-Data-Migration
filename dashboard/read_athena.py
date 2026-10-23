import awswrangler as wr
import boto3
from dotenv import load_dotenv
from os import environ

load_dotenv()

session = boto3.Session(
    region_name=environ.get("REGION_NAME")
)


def _query(sql: str, glue_database: str):
    """Runs a query, writing results to ATHENA_OUTPUT_LOCATION if set."""
    return wr.athena.read_sql_query(sql, database=glue_database,
                                    s3_output=environ.get("ATHENA_OUTPUT_LOCATION"),
                                    boto3_session=session)


def fetch_truck_data(glue_database: str):
    """Fetches truck data from Athena."""
    return _query("SELECT * FROM truck", glue_database)


def fetch_payment_method_data(glue_database: str):
    """Fetches payment method data from Athena."""
    return _query("SELECT * FROM payment_method", glue_database)


def fetch_transaction_data(glue_database: str):
    """Fetches transaction data from Athena."""
    return _query("SELECT * FROM transactions", glue_database)


if __name__ == "__main__":
    glue_database = environ.get("GLUE_DATABASE")
    print(fetch_truck_data(glue_database))
    print(fetch_payment_method_data(glue_database))
    print(fetch_transaction_data(glue_database))
