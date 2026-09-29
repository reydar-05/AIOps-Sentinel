# AIOps Sentinel — Project Review Document

## 1. Problem & concept

On-call engineers get a bare alarm ("CPU > 80%") and must dig through logs to learn *why*.
**AIOps Sentinel automates that first triage step:** when an alarm fires it collects the relevant logs,
strips sensitive data, asks an LLM for a structured root-cause analysis (severity, confidence, concrete
actions), saves the incident and posts a rich alert to Discord — within seconds.

## 2. Architecture

```
 CloudWatch Alarms (CPU, status-check, network) ─┐
 EventBridge (EC2 stopped/terminated)  ──────────┴─▶ SNS topic ─▶ Lambda (Python 3.12)
                                                                     │ 1 parse  2 fetch logs (CloudWatch Logs)
                                                                     │ 3 sanitise  4 trim  5 Groq LLM RCA
                                                                     ├─▶ DynamoDB (incident, TTL 30d)
                                                                     ├─▶ Discord webhook (LOW confidence → review channel)
                                                                     └─▶ SQS dead-letter queue on failure
 Monitored workload: VPC + ALB + Auto Scaling Group of EC2 (CloudWatch agent ships logs)
```

Resilience: AI failure ⇒ safe fallback analysis (HIGH severity, "manual review") and the alert is still sent;
DynamoDB failure never blocks the alert; unrecoverable errors go to the DLQ.

## 3. DevOps tools & where they are used

| Area | Tool | Evidence in repo |
|------|------|------------------|
| Version control | Git / GitHub | branch-based history |
| CI | GitHub Actions – flake8 lint, pytest | `.github/workflows/cicd.yml` jobs `lint`, `test` |
| CD | GitHub Actions – `terraform apply`, Lambda package + deploy, post-deploy smoke test | jobs `deploy-infra`, `deploy-lambda` |
| IaC | Terraform, 5 reusable modules, S3 remote state, `default_tags` | `terraform/` |
| Monitoring | CloudWatch alarms/dashboard/agent, X-Ray tracing | `modules/alarms`, `dashboard.tf` |
| Security | least-privilege IAM, log sanitiser, S3 encryption + public-access block, secrets via GitHub Secrets | `modules/iam`, `log_sanitizer.py` |
| Testing | pytest, fixtures, performance SLO tests, live-AI quality gate | `tests/` |
| AIOps | Groq gpt-oss-120b, prompt engineering, confidence-based routing | `ai/prompts`, `groq_client.py` |

## 4. Audit results (this review)

### Was broken → fixed
| # | Problem | Impact | Fix |
|---|---------|--------|-----|
| 1 | `discord_formatter.py` **never committed** | Lambda crashed on import (`ModuleNotFoundError`) – whole pipeline dead; `test_performance.py` failed | Added `lambda/notification_handler/discord_formatter.py` |
| 2 | CI ran `tests/test_discord.py` and `tests/test_realworld_logs.py` which did not exist | CI red on every push, deploy jobs never ran | Added both tests; CI now also runs `pytest tests` |
| 3 | `requirements.txt` was UTF-16 encoded (with Windows-only packages) | `pip install -r` fails | Replaced with clean UTF-8 minimal list |
| 4 | Two workflows (`cicd.yml`, `deploy.yml`) both applied Terraform on push to `main` | Duplicate/racing deploys | Removed `deploy.yml` |
| 5 | `deploy_lambda.py` hard-coded `C:\Temp` | Fails on the Linux GitHub runner | Uses `tempfile.gettempdir()` |
| 6 | CloudWatch agent started with `-c default` – no log collection; log group `/aws/ec2/aiops` never created | Every incident got "log group not found" → useless LOW-confidence AI output | Agent config ships `/var/log/messages` + httpd logs; Terraform creates the log group |
| 7 | ASG-level CPU alarm (no `InstanceId` dimension) pointed log fetch at the Lambda's own log group | AI analysed the wrong logs | Parser uses the EC2 log group when an ASG is present |
| 8 | Discord `_post` didn't catch `URLError`/timeouts | Noisy error path | Handled, returns `False` |
| 9 | README/STARTUP/docs described Slack + Bedrock | Documentation contradicted the code | README rewritten; legacy banners on older docs |

### Verified working (offline)
Event parsing (CloudWatch + EC2), sanitisation (IP, keys, passwords, e-mail, internal hosts), trimming,
error classification, RCA prompt, Groq response parsing/validation, Discord formatting and webhook routing,
handler end-to-end incl. AI-failure fallback, performance SLOs. **23 tests pass; flake8 clean.**

### Not verifiable without cloud credentials
`terraform validate/plan/apply`, live Groq calls, real Discord delivery, deployed Lambda smoke test.
(Terraform edits were kept small; run `terraform validate` before the first apply.)

### Known limitations / future work
- Secrets (Groq key, webhook) are Lambda env vars and therefore appear in Terraform state → move to Secrets Manager/SSM.
- Token counter is per-container (soft limit only); persist in DynamoDB for a hard cap.
- Only alarm/EC2-state events; no auto-remediation yet (suggested actions are advisory).
- `deploy.yml`-style PR `terraform plan` job was dropped with the duplicate workflow – add it to `cicd.yml` if wanted.
- `docs/risk_analysis.md`, `scalability.md`, `security_hardening.md` still discuss Bedrock/Slack (banner explains the mapping).

## 5. Demo script for the review (≈5 min)

1. **Concept** – slide/diagram from §2.
2. `python scripts/demo.py` – shows the 5 stages live: raw logs with secrets → redacted → AI JSON → Discord message.
   With `GROQ_API_KEY` set the AI stage is a real LLM call; with `DISCORD_WEBHOOK_URL` it posts to Discord.
3. `python -m pytest tests -q` – 23 passed.
4. Show `terraform/` modules + `.github/workflows/cicd.yml` pipeline and the green Actions run.
5. Show AWS console (if deployed): CloudWatch dashboard, DynamoDB incident table, Lambda logs.
6. Trigger a real incident: `aws ec2 stop-instances ...` or `stress-ng` on an instance → Discord alert.
