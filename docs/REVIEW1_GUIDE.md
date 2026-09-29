# AIOps Sentinel: Review 1 Guide

**Module 1: Source control, CI and testing** (course: Essentials in Cloud and DevOps)

This file has two parts: **A. Documentation** (what to explain) and **B. Run-and-show checklist** (what to type and open).

---

## A. Documentation

### A1. The problem and the idea

On-call engineers receive a bare alarm such as "CPU above 80%" and must search through logs to learn why.
**AIOps Sentinel automates that first triage step.** When an alarm fires, it collects the logs, removes secrets,
asks an AI for the root cause, saves the incident and sends an alert to Discord.

### A2. How it works (7 stages)

```
CloudWatch alarm / EC2 event -> SNS -> Lambda
   1 Parse the event            event_parser.py
   2 Fetch 15 min of logs       log_fetcher.py
   3 Redact secrets             log_sanitizer.py   (IPs, keys, passwords, e-mails, internal hosts)
   4 Trim to 4,000 chars        log_trimmer.py     (keeps error lines, drops noise)
   5 AI root-cause analysis     groq_client.py     (gpt-oss-120b, fallback gpt-oss-20b)
   6 Save to DynamoDB           handler.py         (30-day TTL)
   7 Alert on Discord           notifier.py        (LOW confidence goes to a review channel)
```

Failure handling: if the AI is down, a safe fallback analysis is used and the alert is still sent. A DynamoDB failure never blocks the alert.

### A3. The three modules

| Module | Focus | Tools | State |
|--------|-------|-------|-------|
| **1. Source control, CI and testing** (this review) | Working app with automated quality gates | Git, GitHub, GitHub Actions, flake8, pytest, Groq LLM | Complete |
| 2. Infrastructure as Code and cloud | Reproducible AWS stack, automated deployment | Terraform, AWS, CD jobs | Written, not yet deployed |
| 3. Monitoring, security and AIOps | Real alarms end to end, hardening | CloudWatch, X-Ray, IAM, Secrets Manager | Written, not yet verified live |

### A4. DevOps tools in Module 1, and why

| Tool | Purpose | Evidence |
|------|---------|----------|
| **Git and GitHub** | Version control, branch and pull-request workflow | Pull request #1, commit history |
| **GitHub Actions** | Continuous integration: every push and PR is linted and tested automatically | `.github/workflows/cicd.yml`, Checks tab |
| **flake8 (+ bugbear)** | Static analysis catches errors and bad patterns before merge | "Lint Python Code" job |
| **pytest** | 26 automated tests, all runnable offline with no cloud account | `tests/` |
| **Groq LLM** | AIOps: automated root-cause analysis. A live test runs in CI | "PASS: OOM / DISK / DB" in the test log |

The deploy stages (Terraform apply, Lambda deploy, smoke test) exist in the workflow but run only after a merge to `main`. They are skipped on the pull request by design and belong to Module 2.

### A5. Simulated vs real

- **Simulated:** the incidents. Alarm events and logs come from `tests/fixtures` and `scripts/demo.py`. No AWS account is running yet.
- **Real:** the CI runs on GitHub, the code that parses, redacts, trims and classifies, and the live Groq call in CI.
- **Real-time alerts from AWS** arrive with Modules 2 and 3.

### A6. Problems found and fixed during the audit

| Problem | Effect | Fix |
|---------|--------|-----|
| `.gitignore` ended with corrupted text that ignored every new file | New files were never committed | Rewrote the file |
| `discord_formatter.py` was missing | The Lambda failed on import | Written and committed |
| CI ran test files that did not exist | CI failed on every push | Added the tests |
| `requirements.txt` was saved as UTF-16 | `pip install` failed | Clean UTF-8 list |
| Two workflows both ran `terraform apply` on main | Racing deployments | Removed the duplicate |
| Deploy script used a Windows-only temp path | Failed on the Linux runner | Cross-platform temp folder |
| Groq no longer offered the Llama models on the account | AI test failed with 404 | Switched to gpt-oss-120b, fallback 20b |
| EC2 log agent shipped no logs | AI received no logs | Agent config and log group in Terraform (verified in Module 2) |
| ASG alarms read the Lambda's own log group | Analysis of the wrong logs | Parser uses the EC2 log group |

### A7. Likely questions and short answers

