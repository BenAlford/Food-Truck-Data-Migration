# Truck Data Dashboard

This dashboard provides an interactive interface to explore truck performance, revenue, transactions, and payment methods. It visualizes data on a per-truck basis, over time, and by payment method, helping users gain insights into operational and financial metrics. This has been designed to run as an ECS service, but it can also be tested and run locally using the instructions below. Data is sourced from the AWS Glue catalog via Athena queries.

## Prerequisites

- Ensure you've cloned the repository and navigate to the dashboard directory.
   ```bash
   git clone https://github.com/BenAlford/Coursework-Advanced-Data-Week-3
   cd Coursework-Advanced-Data-Week-3/dashboard
   ```
- Before running, ensure you have run 'pipeline.py' in the pipeline directory either locally or as an ECS task to populate the necessary data.
- Data is queried using Athena so ensure the glue crawler has run at least once.

## Deploying as an ECS Service

1. Create an ECR repository in your AWS account to store the Docker image (if not already created). This can be done via the AWS Management Console (https://{region}.console.aws.amazon.com/ecr/private-registry/repositories?region={region}) or using the AWS CLI.
2. Build the Docker image.
   ```bash
   docker build -t truck-dashboard:{version} .
   ```
3. Log in to aws using Docker:
   ```bash
   aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {aws_account_id}.dkr.ecr.{region}.amazonaws.com
   ```
4. Tag the Docker image for your ECR repository.
   ```bash
   docker tag truck-dashboard:{version} {aws_account_id}.dkr.ecr.{region}.amazonaws.com/{repository_name}
   ```
5. Push the Docker image to your container registry:
   ```bash
   docker push {aws_account_id}.dkr.ecr.{region}.amazonaws.com/{repository_name}
   ```
6. Get the image URI for use in the terraform setup. This URI will be in the format:
   ```
   {aws_account_id}.dkr.ecr.{region}.amazonaws.com/{repository_name}:{version}
   ```

7. When configuring the ECS service in Terraform, use this image URI to specify the container image for the task definition.

## Local Testing

In order to test the dashboard locally, you need to follow the steps below:

1. Ensure you have followed the AWS Terraform Setup instructions in /terraform/README.md to  create the necessary infrastructure.
2. Have the necessary AWS credentials configured in the AWS CLI. This can be done by running `aws configure` and providing your AWS access key, secret access key, and default region.
3. Create a .env in this directory with these values:
   ```env
   GLUE_DATABASE="your-glue-database-name"
   REGION_NAME="aws-region"
   ```
4. Activate a virtual environment.
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
5. Install the required Python packages.
   ```bash
   pip install -r requirements.txt
   ```
6. Run the dashboard.
   ```bash
   streamlit run dashboard.py
   ```
7. If not automatically opened, navigate to http://localhost:8501 in your web browser to access the dashboard.