# AIOps Sentinel

**AI-Driven Automated Infrastructure Monitoring and Incident Intelligence System**

Built on AWS — detects infrastructure incidents, analyzes root causes using AI, and delivers intelligent alerts in real time.

---

## Architecture

```
EC2 + Auto Scaling Group
        ↓
CloudWatch Alarms + EventBridge
        ↓
SNS Fan-out
        ↓
Lambda Pipeline:
  ├── Event Parsing
  ├── Log Sanitization + Trimming
  ├── AI Root Cause Analysis (Amazon Bedrock)
  └── Slack Notification
        ↓
DynamoDB (incident storage) + S3 (log archive)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Infrastructure | AWS EC2, ALB, Auto Scaling, Terraform |
| Observability | CloudWatch, EventBridge, X-Ray |
| Compute | AWS Lambda (Python 3.12) |
| AI | Amazon Bedrock (Claude / Nova) |
| Storage | DynamoDB, S3 |
| Alerts | Slack, SNS |
| Security | IAM least privilege, Secrets Manager |
| IaC | Terraform 1.5+ |

---

## Features

- Multi-instance monitoring via Auto Scaling Group
- Real-time event-driven incident detection
- AI-powered root cause analysis with severity classification
- Log sanitization (removes IPs, credentials, emails before AI processing)
- Structured incident storage with 30-day TTL
- Slack alerts with actionable fix suggestions
- Dead Letter Queue for failed event capture
- X-Ray distributed tracing

---

## Project Structure

```
AIOps-Sentinel/
├── terraform/                # Infrastructure as Code
│   ├── modules/              # EC2, Lambda, IAM, Networking, Alarms
│   └── environments/dev/     # Dev environment config
├── lambda/                   # Lambda microservices
│   ├── incident_processor/   # Main pipeline handler
│   ├── log_processor/        # Sanitization + trimming
│   ├── ai_analyzer/          # Bedrock integration
│   └── notification_handler/ # Slack alerts
├── ai/prompts/               # RCA prompt templates
├── tests/                    # Unit + integration tests
├── scripts/                  # Deployment scripts
└── config/                   # IAM policies + config files
```

---

## Setup

```bash
# Clone
git clone https://github.com/reydar-05/AIOps-Sentinel.git
cd AIOps-Sentinel

# Python environment
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# AWS CLI
aws configure

# Infrastructure
cd terraform/environments/dev
terraform init
terraform apply

# Deploy Lambda
python scripts/deploy_lambda.py
```

---

## Status

> Actively being built phase by phase.

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Project Setup | ✅ |
| 1 | Architecture Design | ✅ |
| 2 | Terraform Infrastructure | ✅ |
| 3 | Lambda Local Development | ✅ |
| 4 | Log Processing Engine | ✅ |
| 5 | AI Intelligence (Bedrock) | ✅ |
| 6 | Slack Notifications | ✅ |
| 7 | End-to-End Deployment | ✅ |
| 8 | Security Hardening | ✅ |
| 9 | CloudWatch Dashboard | 🔄 |
| 10+ | Scalability, CI/CD, Cost Optimization | 🔄 |

---

## Author

Built by [reydar-05](https://github.com/reydar-05)
