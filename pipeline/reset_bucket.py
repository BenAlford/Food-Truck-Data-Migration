"""Deletes all objects in the specified S3 bucket."""

import awswrangler
from os import environ
from dotenv import load_dotenv

load_dotenv()
BUCKET = environ.get("BUCKET")


def reset_bucket(bucket_name: str):
    awswrangler.s3.delete_objects(f"s3://{bucket_name}")


if __name__ == "__main__":
    reset_bucket(BUCKET)
