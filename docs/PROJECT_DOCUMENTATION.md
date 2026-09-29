# AIOps Sentinel: Project Documentation

*Automated infrastructure monitoring with AI-generated incident analysis, built with DevOps practices.*

---

## 1. Abstract

AIOps Sentinel is a serverless incident-response pipeline for AWS. When a monitoring alarm fires or an EC2 instance
changes state, the system collects the relevant logs, removes sensitive data, asks a large language model for a
structured root-cause analysis, stores the incident, and sends an alert to a Discord channel. The project also serves
as a worked example of a modern DevOps toolchain: version control, continuous integration, automated testing,
infrastructure as code, continuous delivery and observability.

## 2. Problem statement

An operations engineer who receives a bare alarm such as "CPU utilisation above 80%" must locate the right logs,
read through them, form a hypothesis and decide on an action. This first triage step is repetitive, slow at night
and error-prone under pressure. Sending raw logs to an external AI service, however, risks leaking passwords, keys and
network details. The project automates the triage step while protecting sensitive data.

## 3. Objectives

1. Detect infrastructure incidents automatically from CloudWatch alarms and EC2 state changes.
2. Produce a root-cause analysis with severity, confidence and concrete next actions.
3. Keep sensitive data out of the AI request.
4. Keep working when the AI service is unavailable.
5. Build, test and deploy the whole system through an automated, reproducible DevOps pipeline.

## 4. System architecture

```
 Monitored workload                 Event routing                Processing                     Outputs
 ------------------                 -------------                ----------                     -------
 VPC + ALB + Auto Scaling Group     CloudWatch alarms  --+
 EC2 instances + CloudWatch agent   EventBridge (EC2   --+--> SNS topic --> Lambda pipeline --> DynamoDB (incident record)
   |  logs                            state changes)                          |    |          --> Discord webhook (alert)
   v                                                                          |    +--> Groq LLM API (analysis)
 CloudWatch Logs  <---------------------------------------------------------- +--> SQS dead-letter queue (failures)
```

### 4.1 Pipeline stages

| # | Stage | Module | Behaviour |
|---|-------|--------|-----------|
| 1 | Parse | `event_parser.py` | Recognises CloudWatch alarm and EC2 state-change events delivered through SNS and normalises them into one incident structure. |
| 2 | Fetch logs | `log_fetcher.py` | Reads the last 15 minutes of events from the CloudWatch Logs group of the affected instances. |
| 3 | Sanitise | `log_sanitizer.py` | Replaces IPv4 addresses, AWS access and secret keys, `password=`/`token=` values, e-mail addresses, internal hostnames and user home paths with placeholders. |
| 4 | Trim | `log_trimmer.py` | Keeps error-level lines first, then the most recent lines, capped at 4,000 characters. |
| 5 | Classify and analyse | `processor.py`, `groq_client.py`, `rca_prompt.py` | A rule-based pre-classifier labels the incident type; the model returns severity, confidence, root cause, affected components, immediate actions and a long-term fix as JSON. |
| 6 | Persist | `handler.py` | Writes the incident to DynamoDB with a 30-day expiry. |
| 7 | Notify | `notifier.py`, `discord_formatter.py` | Sends a colour-coded Discord embed. Low-confidence results are routed to a separate review channel when one is configured. |

### 4.2 Resilience design

- **Model fallback:** the analyser tries `openai/gpt-oss-120b`, then `openai/gpt-oss-20b`.
- **Safe fallback:** if every model fails, a predefined HIGH-severity "manual review required" analysis is used and the alert is still delivered.
- **Independent side effects:** a DynamoDB failure does not block the Discord alert.
- **Dead-letter queue:** unrecoverable errors are re-raised so the failed event lands in an SQS queue for inspection.
- **Cost guard:** a per-container token counter logs a warning above a configurable daily ceiling.

## 5. DevOps toolchain and practices

| Practice | Tool | How it is used in this project |
|----------|------|--------------------------------|
| Version control | Git, GitHub | Branch-based development and pull requests; history records every fix. |
| Continuous integration | GitHub Actions | On every push and pull request: lint, then the full test suite. |
| Static analysis | flake8 with bugbear | Enforces style and catches likely bugs before merge. |
| Automated testing | pytest, JSON fixtures | Unit, end-to-end (stubbed cloud) and performance tests that need no cloud account. |
| Quality gate for AI | Live model test in CI | Sends three realistic failure logs (out-of-memory, disk full, database refused) to the real model and checks that the analysis names the actual error. |
| Infrastructure as code | Terraform | Five reusable modules with remote state in S3 and default resource tags. |
| Continuous delivery | GitHub Actions, AWS CLI | On merge to main: `terraform apply`, package and deploy the Lambda, invoke a smoke test. |
| Observability | CloudWatch, X-Ray | Alarms, dashboard, log shipping from EC2 and tracing on the Lambda. |
| Security | IAM, log redaction, GitHub Secrets | Least-privilege roles, redaction before any external call, secrets injected as environment variables at deploy time. |
| AIOps | Groq-hosted LLM | Automated root-cause analysis. |

### 5.1 CI/CD pipeline (`.github/workflows/cicd.yml`)

