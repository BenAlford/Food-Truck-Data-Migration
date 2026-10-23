# Truck Report Generation Lambda Function

This Lambda function generates HTML reports for truck performance, revenue, transactions, and payment methods. It is designed to be triggered daily and emailed to the relevant stakeholders.

## Prerequisites

- Ensure you've cloned the repository and navigate to the html-report directory.
   ```bash
   git clone https://github.com/BenAlford/Coursework-Advanced-Data-Week-3
   cd Coursework-Advanced-Data-Week-3/html-report
   ```

## Deploying as a Lambda Function

To deploy the HTML report generation as a Lambda function, follow the steps below:

1. Create an ECR repository in your AWS account to store the Docker image (if not already created). This can be done via the AWS Management Console (https://{region}.console.aws.amazon.com/ecr/private-registry/repositories?region={region}) or using the AWS CLI.
2. Build the Docker image.
   ```bash
   docker build -t daily-report:{version} .
   ```
3. Log in to aws using Docker:
   ```bash
   aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {aws_account_id}.dkr.ecr.{region}.amazonaws.com
   ```
4. Tag the Docker image for your ECR repository.
   ```bash
   docker tag daily-report:{version} {aws_account_id}.dkr.ecr.{region}.amazonaws.com/{repository_name}
   ```
5. Push the Docker image to your container registry:
   ```bash
   docker push {aws_account_id}.dkr.ecr.{region}.amazonaws.com/{repository_name}
   ```
6. Get the image URI for use in the terraform setup. This URI will be in the format:
   ```
   {aws_account_id}.dkr.ecr.{region}.amazonaws.com/{repository_name}:{version}
   ```
7. When configuring the Lambda function in Terraform, use this image URI to specify the container image for the Lambda function.

## Local Testing

To test the HTML report generation locally, you can run either the Docker container with the necessary environment variables or directly execute the Python script with the required parameters. Both require a `.env` file containing these values:

```env
ACCESS_KEY={access_key}
SECRET_ACCESS_KEY={secret_key}
LOCAL_TEST=true
GLUE_DATABASE={glue_database}
ATHENA_OUTPUT_LOCATION=s3://{athena_output_location}/
REGION={region}
```

To test without Docker:

- Create a venv
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
- Install the required dependencies.
  ```bash
  pip install -r requirements.txt
  ```
- Run the Python script with the necessary environment variables.
  ```bash
  python3 report.py
  ```

To test with docker:

- Run the docker image:
  ```bash
  docker run --env-file .env --platform linux/amd64 -p 9000:8080 daily-report:{version}
  ```
- Run this command in a new terminal:
  ```bash
  curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{"date": "YYYY-MM-DD"}'
  ```