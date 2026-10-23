# AWS Terraform Setup

This project contains the Terraform configuration files to set up the necessary AWS infrastructure for the ETL pipeline.

## Overview

The infrastructure setup consists of:

- An S3 bucket to store processed data files.
- An AWS Glue crawler to catalog the data every 3 hours between 9:10-6:10.
- An AWS Glue database.
- An ECS task to run the pipeline script every 3 hours between 9:20-6:20 using an EventBridge schedule.
- An ECS service to run the dashboard using the container image built for the dashboard application.
- A Lambda function to generate HTML reports for truck performance, revenue, transactions, and payment methods. This lambda function is used in a Step Function state machine to orchestrate daily email reports.
- A Step Function state machine to orchestrate daily email reports at 9:30.
- EventBridge schedules to trigger the ECS task and the email state machine at the specified intervals.
- The necessary IAM roles and policies for all these tasks.

## Prerequisites

1. Ensure you have configured your AWS CLI with the necessary credentials.
2. Make sure you have built and pushed the Docker images for the pipeline, dashboard, and report lambda applications to your container registry.
3. Create an AWS secret in Secrets Manager to store the database login credentials. This secret must contain fields `username` and `password`.
4. Create the necessary email identities in AWS SES for the report sender and recipient. They must both be verified in SES.
5. The VPC, subnets and ECS cluster must already exist in your AWS account as this Terraform configuration assumes their presence.

## Setup

To set up the AWS infrastructure using Terraform, follow these steps:

1. Navigate to the Terraform directory.
   ```bash
   cd terraform
   ```
2. Initialize the Terraform workspace.
   ```bash
   terraform init
   ```
3. Create a terraform.tfvars file with these values:
   ```hcl
    vpc_name               = "VPC-NAME"
    public_subnet_names    = ["PUBLIC-SUBNET-1", "PUBLIC-SUBNET-2", "PUBLIC-SUBNET-3"]
    name_prefix            = "your-resource-prefix" # Prefix for named resources (IAM roles, crawler, ECS service, etc.)
    db_host                = "mysql-hostname"
    db_name                = "db_name"
    db_secret_name         = "db_secrets_name" # The name of the secret in AWS Secrets Manager containing the database credentials
    dashboard_image_uri    = "{account_id}.dkr.ecr.eu-west-2.amazonaws.com/{dashboard_image_name}:latest"
    pipeline_image_uri     = "{account_id}.dkr.ecr.eu-west-2.amazonaws.com/{pipeline_image_name}:latest"
    report_image_uri       = "{account_id}.dkr.ecr.eu-west-2.amazonaws.com/{report_image_name}:latest"
    report_email_recipient = "receiver@example.com"
    report_email_sender    = "sender@example.com"
   ```
4. Apply the Terraform configuration.
   ```bash
   terraform apply
   ```

## Outputs

The Terraform outputs include:
- The S3 bucket name for processed data files.
- The AWS Glue database name.
- The ECS service name for the dashboard.
- The ECS task definition family for the pipeline.
- The Lambda function URL for report generation.
- The Step Function state machine ARN for orchestrating daily email reports.
- The pipeline schedule name for the EventBridge schedule triggering the ECS task.

## Cleanup

To clean up the AWS resources created by this Terraform configuration, run:

```bash
terraform destroy
```

The S3 bucket must be cleared before running `terraform destroy` to avoid errors related to non-empty buckets. To do this, run `reset_bucket.py` in the pipeline folder or manually delete the objects in the bucket.