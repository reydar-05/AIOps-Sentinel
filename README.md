<div align="center">

# 🛡️ AIOps Sentinel

### AI-driven infrastructure monitoring & incident intelligence — built with DevOps practices end to end

[![CI/CD](https://github.com/reydar-05/AIOps-Sentinel/actions/workflows/cicd.yml/badge.svg)](https://github.com/reydar-05/AIOps-Sentinel/actions/workflows/cicd.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?logo=terraform&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-ap--south--1-FF9900?logo=amazonaws&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI%2FCD-2088FF?logo=githubactions&logoColor=white)

</div>

> When infrastructure breaks, AIOps Sentinel **detects** it, **fetches the logs**, **redacts secrets**, asks an **LLM for the root cause**, **stores** the incident and **alerts the team on Discord**.

```
CloudWatch Alarm ─┐
                  ├─▶ SNS ─▶ Lambda pipeline ─┬─▶ DynamoDB (incident history, 30-day TTL)
EC2 State Change ─┘                           └─▶ Discord alert (colour-coded, low-confidence → review channel)
```

## Project modules (three reviews)

| Module | Focus | Tools | Status |
|--------|-------|-------|--------|
| **1. Source control, CI and testing** | Code quality pipeline and a working, testable app | Git/GitHub, GitHub Actions, flake8, pytest, Groq LLM | **Complete.** CI green on PR #1 |
| **2. Infrastructure as Code and cloud** | Reproducible AWS infrastructure and automated deployment | Terraform (5 modules, S3 remote state), AWS Lambda / SNS / SQS / DynamoDB / EC2 + ALB, CD jobs | Code written, to be validated and deployed |
| **3. Monitoring, security and AIOps** | Real alarms end to end, observability, hardening | CloudWatch alarms + dashboard + agent, X-Ray, IAM, Secrets Manager | Code written, to be verified live |

> **Simulated vs real.** In Module 1 every incident is a simulated event: the SNS/CloudWatch payloads and sample logs live in `tests/fixtures` and `scripts/demo.py`. The CI runs and the live Groq call in CI are real. Real-time alarms from a running AWS system arrive with Modules 2 and 3.

## Pipeline (`lambda/incident_processor/handler.py`)

| # | Stage | Module | What it does |
|---|-------|--------|--------------|
| 1 | Parse | `event_parser.py` | Normalises CloudWatch-alarm / EC2-state-change events from SNS |
| 2 | Fetch logs | `log_fetcher.py` | Last 15 min from CloudWatch Logs (`/aws/ec2/aiops`) |
| 3 | Sanitise | `log_sanitizer.py` | Redacts IPs, AWS keys, passwords/tokens, e-mails, internal hostnames |
| 4 | Trim | `log_trimmer.py` | Keeps error lines + latest lines, caps at 4 000 chars |
| 5 | Analyse | `groq_client.py` + `rca_prompt.py` | gpt-oss-120b → gpt-oss-20b fallback → safe hard-coded fallback if AI is down |
| 6 | Persist + notify | `handler.py`, `notifier.py`, `discord_formatter.py` | DynamoDB write, Discord embed |

## DevOps toolchain (by module)

| Practice | Tool |
|----------|------|
| Source control & collaboration (M1) | Git + GitHub |
| CI (M1) / CD (M2) | GitHub Actions: lint → test on every push and PR; terraform apply → deploy Lambda → smoke test on `main` |
| Infrastructure as Code (M2) | Terraform (modular: networking, iam, ec2, alarms, lambda) + S3 remote state |
| Cloud (M2) | AWS – EC2 Auto Scaling + ALB, Lambda, SNS, SQS DLQ, DynamoDB, S3, EventBridge, X-Ray |
| Monitoring & observability (M3) | CloudWatch alarms, dashboard, logs, agent on EC2 |
| Code quality (M1) | flake8 (+bugbear), pytest, offline test suite |
| Secrets management (M3) | GitHub Secrets → `TF_VAR_*` → Lambda env vars; `.env` git-ignored |
| AIOps (M1) | Groq LLM (`gpt-oss-120b`, fallback `gpt-oss-20b`) for automated root-cause analysis |

## Quick start (Module 1, no AWS needed)

```bash
git clone https://github.com/reydar-05/AIOps-Sentinel.git && cd AIOps-Sentinel
git checkout claude/practical-goldberg-r6m7ru      # until PR #1 is merged
pip install -r requirements.txt
python scripts/demo.py            # runs the real pipeline on a sample incident, prints every stage
python -m pytest tests -q         # 26 offline tests
```

Live AI analysis (optional; otherwise the demo uses a canned AI response):

```powershell
# Windows PowerShell
$env:GROQ_API_KEY = "gsk_..."
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
python scripts/demo.py
```
```bash
# macOS / Linux
GROQ_API_KEY=gsk_... python scripts/demo.py
```

Optionally set `DISCORD_WEBHOOK_URL` to post the alert to a Discord channel. If Groq returns `model_not_found`, list the models your key can use (`GET https://api.groq.com/openai/v1/models`) and set `GROQ_MODELS="modelA,modelB"`.

### Project dashboard (local, no server)

```bash
python scripts/build_dashboard.py      # rebuilds dashboard/index.html from the real pipeline code and opens it
```

Or just double-click `dashboard/index.html`. It has an architecture view, an incident simulator (real parsing/redaction code on sample incidents; AI text and alerts are sample output), the AWS resource inventory, the CI/CD flow and module status. Fonts load from Google Fonts when online and fall back to system fonts offline.

Full deployment: see [`STARTUP.md`](STARTUP.md). Review 1 documentation and run-and-show checklist: [`docs/REVIEW1_GUIDE.md`](docs/REVIEW1_GUIDE.md). Project audit, architecture and review notes: [`docs/PROJECT_REVIEW.md`](docs/PROJECT_REVIEW.md).

## Repository layout

```
lambda/            incident_processor · log_processor · ai_analyzer · notification_handler
ai/prompts/        rca_prompt.py
terraform/         modules/{networking,iam,ec2,alarms,lambda} · environments/dev
.github/workflows/ cicd.yml
tests/             offline unit + e2e tests, fixtures
scripts/           demo.py · deploy_lambda.py · verify_setup.py
docs/              PROJECT_REVIEW · risk_analysis · scalability · security_hardening
```
