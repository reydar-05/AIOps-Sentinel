# AIOps Sentinel — Startup Guide

Complete setup guide for deploying AIOps Sentinel from scratch in a new environment.

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.12+ | python.org |
| Terraform | 1.7+ | developer.hashicorp.com/terraform |
| AWS CLI | v2 | docs.aws.amazon.com/cli |
| Git | any | git-scm.com |

---

## Step 1 — AWS Account Setup

### 1a. Configure AWS CLI

```bash
aws configure
# Enter: Access Key ID, Secret Access Key, Region: ap-south-1, Format: json
```

Verify:
```bash
aws sts get-caller-identity
```

### 1b. Required IAM Permissions

The IAM user running Terraform needs these AWS managed policies:
- `AmazonEC2FullAccess`
- `AmazonVPCFullAccess`
- `AmazonDynamoDBFullAccess`
- `AmazonS3FullAccess`
- `AWSLambda_FullAccess`
- `AmazonSNSFullAccess`
- `AmazonSQSFullAccess`
- `IAMFullAccess`
- `CloudWatchFullAccess`
- `SecretsManagerReadWrite`
- `AmazonEventBridgeFullAccess`

---

## Step 2 — Clone and Install

```bash
git clone <your-repo-url>
cd "AIOps Sentinel"
pip install -r requirements.txt
```

---

## Step 3 — Create Terraform State Bucket

This only needs to be done once. Replace the account ID if different:

```bash
aws s3 mb s3://aiops-terraform-state-652197206400 --region ap-south-1
aws s3api put-bucket-versioning --bucket aiops-terraform-state-652197206400 --versioning-configuration Status=Enabled
```

---

## Step 4 — Configure Variables

Create `terraform/environments/dev/terraform.tfvars`:

```hcl
aws_account_id = "652197206400"
alert_email    = "your-email@example.com"
ami_id         = "ami-0f58b397bc5c1f2e8"
groq_api_key   = ""
```

> **Note:** `terraform.tfvars` is git-ignored. Never commit it.

To find the latest Amazon Linux 2023 AMI for ap-south-1:
```bash
aws ssm get-parameter --name "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64" --region ap-south-1 --query "Parameter.Value" --output text
```

---

## Step 5 — Configure Slack Webhook

1. Go to your Slack workspace → Apps → Incoming Webhooks → Add New Webhook
2. Choose a channel (e.g. `#aiops-alerts`) and copy the webhook URL

After Terraform deploys (Step 6), update the secret:
```bash
aws secretsmanager put-secret-value \
  --secret-id aiops/slack/webhook \
  --secret-string "{\"webhook_url\":\"https://hooks.slack.com/services/YOUR/WEBHOOK/URL\",\"channel\":\"#aiops-alerts\"}" \
  --region ap-south-1
```

---

## Step 6 — Deploy Infrastructure

```bash
cd terraform/environments/dev
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

This creates all AWS resources (~3–5 minutes). Confirm with `yes` when prompted.

---

## Step 7 — Deploy Lambda

From the project root:

```bash
python scripts/deploy_lambda.py
```

This packages all Lambda source files and dependencies, uploads to AWS, and prints the package size and deployment status.

---

## Step 8 — Set Up GitHub Actions (CI/CD)

In your GitHub repository → Settings → Secrets → Actions, add:

| Secret | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | Your IAM access key |
| `AWS_SECRET_ACCESS_KEY` | Your IAM secret key |
| `AWS_ACCOUNT_ID` | `652197206400` |
| `ALERT_EMAIL` | Your email address |
| `AMI_ID` | `ami-0f58b397bc5c1f2e8` |
| `GROQ_API_KEY` | OpenRouter key (or leave empty) |

Push any commit to `main` to trigger the full pipeline.

---

## Step 9 — Verify Everything Works

### Run unit tests (no AWS needed)
```bash
python tests/test_local_lambda.py
python tests/test_log_processor.py
python tests/test_notifications.py
```

### Trigger an end-to-end test
```bash
aws lambda invoke --function-name aiops-incident-processor-dev --region ap-south-1 --payload file://tests/fixtures/lambda_test_event.json --cli-binary-format raw-in-base64-out response.json
```

Check the response:
```bash
cat response.json
```

Expected: `{"statusCode": 200, "incident_id": "...", "severity": "HIGH"}`

You should receive a Slack alert in ~5 seconds.

### Check the CloudWatch Dashboard
Open the AWS console → CloudWatch → Dashboards → `AIOps-Sentinel-dev`

---

## Ongoing Operations

### Redeploy Lambda after code changes
```bash
python scripts/deploy_lambda.py
```

Or push to `main` — CI/CD handles it automatically.

### View Lambda logs
```bash
aws logs tail /aws/lambda/aiops-incident-processor-dev --follow --region ap-south-1
```

### Query incidents in DynamoDB
```bash
aws dynamodb scan --table-name aiops-incidents-dev --region ap-south-1 --output table
```

### Replay a failed event from DLQ
```bash
# List messages in DLQ
aws sqs receive-message --queue-url https://sqs.ap-south-1.amazonaws.com/652197206400/aiops-lambda-dlq-dev --region ap-south-1
```

### Destroy all infrastructure (dev teardown)
```bash
cd terraform/environments/dev
terraform destroy -var-file=terraform.tfvars
```

---

## Troubleshooting

| Problem | Check |
|---|---|
| Lambda returns `FunctionError` | `aws logs tail /aws/lambda/aiops-incident-processor-dev --region ap-south-1` |
| No Slack message | Check `aiops/slack/webhook` secret has a valid webhook URL |
| AI analysis unavailable | Check `GROQ_API_KEY` env var on Lambda; verify OpenRouter key is valid |
| Terraform state conflict | Ensure S3 backend bucket exists and IAM user has S3 access |
| CI/CD Terraform fails | Verify all 6 GitHub secrets are set with no leading/trailing spaces |
| DynamoDB `ResourceNotFound` | Check `DYNAMODB_TABLE_NAME` env var on Lambda matches table name (`aiops-incidents-dev`) |

---

## Key Resource Names (dev environment)

| Resource | Name |
|---|---|
| Lambda | `aiops-incident-processor-dev` |
| SNS Topic | `aiops-alerts-dev` |
| DynamoDB | `aiops-incidents-dev` |
| S3 Log Archive | `aiops-log-archive-dev` |
| SQS DLQ | `aiops-lambda-dlq-dev` |
| Secrets Manager | `aiops/slack/webhook` |
| CloudWatch Dashboard | `AIOps-Sentinel-dev` |
| ASG | `aiops-asg-dev` |
| Terraform State Bucket | `aiops-terraform-state-652197206400` |
| Log Group | `/aws/lambda/aiops-incident-processor-dev` |

## CI/CD Workflow

git add .github/workflows/deploy.yml
git commit -m "ci: add GitHub Actions CI/CD pipeline"
git push origin main

## Testing & Validation

$env:PYTHONIOENCODING="utf-8"
python tests/test_performance.py