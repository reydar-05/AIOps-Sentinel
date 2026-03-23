<div align="center">

# 🛡️ AIOps Sentinel

### AI-Driven Automated Infrastructure Monitoring & Incident Intelligence

[![CI/CD](https://github.com/reydar-05/AIOps-Sentinel/actions/workflows/cicd.yml/badge.svg)](https://github.com/reydar-05/AIOps-Sentinel/actions/workflows/cicd.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-1.7+-7B42BC?logo=terraform&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-ap--south--1-FF9900?logo=amazonaws&logoColor=white)
![Lambda](https://img.shields.io/badge/Lambda-Python%203.12-FF9900?logo=awslambda&logoColor=white)
![DynamoDB](https://img.shields.io/badge/DynamoDB-Incidents-4053D6?logo=amazondynamodb&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22c55e)

<br/>

> **When your infrastructure breaks, AIOps Sentinel detects it, fetches the logs, asks AI what went wrong, and tells your team on Slack — in under 7 seconds.**

<br/>

```
  CloudWatch Alarm  ──┐
                      ├──▶  SNS  ──▶  Lambda Pipeline  ──▶  DynamoDB
  EC2 State Change  ──┘                                 └──▶  Slack Alert
```

</div>

---

## ✨ What It Does

| Step | What Happens |
|------|-------------|
| 🔔 **Detects** | CloudWatch alarm fires (CPU > 80%, disk full, instance crash) or EC2 state changes |
| 📋 **Fetches Logs** | Pulls the last 15 minutes of CloudWatch logs for the affected instance |
| 🔒 **Sanitizes** | Strips IPs, AWS keys, credentials, emails before any external call |
| ✂️ **Trims** | Intelligently caps logs to 4 000 chars — keeps error lines, drops noise |
| 🧠 **AI Analysis** | Amazon Bedrock (or OpenRouter fallback) produces structured root cause analysis |
| 💾 **Persists** | Writes incident to DynamoDB with 30-day TTL |
| 💬 **Alerts** | Posts a rich, color-coded Slack message in ~5 seconds |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TRIGGER LAYER                                │
│                                                                     │
│   ┌──────────────────────┐    ┌──────────────────────────────┐     │
│   │  CloudWatch Alarms   │    │  EventBridge (EC2 state)     │     │
│   │  • CPU > 80%         │    │  • stopped / terminated      │     │
│   │  • Status check fail │    │  • stopping                  │     │
│   │  • Network anomaly   │    └──────────────┬───────────────┘     │
│   └──────────┬───────────┘                   │                     │
└──────────────┼───────────────────────────────┼─────────────────────┘
               └──────────────┬────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         SNS TOPIC                                   │
│               aiops-alerts-dev                                      │
│    ┌──────────────┬─────────────────┬──────────────┐               │
│    ▼              ▼                 ▼               ▼               │
│  Lambda         Email           SQS DLQ         (future)           │
│  (primary)    (optional)      (on failure)                         │
└────┬────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     LAMBDA PIPELINE                                 │
│              aiops-incident-processor-dev                           │
│              Python 3.12 │ 512 MB │ 300s timeout                   │
│                                                                     │
│  1. Event Parser   ──▶  Normalize CloudWatch / EC2 event           │
│  2. Log Fetcher    ──▶  15-min CloudWatch logs                      │
│  3. Log Sanitizer  ──▶  Redact secrets, IPs, credentials           │
│  4. Log Trimmer    ──▶  4 000-char intelligent truncation           │
│  5. AI Analyzer    ──▶  Bedrock RCA  ──(fallback)──▶  OpenRouter   │
│  6a. DynamoDB      ──▶  Persist incident (30-day TTL)              │
│  6b. Slack         ──▶  Block Kit alert                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🧠 AI-Powered Root Cause Analysis

Every incident gets a structured AI response:

```json
{
  "summary":             "Java heap exhaustion caused complete service outage",
  "root_cause":          "OOM triggered by unbounded cache growth in DataProcessor.java. GC overhead exceeded 98%, causing all threads to halt.",
  "severity":            "HIGH",
  "severity_reason":     "Full service unavailability, no self-recovery observed",
  "affected_components": ["EC2", "Auto Scaling Group", "ALB"],
  "immediate_actions":   ["Restart affected instances", "Increase JVM heap to 4GB", "Scale ASG to 3 instances"],
  "long_term_fix":       "Implement bounded cache with LRU eviction and add memory pressure alarms",
  "pattern_detected":    true,
  "pattern_description": "OOM crash recurring every ~2 hours since v2.3.1 deployment",
  "confidence":          "HIGH",
  "estimated_impact":    "~5 min full outage, ~200 users affected"
}
```

### Model Priority Chain

```
1. 🥇 Amazon Bedrock     →  Claude 3.5 Sonnet / Nova Lite (configurable)
2. 🥈 OpenRouter Free    →  Gemma 3N → Nemotron 9B → Qwen3 4B → GPT-OSS 20B
3. 🥉 Hardcoded Fallback →  HIGH severity, manual review flag
```

---

## 💬 Slack Alert Preview

```
┌────────────────────────────────────────────────────────────┐
│ 🔴  AIOps Sentinel Alert — HIGH                            │
├────────────────────────────────────────────────────────────┤
│ Java heap exhaustion caused complete service outage        │
├────────────────────────────────────────────────────────────┤
│ Incident ID   │ abc-1234-...                               │
│ Environment   │ dev                                        │
│ Alarm         │ aiops-high-cpu-dev                         │
│ Instance      │ i-0abc123def456789                         │
│ Region        │ ap-south-1                                 │
│ Confidence    │ HIGH                                       │
├────────────────────────────────────────────────────────────┤
│ Root Cause                                                  │
│ OOM triggered by unbounded cache growth...                 │
├────────────────────────────────────────────────────────────┤
│ Immediate Actions                                           │
│ • Restart affected instances                               │
│ • Increase JVM heap to 4GB                                 │
│ • Scale ASG to 3 instances                                 │
├────────────────────────────────────────────────────────────┤
│ ⚠️  Recurring Pattern: OOM every ~2h since v2.3.1          │
└────────────────────────────────────────────────────────────┘
```

**Severity colors:** 🔴 CRITICAL &nbsp;|&nbsp; 🟠 HIGH &nbsp;|&nbsp; 🟡 MEDIUM &nbsp;|&nbsp; 🔵 LOW

---

## ☁️ AWS Infrastructure

<table>
<tr><th>Resource</th><th>Name</th><th>Purpose</th></tr>
<tr><td>⚡ Lambda</td><td><code>aiops-incident-processor-dev</code></td><td>Main pipeline (512 MB, 300s, X-Ray)</td></tr>
<tr><td>📣 SNS</td><td><code>aiops-alerts-dev</code></td><td>Alarm fan-out to Lambda + email</td></tr>
<tr><td>🗄️ DynamoDB</td><td><code>aiops-incidents-dev</code></td><td>Incident store (pay-per-request, 30-day TTL)</td></tr>
<tr><td>🪣 S3</td><td><code>aiops-log-archive-dev</code></td><td>Log archiving (IA → Glacier → delete)</td></tr>
<tr><td>💀 SQS DLQ</td><td><code>aiops-lambda-dlq-dev</code></td><td>Failed events (14-day retention)</td></tr>
<tr><td>🔐 Secrets Manager</td><td><code>aiops/slack/webhook</code></td><td>Slack webhook URL</td></tr>
<tr><td>📊 CloudWatch</td><td><code>aiops-high-cpu-dev</code> +3</td><td>CPU, status check, network alarms</td></tr>
<tr><td>📈 Dashboard</td><td><code>AIOps-Sentinel-dev</code></td><td>Live infrastructure intelligence view</td></tr>
<tr><td>🖥️ EC2 / ASG</td><td><code>aiops-asg-dev</code></td><td>Auto-scaled fleet (t3.micro, 1–3 instances)</td></tr>
<tr><td>⚖️ ALB</td><td><code>aiops-alb-dev</code></td><td>Load balancer (public subnets, multi-AZ)</td></tr>
<tr><td>🌐 VPC</td><td><code>10.0.0.0/16</code></td><td>Isolated network, public + private subnets</td></tr>
<tr><td>🪣 S3 (state)</td><td><code>aiops-terraform-state-*</code></td><td>Shared Terraform remote state</td></tr>
</table>

---

## 🚀 CI/CD Pipeline

Every push to `main` triggers a 4-stage GitHub Actions pipeline:

```
Push to main
     │
     ▼
┌─────────┐    ┌─────────┐    ┌────────────────────┐    ┌────────────────┐
│  Lint   │───▶│  Test   │───▶│ Deploy Infra       │───▶│ Deploy Lambda  │
│         │    │         │    │ (Terraform)        │    │                │
│ flake8  │    │ 3 test  │    │ init → validate    │    │ package + zip  │
│ lambda/ │    │ suites  │    │ plan → apply       │    │ upload to AWS  │
│ ai/     │    │ no AWS  │    │ S3 remote state    │    │ smoke test     │
│ tests/  │    │ needed  │    │                    │    │                │
└─────────┘    └─────────┘    └────────────────────┘    └────────────────┘
  ~30s           ~60s               ~2 min                   ~45s
```

> ⚠️ **Note:** Infrastructure and Lambda deploy jobs only run on pushes to `main` (not PRs).

### GitHub Secrets Required

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key |
| `AWS_ACCOUNT_ID` | 12-digit AWS account ID |
| `ALERT_EMAIL` | Email for SNS alerts (optional) |
| `AMI_ID` | Amazon Linux 2023 AMI for ap-south-1 |
| `GROQ_API_KEY` | OpenRouter API key (optional fallback) |

---

## 📁 Repository Structure

```
AIOps Sentinel/
│
├── 🔧 lambda/
│   ├── incident_processor/    # handler.py · event_parser.py · log_fetcher.py
│   ├── log_processor/         # processor.py · log_sanitizer.py · log_trimmer.py
│   ├── ai_analyzer/           # analyzer.py · bedrock_client.py · groq_client.py
│   └── notification_handler/  # notifier.py · slack_formatter.py · secrets.py
│
├── 🧠 ai/
│   └── prompts/rca_prompt.py  # RCA prompt template for Bedrock
│
├── ⚙️ config/
│   └── settings.py            # Central config loaded from environment
│
├── 🏗️ terraform/
│   ├── environments/dev/      # main.tf · variables.tf · dashboard.tf
│   └── modules/               # networking · ec2 · iam · lambda · alarms
│
├── 📜 scripts/
│   └── deploy_lambda.py       # 5-step Lambda packaging + deployment
│
├── 🧪 tests/
│   ├── fixtures/              # SNS · CloudWatch · EC2 test events
│   ├── test_local_lambda.py   # Event parser (3 tests)
│   ├── test_log_processor.py  # Sanitizer + trimmer (3 tests)
│   └── test_notifications.py  # Slack formatter (4 tests)
│
└── 🔄 .github/workflows/
    └── cicd.yml               # Lint → Test → Terraform → Lambda
```

---

## 🧪 Testing

```bash
# All tests run locally — no AWS credentials needed
python tests/test_local_lambda.py    # 3 tests: event parsing
python tests/test_log_processor.py   # 3 tests: sanitize, trim, classify
python tests/test_notifications.py   # 4 tests: Slack Block Kit formatting
```

### End-to-End Test (live AWS)

```bash
aws lambda invoke \
  --function-name aiops-incident-processor-dev \
  --region ap-south-1 \
  --payload file://tests/fixtures/lambda_test_event.json \
  --cli-binary-format raw-in-base64-out \
  response.json && cat response.json
```

Expected: `{"statusCode": 200, "incident_id": "...", "severity": "HIGH"}` + Slack alert in ~5s

---

## 🔒 Security

- **IAM least privilege** — Lambda role restricted to `aiops-*` resources only
- **Secrets Manager** — Slack webhook stored encrypted, fetched at runtime
- **Log sanitization** — Credentials, IPs, and keys stripped before AI processing
- **S3 encryption** — AES-256 on all objects, all public access blocked
- **VPC isolation** — EC2 in private subnets, ALB in public subnets
- **X-Ray tracing** — Full distributed trace on every Lambda invocation
- **SQS DLQ** — Failed events retained 14 days for replay

---

## 🛠️ Tech Stack

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-1.7+-7B42BC?logo=terraform&logoColor=white)
![AWS Lambda](https://img.shields.io/badge/AWS_Lambda-FF9900?logo=awslambda&logoColor=white)
![DynamoDB](https://img.shields.io/badge/DynamoDB-4053D6?logo=amazondynamodb&logoColor=white)
![Amazon SNS](https://img.shields.io/badge/SNS-FF4F8B?logo=amazonaws&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?logo=githubactions&logoColor=white)

---

<div align="center">

**Built with ❤️ on AWS &nbsp;|&nbsp; Region: ap-south-1 (Mumbai)**

*AIOps Sentinel — from alarm to answer in under 7 seconds*

</div>
