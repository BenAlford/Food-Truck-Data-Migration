resource "aws_cloudwatch_log_group" "s3_task" {
  name              = "/ecs/${var.name_prefix}-s3-task"
  retention_in_days = var.log_retention_days
}

# Egress-only: the batch task needs to reach ECR, S3 and the database, but accepts no inbound traffic
resource "aws_security_group" "s3_task" {
  name        = "${var.name_prefix}-s3-task-sg"
  description = "Security group for the scheduled pipeline task (egress only)"
  vpc_id      = data.aws_vpc.selected.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Task role: what the running container may do
resource "aws_iam_role" "s3_task_role" {
  name               = "${var.name_prefix}-s3-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

data "aws_iam_policy_document" "s3_task_access" {
  statement {
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [aws_s3_bucket.truck_data.arn]
  }

  statement {
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.truck_data.arn}/*"]
  }
}

resource "aws_iam_role_policy" "s3_task_access" {
  name   = "${var.name_prefix}-s3-task-access"
  role   = aws_iam_role.s3_task_role.id
  policy = data.aws_iam_policy_document.s3_task_access.json
}

# Execution role: used by ECS to pull the image, write logs and inject the DB secret.
# Separate from the dashboard's execution role so only this task can read the secret.
resource "aws_iam_role" "s3_task_execution_role" {
  name               = "${var.name_prefix}-s3-task-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

resource "aws_iam_role_policy_attachment" "s3_task_execution" {
  role       = aws_iam_role.s3_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "s3_task_db_secret" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [data.aws_secretsmanager_secret.db.arn]
  }
}

resource "aws_iam_role_policy" "s3_task_db_secret" {
  name   = "${var.name_prefix}-s3-task-db-secret"
  role   = aws_iam_role.s3_task_execution_role.id
  policy = data.aws_iam_policy_document.s3_task_db_secret.json
}

resource "aws_ecs_task_definition" "s3_task" {
  family                   = "${var.name_prefix}-s3-task"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.s3_task_execution_role.arn
  task_role_arn            = aws_iam_role.s3_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "s3-task"
      image     = var.pipeline_image_uri
      essential = true
      environment = [
        { name = "BUCKET", value = aws_s3_bucket.truck_data.bucket },
        { name = "DB_HOST", value = var.db_host },
        { name = "DB_NAME", value = var.db_name },
      ]
      secrets = [
        { name = "DB_USER", valueFrom = "${data.aws_secretsmanager_secret.db.arn}:username::" },
        { name = "DB_PASSWORD", valueFrom = "${data.aws_secretsmanager_secret.db.arn}:password::" },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.s3_task.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}