```
push / pull request --> Lint --> Test --------------------------------> (stop on pull requests)
                                   |
                                   +--(main branch only)--> Terraform validate/plan/apply --> Deploy Lambda --> Smoke test
```

### 5.2 Infrastructure as code (`terraform/`)

| Module | Provisions |
|--------|------------|
| `networking` | VPC, public and private subnets, internet gateway, route tables, security groups |
| `iam` | EC2 instance role (SSM, CloudWatch agent) and Lambda execution role (scoped logs, DynamoDB, S3, SQS, SNS, X-Ray) |
| `ec2` | Launch template, Auto Scaling Group (1 to 3 instances) with scaling policies, Application Load Balancer, CloudWatch agent configuration |
| `alarms` | CloudWatch alarms: CPU high (above 80%), CPU low (below 20%), status-check failed, network-in high |
| `lambda` | Incident-processor function (Python 3.12, 512 MB, 300 s, X-Ray active), SNS trigger, dead-letter queue |
| environment `dev` | SNS topic, EventBridge rule for EC2 state changes, DynamoDB table, S3 log archive with lifecycle rules, log group, CloudWatch dashboard |

## 6. Security design

| Threat | Control |
|--------|---------|
| Secrets leaking to the AI provider | Sanitiser runs before any external call (eight redaction patterns). |
| Excessive permissions | Separate least-privilege IAM roles for EC2 and Lambda, resource-scoped where possible. |
| Public data exposure | S3 log archive is encrypted and blocks public access. |
| Credentials in source control | Secrets kept in GitHub Secrets and passed to Terraform as variables; `.env` files are git-ignored. |
| Runaway AI cost | Token counter with a warning ceiling; bounded prompt size. |

## 7. Testing

Twenty-six automated tests run without any cloud account:

| Area | Tests |
|------|-------|
| Event parsing (CloudWatch and EC2 events) | 3 |
| Log processing (redaction, trimming, classification) | 3 |
| Discord formatting and webhook routing | 4 |
| AI client (request format, model fallback) | 2 |
| AI prompt construction and optional live call | 2 |
| End-to-end handler with stubbed cloud services, including AI-failure fallback | 3 |
| Performance service-level checks (parsing, redaction, trimming, formatting, burst load) | 7 |
| Dashboard build from real pipeline output | 1 |
| Live AI quality gate (three failure scenarios) | 1 |

Continuous integration runs lint and this suite on every change; the live AI gate passes all three scenarios.

## 8. Project dashboard

`dashboard/index.html` is a single-file visual overview: architecture, an incident simulator, the AWS resource inventory,
the CI/CD flow and implementation status. The simulator runs the project's real parsing, redaction, trimming and
classification code on sample incidents; the AI text and Discord alert shown are sample output.

## 9. Implementation status

| Area | Status |
|------|--------|
| Pipeline code (parse, redact, trim, classify, analyse, notify, persist) | Implemented and covered by automated tests |
| Lint and test automation in CI | Implemented and passing |
| Live AI analysis | Verified in CI against the real service |
| Terraform modules | Implemented; not yet applied to an AWS account |
| Automated deployment (CD) | Implemented; runs on merge to the main branch |
| Real-time alarms end to end | Depends on deployment; demonstrated so far with simulated events |

All incident data shown in demonstrations and the dashboard is **simulated** from test fixtures. Live alarms from a running AWS
environment require the deployed stack.

## 10. Issues found and resolved during development

| Issue | Impact | Resolution |
|-------|--------|------------|
| `.gitignore` contained corrupted text that ignored every new file | New source files were never committed | File rewritten |
| Notification formatter module missing from the repository | Lambda failed on import | Module implemented and committed |
| CI referenced test files that did not exist | Pipeline failed on every push | Tests written |
| `requirements.txt` saved in the wrong text encoding | Dependency install failed | Replaced with a clean list |
| Two workflows both applied Terraform on the main branch | Competing deployments | Duplicate removed |
| Deploy script used a Windows-only temporary path | Failed on the Linux CI runner | Cross-platform path |
| The hosted model family originally configured was withdrawn | AI calls returned 404 | Switched to gpt-oss models with fallback |
| EC2 agent collected no logs and the log group did not exist | The AI would receive no evidence | Agent configuration and log group added |
| Alarms on the Auto Scaling Group read the Lambda's own log group | Analysis of the wrong logs | Parser selects the EC2 log group |

## 11. Limitations and future work

- The AI key and webhook URLs are Lambda environment variables and therefore appear in Terraform state; Secrets Manager is the intended replacement.
- The token ceiling is a per-container warning, not a hard limit; persisting the counter in DynamoDB would enforce it.
- Suggested actions are advisory; automatic remediation (restart, scale out) is future work.
- Incident history could feed a trend or recurrence report.

## 12. Technology summary

Python 3.12 · AWS Lambda, SNS, SQS, DynamoDB, S3, EventBridge, EC2 Auto Scaling, ALB, CloudWatch, X-Ray, IAM ·
Terraform · GitHub Actions · pytest · flake8 · Groq (gpt-oss models) · Discord webhooks
