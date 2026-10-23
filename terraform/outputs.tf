output "bucket_name" {
  description = "S3 bucket holding the truck data"
  value       = aws_s3_bucket.truck_data.bucket
}

output "glue_database_name" {
  description = "Glue catalog database"
  value       = aws_glue_catalog_database.truck_db.name
}

output "dashboard_service_name" {
  description = "ECS service running the dashboard"
  value       = aws_ecs_service.truck.name
}

output "pipeline_task_definition_family" {
  description = "Task definition family for the scheduled pipeline task"
  value       = aws_ecs_task_definition.s3_task.family
}

output "report_lambda_url" {
  description = "URL of the HTML transaction report (append ?date=YYYY-MM-DD)"
  value       = aws_lambda_function_url.report.function_url
}

output "pipeline_schedule_name" {
  description = "EventBridge schedule that triggers the pipeline task"
  value       = aws_scheduler_schedule.s3_task.name
}

output "report_state_machine_arn" {
  description = "Step Functions state machine that generates and emails the report (input: {} or {\"date\": \"YYYY-MM-DD\"})"
  value       = aws_sfn_state_machine.report.arn
}
