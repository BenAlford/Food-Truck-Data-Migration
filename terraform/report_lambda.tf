resource "aws_cloudwatch_log_group" "report_lambda" {
  name              = "/aws/lambda/${var.name_prefix}-report"
  retention_in_days = var.log_retention_days
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "report_lambda" {
  name               = "${var.name_prefix}-report-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "report_lambda_logs" {
  role       = aws_iam_role.report_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Same Athena/Glue/S3 access as the dashboard task
resource "aws_iam_role_policy" "report_lambda_athena" {
  name   = "${var.name_prefix}-report-lambda-athena"
  role   = aws_iam_role.report_lambda.id
  policy = data.aws_iam_policy_document.ecs_task_athena.json
}

resource "aws_lambda_function" "report" {
  function_name = "${var.name_prefix}-report"
  role          = aws_iam_role.report_lambda.arn
  package_type  = "Image"
  image_uri     = var.report_image_uri
  timeout       = 90
  memory_size   = 256

  environment {
    variables = {
      GLUE_DATABASE          = aws_glue_catalog_database.truck_db.name
      ATHENA_OUTPUT_LOCATION = "s3://${aws_s3_bucket.truck_data.bucket}/${var.athena_results_prefix}/"
      REGION                 = var.aws_region
    }
  }

  depends_on = [aws_cloudwatch_log_group.report_lambda]
}

# Public URL: open it with ?date=YYYY-MM-DD. Switch authorization_type to AWS_IAM to restrict access.
resource "aws_lambda_function_url" "report" {
  function_name      = aws_lambda_function.report.function_name
  authorization_type = "NONE"
}

resource "aws_lambda_permission" "report_url_public" {
  statement_id           = "AllowPublicFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.report.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_permission" "report_url_invoke" {
  statement_id  = "AllowPublicFunctionUrlInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.report.function_name
  principal     = "*"
}