- **Why redact before the AI?** Logs can contain passwords, keys and IPs. Nothing sensitive should leave the account, so redaction runs before any external call.
- **What if the AI is down?** A fallback analysis (HIGH severity, "manual review") is used and the alert still goes out. Model fallback (120b, then 20b) comes first.
- **How do you know it works without AWS?** 26 offline tests plus a stubbed end-to-end test of the Lambda handler, run automatically in CI.
- **Why is deployment skipped?** It needs AWS credentials and runs only on `main`. That is Module 2.
- **What is not built yet?** Deployed infrastructure, live alarms, secrets in Secrets Manager, automatic remediation.

---

## B. Run-and-show checklist

### B1. One-time setup (do this before the review, on your laptop)

Windows PowerShell:

```powershell
cd path\to\AIOps-Sentinel
git fetch origin
git checkout claude/practical-goldberg-r6m7ru
git pull
python --version                     # 3.11 or newer
pip install -r requirements.txt
```

Optional, for the live AI stage. Paste your real key; never share it or commit it:

```powershell
$env:GROQ_API_KEY = "gsk_PASTE_FULL_KEY_HERE"
$env:DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/..."   # optional
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
```

Environment variables last only for that PowerShell window, so run the demo from the same window.

### B2. What to show, in order (about 8 minutes)

| # | Show | How | What the audience should see |
|---|------|-----|------------------------------|
| 1 | **The idea** | Dashboard **Overview** tab, or the diagram in section A2 | Alarm to alert in 7 stages |
| 2 | **GitHub** | Repository page, then pull request #1 | Branch workflow, commit history |
| 3 | **CI pipeline** | PR #1, **Checks** tab | Lint and Unit Tests green; Terraform and Deploy skipped by design |
| 4 | **CI test log** | Open the "Run Unit Tests" job | `PASS: OOM`, `PASS: DISK`, `PASS: DB` from the live AI test |
| 5 | **Live demo** | `python scripts/demo.py` | 5 stages: raw logs with secrets, redacted logs, AI analysis, Discord alert |
| 6 | **Tests locally** | `python -m pytest tests -q` | `26 passed` |
| 7 | **Dashboard** | `python scripts/build_dashboard.py` | Opens in the browser; use the **Incident simulator** tab |
| 8 | **Wrap-up** | Sections A3 and A6 | What was fixed; what Modules 2 and 3 add |

### B3. Commands to run live

```powershell
python scripts/demo.py
python -m pytest tests -q
python scripts/build_dashboard.py
```

Expected results:

- **demo.py:** five headed stages. With `GROQ_API_KEY` set, stage 4 prints a live analysis; without it, a labelled canned response. With `DISCORD_WEBHOOK_URL` set, stage 5 posts to Discord.
- **pytest:** `26 passed`.
- **build_dashboard.py:** prints "Dashboard written to ...\dashboard\index.html" and opens your browser. You can also double-click `dashboard/index.html`.

### B4. Dashboard tour (2 minutes)

1. **Overview:** architecture diagram and module table.
2. **Incident simulator:** pick "High CPU from memory leak", press **Replay stage by stage**. Point at stage 2 (secrets highlighted in red) and stage 3 (replaced with `[..._REDACTED]`). Say that the AI text and the alert are sample output.
3. **AWS infrastructure:** what Terraform will create in Module 2.
4. **DevOps pipeline:** the CI/CD flow and the tools by module.
5. **Status and roadmap:** honest state of each module.

### B5. If something goes wrong

| Symptom | Fix |
|---------|-----|
| `pip` not found | `python -m pip install -r requirements.txt` |
| Demo AI stage errors | Run without a key; it uses the canned response. Check `$env:GROQ_API_KEY` is set in this window |
| `Invalid API Key` | Key mistyped or truncated; create a new key at console.groq.com |
| `model_not_found` (404) | List your models: `GET https://api.groq.com/openai/v1/models`, then set `$env:GROQ_MODELS = "modelA,modelB"` |
| "Connection closed" in PowerShell | Run the TLS 1.2 line from B1; try a phone hotspot |
| Tests fail on import | Run from the repo root, on the PR branch, after `git pull` |
| Dashboard fonts look plain | Offline; fonts fall back to system fonts, everything still works |

### B6. Rehearsal checklist

- [ ] `git pull` on the PR branch
- [ ] `pip install -r requirements.txt` succeeds
- [ ] `python scripts/demo.py` runs (with and without the key)
- [ ] `python -m pytest tests -q` shows 26 passed
- [ ] `python scripts/build_dashboard.py` opens the dashboard
- [ ] PR #1 Checks tab is green
- [ ] Wi-Fi tested; hotspot ready as a backup
- [ ] Keys are set only in the terminal window, not in any file
