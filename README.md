# AIOps Sentinel

**AI-Driven Automated Infrastructure Monitoring and Incident Intelligence System**

AIOps Sentinel is a production-grade, serverless incident response platform built on AWS. When a CloudWatch alarm fires or an EC2 instance changes state, it automatically fetches logs, sanitizes them, runs AI-powered root cause analysis, persists the incident to DynamoDB, and delivers a structured Slack alert — all within seconds.

---

## Architecture Overview

```
CloudWatch Alarm ─┐
                  ├──► SNS Topic ──► Lambda Pipeline ──► DynamoDB
EventBridge       ┘         │                       └──► Slack Alert
(EC2 state)                 └──► Email (optional)
                             └──► SQS DLQ (on failure)
```

### Lambda Pipeline (6 steps, ~3–7 seconds end-to-end)

```
SNS Event
  │
  ├─ 1. Event Parser      Parse CloudWatch alarm or EC2 state-change into normalized incident
  ├─ 2. Log Fetcher       Fetch last 15 min of CloudWatch logs for the affected instance
  ├─ 3. Log Sanitizer     Redact IPs, AWS keys, credentials, emails, internal DNS
  ├─ 4. Log Trimmer       Intelligently cap logs to 4 000 chars (priority error lines kept)
  ├─ 5. AI Analyzer       Root cause analysis via Amazon Bedrock → OpenRouter fallback
  ├─ 6a. DynamoDB Write   Persist incident with 30-day TTL
  └─ 6b. Slack Alert      Post rich Block Kit message color-coded by severity
```

---

## AWS Infrastructure

| Resource | Name | Purpose |
|---|---|---|
| Lambda | `aiops-incident-processor-dev` | Main pipeline (Python 3.12, 512 MB, 300s) |
| SNS Topic | `aiops-alerts-dev` | Fan-out from CloudWatch/EventBridge |
| DynamoDB | `aiops-incidents-dev` | Incident store (pay-per-request, 30-day TTL) |
| S3 Bucket | `aiops-log-archive-dev` | Log archiving (IA → Glacier → delete lifecycle) |
| SQS | `aiops-lambda-dlq-dev` | Dead letter queue (14-day retention) |
| Secrets Manager | `aiops/slack/webhook` | Slack webhook URL |
| CloudWatch Alarms | `aiops-high-cpu-dev` + 3 more | CPU, status check, network |
| CloudWatch Dashboard | `AIOps-Sentinel-dev` | Live infrastructure intelligence view |
| EC2 / ASG | `aiops-asg-dev` | Auto-scaled app servers (t3.micro, min 1 / max 3) |
| ALB | `aiops-alb-dev` | Load balancer for EC2 fleet |
| VPC | `10.0.0.0/16` | Isolated network with public + private subnets |
| S3 (state) | `aiops-terraform-state-652197206400` | Shared Terraform remote state |
| X-Ray | Active tracing | Lambda distributed tracing |

---

## AI Analysis

The AI analyzer produces structured JSON for every incident:

```json
{
  "summary": "One-line description of what happened",
  "root_cause": "Technical 2–3 sentence explanation",
  "severity": "CRITICAL | HIGH | MEDIUM | LOW",
  "affected_components": ["EC2", "Auto Scaling", "DynamoDB"],
  "immediate_actions": ["Restart the service", "Scale up ASG"],
  "long_term_fix": "Architectural recommendation",
  "pattern_detected": true,
  "pattern_description": "Memory leak every ~2 hours since last deployment",
  "confidence": "HIGH | MEDIUM | LOW",
  "estimated_impact": "Complete service unavailability for ~5 min"
}
```

**Model priority:**
1. Amazon Bedrock (Claude 3.5 Sonnet / Nova Lite — configured via `BEDROCK_MODEL_ID`)
2. OpenRouter free tier (Gemma, Nemotron, Qwen, GPT-OSS — iterates until one succeeds)
3. Hardcoded fallback (HIGH severity, manual review required)

---

## Slack Alert Format

Each alert is a color-coded Slack Block Kit message:

| Severity | Color |
|---|---|
| CRITICAL | Red `#FF0000` |
| HIGH | Orange `#FF6600` |
| MEDIUM | Yellow `#FFD700` |
| LOW | Blue `#0066CC` |

Fields included: incident ID, alarm name, instance ID, region, root cause, immediate actions, long-term fix, estimated impact, affected components, confidence, and a pattern warning if a recurring issue is detected.

---

## Repository Structure

