data "aws_iam_policy_document" "report_scheduler" {
  statement {
    actions   = ["states:StartExecution"]
    resources = [aws_sfn_state_machine.report.arn]
  }
}

resource "aws_iam_role" "report_scheduler" {
  name               = "${var.name_prefix}-report-scheduler-role"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
}

resource "aws_iam_role_policy" "report_scheduler" {
  name   = "${var.name_prefix}-report-scheduler"
  role   = aws_iam_role.report_scheduler.id
  policy = data.aws_iam_policy_document.report_scheduler.json
}

resource "aws_scheduler_schedule" "report" {
  name                         = "${var.name_prefix}-report-schedule"
  description                  = "Emails the previous day's transaction report"
  schedule_expression          = var.report_schedule_expression
  schedule_expression_timezone = var.report_schedule_timezone
  state                        = var.report_schedule_enabled ? "ENABLED" : "DISABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_sfn_state_machine.report.arn
    role_arn = aws_iam_role.report_scheduler.arn

    # No date: the state machine defaults to yesterday
    input = jsonencode({})
  }
}
