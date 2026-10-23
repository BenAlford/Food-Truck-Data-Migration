resource "aws_glue_catalog_database" "truck_db" {
  name = var.glue_database_name
}

data "aws_iam_policy_document" "glue_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "crawler_role" {
  name               = "${var.name_prefix}-crawler-role"
  assume_role_policy = data.aws_iam_policy_document.glue_assume_role.json
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.crawler_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

data "aws_iam_policy_document" "crawler_s3_read" {
  statement {
    actions   = ["s3:GetObject", "s3:ListBucket"]
    resources = [aws_s3_bucket.truck_data.arn, "${aws_s3_bucket.truck_data.arn}/*"]
  }
}

resource "aws_iam_role_policy" "crawler_s3_read" {
  name   = "${var.name_prefix}-crawler-s3-read"
  role   = aws_iam_role.crawler_role.id
  policy = data.aws_iam_policy_document.crawler_s3_read.json
}

resource "aws_glue_crawler" "truck_crawler" {
  name          = "${var.name_prefix}-crawler"
  database_name = aws_glue_catalog_database.truck_db.name
  role          = aws_iam_role.crawler_role.arn
  schedule      = var.crawler_schedule
  dynamic "s3_target" {
    for_each = var.crawler_data_prefixes
    content {
      path = "s3://${aws_s3_bucket.truck_data.bucket}/${s3_target.value}/"
    }
  }

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }
}
