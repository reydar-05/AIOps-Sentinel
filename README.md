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

## Pipeline (`lambda/incident_processor/handler.py`)

| # | Stage | Module | What it does |
|---|-------|--------|--------------|
| 1 | Parse | `event_parser.py` | Normalises CloudWatch-alarm / EC2-state-change events from SNS |
| 2 | Fetch logs | `log_fetcher.py` | Last 15 min from CloudWatch Logs (`/aws/ec2/aiops`) |
| 3 | Sanitise | `log_sanitizer.py` | Redacts IPs, AWS keys, passwords/tokens, e-mails, internal hostnames |
| 4 | Trim | `log_trimmer.py` | Keeps error lines + latest lines, caps at 4 000 chars |
| 5 | Analyse | `groq_client.py` + `rca_prompt.py` | gpt-oss-120b → gpt-oss-20b fallback → safe hard-coded fallback if AI is down |
| 6 | Persist + notify | `handler.py`, `notifier.py`, `discord_formatter.py` | DynamoDB write, Discord embed |

## DevOps toolchain

| Practice | Tool |
|----------|------|
| Source control & collaboration | Git + GitHub |
| CI/CD | GitHub Actions (lint → test → terraform apply → deploy Lambda → smoke test) |
| Infrastructure as Code | Terraform (modular: networking, iam, ec2, alarms, lambda) + S3 remote state |
| Cloud | AWS – EC2 Auto Scaling + ALB, Lambda, SNS, SQS DLQ, DynamoDB, S3, EventBridge, X-Ray |
| Monitoring & observability | CloudWatch alarms, dashboard, logs, agent on EC2 |
| Code quality | flake8 (+bugbear), pytest, offline test suite |
| Secrets management | GitHub Secrets → `TF_VAR_*` → Lambda env vars; `.env` git-ignored |
| AIOps | Groq LLM for automated root-cause analysis |

## Quick start (no AWS needed)

```bash
pip install -r requirements.txt
python scripts/demo.py            # runs the real pipeline on a sample incident, prints every stage
python -m pytest tests -q         # 23 offline tests
GROQ_API_KEY=gsk_... python scripts/demo.py   # live AI analysis
```

Full deployment: see [`STARTUP.md`](STARTUP.md). Project audit, architecture and review notes: [`docs/PROJECT_REVIEW.md`](docs/PROJECT_REVIEW.md).

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
