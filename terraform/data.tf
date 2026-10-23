data "aws_caller_identity" "current" {}

data "aws_vpc" "selected" {
  filter {
    name   = "tag:Name"
    values = [var.vpc_name]
  }
}

data "aws_subnets" "selected" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.selected.id]
  }

  # Tasks use assign_public_ip, so they must run in subnets routed to an internet gateway
  filter {
    name   = "tag:Name"
    values = var.public_subnet_names
  }
}

data "aws_ecs_cluster" "existing" {
  cluster_name = var.ecs_cluster_name
}

data "aws_secretsmanager_secret" "db" {
  name = var.db_secret_name
}
