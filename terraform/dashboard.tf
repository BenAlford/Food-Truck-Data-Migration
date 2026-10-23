resource "aws_cloudwatch_log_group" "truck_service" {
  name              = "/ecs/${var.name_prefix}-service"
  retention_in_days = var.log_retention_days
}

resource "aws_iam_role" "ecs_task_role" {
  name               = "${var.name_prefix}-ecs-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

data "aws_iam_policy_document" "ecs_task_athena" {
  statement {
    actions = [
      "athena:StartQueryExecution",
      "athena:GetQueryExecution",
      "athena:GetQueryResults",
      "athena:StopQueryExecution",
      "athena:GetWorkGroup",
    ]
    resources = ["arn:aws:athena:${var.aws_region}:${local.account_id}:workgroup/${var.athena_workgroup}"]
  }

  statement {
    actions = ["glue:GetDatabase", "glue:GetTable", "glue:GetTables", "glue:GetPartition", "glue:GetPartitions", "glue:CreateTable", "glue:DeleteTable"]
    resources = [
      "arn:aws:glue:${var.aws_region}:${local.account_id}:catalog",
      aws_glue_catalog_database.truck_db.arn,
      "arn:aws:glue:${var.aws_region}:${local.account_id}:table/${aws_glue_catalog_database.truck_db.name}/*",
    ]
  }

  statement {
    actions   = ["s3:GetObject", "s3:ListBucket"]
    resources = [aws_s3_bucket.truck_data.arn, "${aws_s3_bucket.truck_data.arn}/*"]
  }

  # Athena writes query results here
  statement {
    actions = [
      "s3:PutObject",
      "s3:GetBucketLocation",
      "s3:AbortMultipartUpload",
      "s3:ListMultipartUploadParts",
    ]
    resources = [aws_s3_bucket.truck_data.arn, "${aws_s3_bucket.truck_data.arn}/${var.athena_results_prefix}/*"]
  }
}

resource "aws_iam_role_policy" "ecs_task_athena" {
  name   = "${var.name_prefix}-ecs-task-athena"
  role   = aws_iam_role.ecs_task_role.id
  policy = data.aws_iam_policy_document.ecs_task_athena.json
}

resource "aws_security_group" "truck_service" {
  name        = "${var.name_prefix}-service-sg"
  description = "Security group for the truck ECS service"
  vpc_id      = data.aws_vpc.selected.id

  ingress {
    from_port   = var.container_port
    to_port     = var.container_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_ecs_task_definition" "truck" {
  family                   = "${var.name_prefix}-task"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "truck"
      image     = var.dashboard_image_uri
      essential = true
      portMappings = [
        {
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "GLUE_DATABASE"
          value = aws_glue_catalog_database.truck_db.name
        },
        {
          name  = "REGION_NAME"
          value = var.aws_region
        },
        {
          name  = "ATHENA_OUTPUT_LOCATION"
          value = "s3://${aws_s3_bucket.truck_data.bucket}/${var.athena_results_prefix}/"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.truck_service.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "truck" {
  name            = "${var.name_prefix}-service"
  cluster         = data.aws_ecs_cluster.existing.arn
  task_definition = aws_ecs_task_definition.truck.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.selected.ids
    security_groups  = [aws_security_group.truck_service.id]
    assign_public_ip = true # needed to pull from ECR in the VPC
  }
}
