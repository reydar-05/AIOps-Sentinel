<div align="center">

# 🛡️ AIOps Sentinel

### AI-driven infrastructure monitoring and incident analysis for AWS

[![CI/CD](https://github.com/reydar-05/AIOps-Sentinel/actions/workflows/cicd.yml/badge.svg)](https://github.com/reydar-05/AIOps-Sentinel/actions/workflows/cicd.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?logo=terraform&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-ap--south--1-FF9900?logo=amazonaws&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI%2FCD-2088FF?logo=githubactions&logoColor=white)

</div>

When infrastructure raises an alarm, AIOps Sentinel **fetches the logs**, **redacts secrets**, asks an **LLM for the root cause**, **stores the incident** and **alerts the team on Discord**.

```
CloudWatch alarm ─┐
                  ├─▶ SNS ─▶ Lambda pipeline ─┬─▶ DynamoDB (incident history, 30-day TTL)
EC2 state change ─┘                           └─▶ Discord alert (low confidence → review channel)
```

## How it works

| # | Stage | Module | What it does |
|---|-------|--------|--------------|
| 1 | Parse | `event_parser.py` | Normalises CloudWatch alarm and EC2 state-change events from SNS |
| 2 | Fetch logs | `log_fetcher.py` | Reads the last 15 minutes from CloudWatch Logs |
| 3 | Sanitise | `log_sanitizer.py` | Redacts IPs, AWS keys, passwords and tokens, e-mails, internal hostnames |
| 4 | Trim | `log_trimmer.py` | Keeps error lines plus the latest lines, capped at 4,000 characters |
| 5 | Analyse | `groq_client.py`, `rca_prompt.py` | Structured root-cause analysis with `gpt-oss-120b`, falling back to `gpt-oss-20b`, then to a safe manual-review response |
| 6 | Persist | `handler.py` | Saves the incident to DynamoDB |
| 7 | Notify | `notifier.py`, `discord_formatter.py` | Colour-coded Discord embed |

Each analysis includes severity, confidence, root cause, affected components, immediate actions and a long-term fix. If the AI is unavailable, the alert is still sent.

## DevOps toolchain

| Practice | Tool |
|----------|------|
| Version control | Git, GitHub |
| Continuous integration | GitHub Actions: lint, then tests on every push and pull request |
| Continuous delivery | GitHub Actions: `terraform apply`, Lambda deploy and smoke test on `main` |
| Infrastructure as code | Terraform: networking, iam, ec2, alarms and lambda modules, S3 remote state |
| Code quality | flake8 (with bugbear), pytest |
| Cloud | EC2 Auto Scaling + ALB, Lambda, SNS, SQS dead-letter queue, DynamoDB, S3, EventBridge |
| Observability | CloudWatch alarms, dashboard and agent; X-Ray tracing |
| Security | Least-privilege IAM, log redaction before any external call, GitHub Secrets |
| AIOps | Groq-hosted LLM for root-cause analysis |

## Getting started

```bash
pip install -r requirements.txt
python scripts/demo.py               # runs the pipeline on a sample incident and prints every stage
python -m pytest tests -q            # automated test suite, no cloud account needed
python scripts/build_dashboard.py    # builds and opens the local dashboard (dashboard/index.html)
```

Set `GROQ_API_KEY` for live AI analysis and `DISCORD_WEBHOOK_URL` to post alerts to Discord; without them the demo uses a sample AI response. Copy `.env.example` for the full list of settings. Deployment instructions are in [`STARTUP.md`](STARTUP.md).

## Repository layout

```
lambda/            incident_processor · log_processor · ai_analyzer · notification_handler
ai/prompts/        rca_prompt.py
terraform/         modules/{networking,iam,ec2,alarms,lambda} · environments/dev
.github/workflows/ cicd.yml
tests/             unit, end-to-end and performance tests, fixtures
scripts/           demo.py · build_dashboard.py · deploy_lambda.py · verify_setup.py
dashboard/         local single-file dashboard
docs/              risk_analysis · scalability · security_hardening
```

## Documentation

- [`STARTUP.md`](STARTUP.md): deployment guide
- [`docs/risk_analysis.md`](docs/risk_analysis.md), [`docs/scalability.md`](docs/scalability.md), [`docs/security_hardening.md`](docs/security_hardening.md)
- Full project documentation (problem, architecture, design, testing and status) is kept as a separate Word document.

## License

MIT