```
AIOps Sentinel/
├── lambda/
│   ├── incident_processor/    # handler.py (entry point), event_parser.py, log_fetcher.py
│   ├── log_processor/         # processor.py, log_sanitizer.py, log_trimmer.py
│   ├── ai_analyzer/           # analyzer.py, bedrock_client.py, groq_client.py (OpenRouter)
│   └── notification_handler/  # notifier.py, slack_formatter.py, secrets.py
├── ai/
│   └── prompts/rca_prompt.py  # RCA prompt template
├── config/
│   └── settings.py            # Central config (env-based)
├── terraform/
│   ├── environments/dev/      # main.tf, variables.tf, dashboard.tf
│   └── modules/               # networking, ec2, iam, lambda, alarms
├── scripts/
│   └── deploy_lambda.py       # 5-step deployment script
├── tests/
│   ├── fixtures/              # SNS / CloudWatch / EC2 test events
│   ├── test_local_lambda.py   # Event parser tests (3 tests)
│   ├── test_log_processor.py  # Sanitizer + trimmer tests (3 tests)
│   └── test_notifications.py  # Slack formatter tests (4 tests)
└── .github/
    └── workflows/cicd.yml     # CI/CD: Lint → Test → Terraform → Lambda deploy
```

---

## CI/CD Pipeline

GitHub Actions runs on every push to `main`:

| Job | What it does |
|---|---|
| **Lint** | flake8 on all Python code (`lambda/`, `ai/`, `tests/`) |
| **Test** | Runs 3 test suites — no AWS credentials required |
| **Deploy Infrastructure** | `terraform plan` + `terraform apply` using S3 remote state |
| **Deploy Lambda** | Packages + deploys Lambda, then smoke-tests with a real invocation |

### Required GitHub Secrets

| Secret | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key |
| `AWS_ACCOUNT_ID` | Your 12-digit AWS account ID |
| `ALERT_EMAIL` | Email for SNS subscription (optional) |
| `AMI_ID` | Amazon Linux 2023 AMI ID for ap-south-1 |
| `GROQ_API_KEY` | OpenRouter API key (optional AI fallback) |

---

## Testing End-to-End

Invoke the Lambda directly with a simulated CloudWatch alarm:

```bash
aws lambda invoke \
  --function-name aiops-incident-processor-dev \
  --region ap-south-1 \
  --payload file://tests/fixtures/lambda_test_event.json \
  --cli-binary-format raw-in-base64-out \
  response.json
cat response.json
```

Expected response:
```json
{"statusCode": 200, "incident_id": "...", "severity": "HIGH"}
```

You should receive a Slack alert in the `#aiops-alerts` channel within ~5 seconds.

---

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests (no AWS needed)
python tests/test_local_lambda.py
python tests/test_log_processor.py
python tests/test_notifications.py

# Deploy Lambda manually
python scripts/deploy_lambda.py
```

---

## Security Controls

- **IAM least privilege** — Lambda role scoped to only `aiops-*` resources
- **Secrets Manager** — Slack webhook never hardcoded or in environment variables (production)
- **S3 encryption** — AES-256 on all log archive objects
- **S3 public access block** — All 4 flags enabled
- **VPC isolation** — EC2 instances in private subnets, ALB in public subnets
- **Log sanitization** — IPs, AWS keys, credentials, emails redacted before AI processing
- **X-Ray tracing** — Full distributed trace for every Lambda invocation
- **SQS DLQ** — Failed Lambda invocations captured for 14 days for replay

---

## Environment Variables (Lambda)

| Variable | Description |
|---|---|
| `ENVIRONMENT` | `dev` / `staging` / `prod` |
| `BEDROCK_MODEL_ID` | Bedrock model (e.g. `amazon.nova-lite-v1:0`) |
| `BEDROCK_MAX_TOKENS` | Max AI response tokens (default: `2048`) |
| `DYNAMODB_TABLE_NAME` | DynamoDB table (e.g. `aiops-incidents-dev`) |
| `S3_LOG_BUCKET` | Log archive bucket (e.g. `aiops-log-archive-dev`) |
| `SNS_TOPIC_ARN` | SNS topic ARN |
| `SLACK_SECRET_NAME` | Secrets Manager key for Slack webhook |
| `GROQ_API_KEY` | OpenRouter API key for AI fallback |
| `LOG_LEVEL` | `INFO` / `DEBUG` |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.12 |
| IaC | Terraform 1.7+ (modular, S3 remote state) |
| AI | Amazon Bedrock + OpenRouter (multi-model fallback) |
| Messaging | AWS SNS, SQS |
| Storage | DynamoDB, S3 |
| Observability | CloudWatch, X-Ray |
| CI/CD | GitHub Actions |
| Region | ap-south-1 (Mumbai) |
