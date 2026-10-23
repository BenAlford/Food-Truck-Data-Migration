# Pipeline

This folder should contain all code and resources required for the ETL pipeline that takes the latest data from a MySQL database, processes it and loads it into S3. This pipeline is designed to be run as an ECS task, but it can also be tested and run locally using the instructions below.

## Overview
   
This pipeline extracts the latest data from a MySQL database, transforms it as needed, and loads it into an S3 bucket for further use. To do this, it follows these steps:

- Get the last index processed from the MySQL database. This is stored in the same S3 bucket as the data will be when it is uploaded.
- Extract the new data from the MySQL database starting from the last index.
- Transform the data by completing steps such as converting pence to pounds, validating datetimes, and dropping NULL records.
- Load the transformed data into the S3 bucket in parquet format. This project partitions the data by date to optimize query performance and storage efficiency.

## Prerequisites

- Ensure you've cloned the repository and navigate to the pipeline directory.
   ```bash
   git clone https://github.com/BenAlford/Coursework-Advanced-Data-Week-3
   cd Coursework-Advanced-Data-Week-3/pipeline
   ```

## Deploying as an ECS Task

To deploy the pipeline as an ECS task, follow the steps below:

1. Create an ECR repository in your AWS account to store the Docker image (if not already created). This can be done via the AWS Management Console (https://{region}.console.aws.amazon.com/ecr/private-registry/repositories?region={region}) or using the AWS CLI.
2. Build the Docker image.
   ```bash
   docker build -t truck-pipeline:{version} .
   ```
3. Log in to aws using Docker:
   ```bash
   aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {aws_account_id}.dkr.ecr.{region}.amazonaws.com
   ```
4. Tag the Docker image for your ECR repository.
   ```bash
   docker tag truck-pipeline:{version} {aws_account_id}.dkr.ecr.{region}.amazonaws.com/{repository_name}
   ```
5. Push the Docker image to your container registry:
   ```bash
   docker push {aws_account_id}.dkr.ecr.{region}.amazonaws.com/{repository_name}
   ```
6. Get the image URI for use in the terraform setup. This URI will be in the format:
   ```
   {aws_account_id}.dkr.ecr.{region}.amazonaws.com/{repository_name}:{version}
   ```

When configuring the ECS task in Terraform, use this image URI to specify the container image for the task definition.

## Local Testing

In order to test the pipeline locally, you need to follow the steps below:

1. Ensure you have followed the AWS Terraform Setup instructions in /terraform/README.md to  create the necessary infrastructure.
2. Have the necessary AWS credentials configured in the AWS CLI. This can be done by running `aws configure` and providing your AWS access key, secret access key, and default region.
3. Create a `.env` file in this directory with the following content:
   ```env
   BUCKET="your-bucket-name"

   DB_HOST="your-db-host"
   DB_USER="your-db-username"
   DB_PASSWORD="your-db-password"
   DB_NAME="your-db-name"
   ```
4. Create a virtual environment.
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
5. Install the required Python packages.
   ```bash
   pip install -r requirements.txt
   ```
6. Run the ETL pipeline.
   ```bash
   python pipeline.py
   ```

To verify that the ETL pipeline ran successfully, check the S3 bucket specified in your `.env` file for the processed data files.

The bucket name specified in your `.env` should match the name of the S3 bucket created by the Terraform configuration.

## Options

In addition to the pipeline, you can reset the s3 bucket by running `reset_bucket.py`. This will clear all the data in the specified S3 bucket, allowing you to start fresh.