import logging
from os import environ
from dotenv import load_dotenv
from extract import extract_last_batch_transaction_data, extract_truck_data, extract_payment_method_data, get_last_transaction_id
from transform import clean_transaction_data
from load import upload_transaction_data, upload_dimension_data, write_last_transaction_id


logger = logging.getLogger(__name__)

load_dotenv()
BUCKET = environ.get("BUCKET")


def run_pipeline() -> None:
    """Extracts data from the database, transforms it and loads it into S3."""
    logger.info("Pipeline started")

    try:
        last_id = get_last_transaction_id()
        transaction_df = extract_last_batch_transaction_data(last_id)

        if transaction_df.empty:
            logger.info("No new transactions found")
            return

        new_last_id = transaction_df["transaction_id"].max()

        truck_df = extract_truck_data()
        payment_method_df = extract_payment_method_data()

        cleaned_df = clean_transaction_data(
            transaction_df, truck_df, payment_method_df)

        upload_transaction_data(cleaned_df, BUCKET)

        upload_dimension_data(truck_df, payment_method_df, BUCKET)

        write_last_transaction_id(new_last_id)
    except Exception:
        logger.exception("Pipeline failed")
        raise

    logger.info("Pipeline finished")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        filename="pipeline.log", encoding="utf-8")
    run_pipeline()
