data "aws_iam_policy_document" "scheduler_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
  }
}

resource "aws_iam_role" "s3_task_scheduler" {
  name               = "${var.name_prefix}-s3-task-scheduler-role"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
}

data "aws_iam_policy_document" "s3_task_scheduler" {
  statement {
    actions   = ["ecs:RunTask"]
    resources = ["arn:aws:ecs:${var.aws_region}:${local.account_id}:task-definition/${aws_ecs_task_definition.s3_task.family}:*"]

    condition {
      test     = "ArnEquals"
      variable = "ecs:cluster"
      values   = [data.aws_ecs_cluster.existing.arn]
    }
  }

  statement {
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.s3_task_execution_role.arn, aws_iam_role.s3_task_role.arn]

    condition {
      test     = "StringLike"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "s3_task_scheduler" {
  name   = "${var.name_prefix}-s3-task-scheduler"
  role   = aws_iam_role.s3_task_scheduler.id
  policy = data.aws_iam_policy_document.s3_task_scheduler.json
}

resource "aws_scheduler_schedule" "s3_task" {
  name                         = "${var.name_prefix}-s3-task-schedule"
  description                  = "Runs the ${aws_ecs_task_definition.s3_task.family} Fargate task on a schedule"
  schedule_expression          = var.s3_task_schedule_expression
  schedule_expression_timezone = var.s3_task_schedule_timezone
  state                        = var.s3_task_schedule_enabled ? "ENABLED" : "DISABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = data.aws_ecs_cluster.existing.arn
    role_arn = aws_iam_role.s3_task_scheduler.arn

    ecs_parameters {
      # Unversioned ARN so each run uses the latest active task definition revision
      task_definition_arn = replace(aws_ecs_task_definition.s3_task.arn, "/:[0-9]+$/", "")
      launch_type         = "FARGATE"
      task_count          = 1

      network_configuration {
        subnets          = data.aws_subnets.selected.ids
        security_groups  = [aws_security_group.s3_task.id]
        assign_public_ip = true
      }
    }

    retry_policy {
      maximum_retry_attempts = 0
    }
  }
}
