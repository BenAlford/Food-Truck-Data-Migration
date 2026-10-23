# Existing SES identities (must already be verified in this region). In the SES sandbox both
# the sender and the recipient need to be verified.
data "aws_sesv2_email_identity" "report" {
  for_each       = toset([var.report_email_sender, var.report_email_recipient])
  email_identity = each.value
}

data "aws_iam_policy_document" "sfn_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
  }
}

resource "aws_iam_role" "report_state_machine" {
  name               = "${var.name_prefix}-report-sfn-role"
  assume_role_policy = data.aws_iam_policy_document.sfn_assume_role.json
}

data "aws_iam_policy_document" "report_state_machine" {
  statement {
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.report.arn, "${aws_lambda_function.report.arn}:*"]
  }

  statement {
    actions   = ["ses:SendEmail"]
    resources = [for identity in data.aws_sesv2_email_identity.report : identity.arn]
  }
}

resource "aws_iam_role_policy" "report_state_machine" {
  name   = "${var.name_prefix}-report-sfn-policy"
  role   = aws_iam_role.report_state_machine.id
  policy = data.aws_iam_policy_document.report_state_machine.json
}

# JSONata state machine. The report covers the date in the execution input ({"date": "YYYY-MM-DD"}),
# or yesterday when no date is given. "Yesterday" is worked out in UTC, which matches UK time
# except between 00:00 and 01:00 BST.
resource "aws_sfn_state_machine" "report" {
  name     = "${var.name_prefix}-report"
  role_arn = aws_iam_role.report_state_machine.arn

  definition = jsonencode({
    Comment       = "Builds the daily transaction report and emails it"
    QueryLanguage = "JSONata"
    StartAt       = "GenerateReport"
    States = {
      GenerateReport = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Arguments = {
          FunctionName = aws_lambda_function.report.arn
          Payload = {
            date = "{% $exists($states.input.date) ? $states.input.date : $fromMillis($millis() - 86400000, '[Y0001]-[M01]-[D01]') %}"
          }
        }
        Output = "{% $states.result.Payload %}"
        Retry = [{
          ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException", "Lambda.TooManyRequestsException"]
          IntervalSeconds = 2
          MaxAttempts     = 3
          BackoffRate     = 2
        }]
        Next = "SendEmail"
      }

      SendEmail = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:sesv2:sendEmail"
        Arguments = {
          FromEmailAddress = var.report_email_sender
          Destination = {
            ToAddresses = [var.report_email_recipient]
          }
          Content = {
            Simple = {
              Subject = {
                Data    = "{% $states.input.subject %}"
                Charset = "UTF-8"
              }
              Body = {
                Html = {
                  Data    = "{% $states.input.html %}"
                  Charset = "UTF-8"
                }
              }
            }
          }
        }
        End = true
      }
    }
  })
}
