# Food Truck Data Migration

This project is focused on migrating food truck data from a MySQL database stored in an RDS to a data lake system using S3, Glue, and Athena. New data is added to the MySQL database every 3 hours. When the pipeline runs, it extracts the new data and loads it into the data lake. 

## Overview
When fully setup, this project contains:

- A pipeline script that runs every 3 hours to extract new data from the MySQL database and load it into the S3.
- A dashboard that visualizes the food truck data stored in the data lake using Athena queries.
- A workflow to generate and email a daily report of the previous day's food truck data.

Further details on the setup and usage of this project can be found in the respective documentation for each component.

## Technologies

This project is hosted on AWS and leverages these AWS services:
- S3 to store processed data files
- Glue to catalog and manage the data in the data lake
- Glue Crawler to automatically discover and catalog the data in the data lake
- Athena to query the data in the data lake
- RDS to host the MySQL database containing the food truck data
- ECS to run the pipeline and dashboard containerized applications
- Lambda to generate HTML reports for the food truck data
- Step Functions to orchestrate the daily report generation workflow
- SES to send the daily report emails
- Secrets Manager to store the database credentials securely
- CloudWatch to monitor and log the activities of the AWS resources

The scripts in this repository were built in Python 3.9, and make use of these libraries:
- pandas for data processing
- altair for data visualization
- streamlit for building the dashboard
- boto3 and awswrangler for interacting with AWS services

## MySQL Database Schema
The project assumes the MySQL database already exists and contains these tables in a STAR schema:

`FACT_Transaction`:
- transaction_id (primary key) BIGINT
- truck_id (foreign key to DIM_Truck) SMALLINT
- payment_method_id (foreign key to DIM_Payment_Method) SMALLINT
- total (amount of the transaction in pence) FLOAT
- at (timestamp of the transaction) TIMESTAMP

`DIM_Truck`:
- truck_id (primary key) SMALLINT
- truck_name VARCHAR(255)
- truck_description TEXT  
- has_card_reader BOOLEAN
- fsa_rating (Food Standards Agency rating of the truck) SMALLINT

`DIM_Payment_Method`:
- payment_method_id (primary key) SMALLINT
- payment_method VARCHAR(10)

## Prerequisites

Before setting up and running this project, ensure you have the following:

- An AWS account with the necessary permissions to create and manage S3 buckets, Glue crawlers, Athena databases, RDS instances, ECS services, Lambda functions, and Step Functions.
- AWS CLI configured with the appropriate credentials.
- Docker installed and configured for building and pushing container images.
- Python 3.9 installed.

Different sections may have additional prerequisites specific to their setup and usage.

## Project Structure
The project is organized into the following main directories and files:

- `pipeline/`: Contains the ETL pipeline code and resources for extracting data from MySQL and loading it into S3.
- `html-report/`: Contains the code for the lambda function that generates HTML reports of the food truck data.
- `dashboard/`: Contains the code and resources for the streamlit dashboard that visualizes the food truck data using Athena queries.
- `terraform/`: Contains the Terraform configuration for setting up the necessary AWS infrastructure.

To find out more about each component, refer to the respective README files within each directory.