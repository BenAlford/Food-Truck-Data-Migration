# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------

variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "eu-west-2"
}

variable "name_prefix" {
  description = "Prefix for named resources (IAM roles, crawler, ECS service, etc.)"
  type        = string
}

variable "vpc_name" {
  description = "Name tag of the existing VPC to deploy into (set in terraform.tfvars)"
  type        = string
}

variable "public_subnet_names" {
  description = "Name tags of the public subnets (in the VPC) that ECS tasks run in. They must route to an internet gateway (set in terraform.tfvars)"
  type        = list(string)

  validation {
    condition     = length(var.public_subnet_names) > 0
    error_message = "At least one public subnet name must be provided."
  }
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

variable "ecs_cluster_name" {
  description = "Name of the existing ECS cluster to run tasks in"
  type        = string
  default     = "c26-ecs-cluster"
}

# ---------------------------------------------------------------------------
# Storage and Glue
# ---------------------------------------------------------------------------

variable "bucket_name" {
  description = "Name of the S3 bucket holding the truck data"
  type        = string
  default     = "c26-ben-truck-data"
}

variable "glue_database_name" {
  description = "Name of the Glue catalog database"
  type        = string
  default     = "c26_ben_truck_db"
}

variable "crawler_data_prefixes" {
  description = "S3 key prefixes (folders) in the bucket that the Glue crawler scans"
  type        = list(string)
  default     = ["transactions", "truck", "payment_method"]
}

# ---------------------------------------------------------------------------
# Dashboard service
# ---------------------------------------------------------------------------

variable "dashboard_image_uri" {
  description = "Full ECR image URI (including tag) for the dashboard container (set in terraform.tfvars)"
  type        = string
}

variable "container_port" {
  description = "Port the dashboard container listens on (Streamlit default)"
  type        = number
  default     = 8501
}

variable "task_cpu" {
  description = "Fargate task CPU units (used by both the dashboard and pipeline tasks)"
  type        = number
  default     = 256
}

variable "task_memory" {
  description = "Fargate task memory in MiB (used by both the dashboard and pipeline tasks)"
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Number of dashboard ECS tasks to run"
  type        = number
  default     = 1
}

variable "athena_workgroup" {
  description = "Athena workgroup the dashboard may run queries in"
  type        = string
  default     = "primary"
}

variable "athena_results_prefix" {
  description = "S3 key prefix in the bucket where Athena writes query results"
  type        = string
  default     = "athena-results"
}

# ---------------------------------------------------------------------------
# Pipeline task and schedule
# ---------------------------------------------------------------------------

variable "pipeline_image_uri" {
  description = "Full ECR image URI (including tag) for the pipeline task (set in terraform.tfvars)"
  type        = string
}

variable "report_image_uri" {
  description = "Full ECR image URI (including tag) for the report Lambda container (set in terraform.tfvars)"
  type        = string
}

variable "db_host" {
  description = "Database host passed to the pipeline task as DB_HOST (set in terraform.tfvars)"
  type        = string
}

variable "db_name" {
  description = "Database name passed to the pipeline task as DB_NAME (set in terraform.tfvars)"
  type        = string
}

variable "db_secret_name" {
  description = "Name of the existing Secrets Manager secret (JSON with username and password keys) (set in terraform.tfvars)"
  type        = string
}

variable "s3_task_schedule_expression" {
  description = "EventBridge Scheduler expression for the pipeline task, e.g. rate(1 hour) or cron(0 * * * ? *)"
  type        = string
  default     = "cron(10 9-18/3 * * ? *)"
}

variable "s3_task_schedule_timezone" {
  description = "IANA timezone the schedule expression is evaluated in"
  type        = string
  default     = "Europe/London"
}

variable "s3_task_schedule_enabled" {
  description = "Whether the pipeline task schedule is enabled"
  type        = bool
  default     = true
}

variable "crawler_schedule" {
  description = "Glue crawler cron schedule. Glue evaluates it in UTC, so the default (08:20-17:20 UTC every 3 hours) is 09:20-18:20 UK time during BST and 08:20-17:20 during GMT"
  type        = string
  default     = "cron(20 8-17/3 * * ? *)"
}

# ---------------------------------------------------------------------------
# Report email (Step Functions + SES)
# ---------------------------------------------------------------------------

variable "report_email_recipient" {
  description = "Existing verified SES identity the daily report is sent to (set in terraform.tfvars)"
  type        = string
}

variable "report_email_sender" {
  description = "Existing verified SES identity the daily report is sent from (set in terraform.tfvars)"
  type        = string
}

variable "report_schedule_expression" {
  description = "EventBridge Scheduler expression for the report email, e.g. cron(30 9 * * ? *) for 09:30 daily"
  type        = string
  default     = "cron(30 9 * * ? *)"
}

variable "report_schedule_timezone" {
  description = "IANA timezone the report schedule expression is evaluated in"
  type        = string
  default     = "Europe/London"
}

variable "report_schedule_enabled" {
  description = "Whether the report email schedule is enabled"
  type        = bool
  default     = true
}
