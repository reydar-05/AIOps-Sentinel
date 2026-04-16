# AIOps Sentinel — Risk Analysis & Mitigation

**Course:** 21IPE315P — Cloud Product and Platform Engineering
**Framework:** STRIDE Threat Model + Risk Matrix

---

## 1. Threat Model (STRIDE)

STRIDE categorizes threats into 6 types. Each is analyzed below for AIOps Sentinel.

| Category              | Definition                              |
|-----------------------|-----------------------------------------|
| **S**poofing          | Impersonating a legitimate user/service |
| **T**ampering         | Unauthorized modification of data       |
| **R**epudiation       | Denying an action occurred              |
| **I**nformation Disclosure | Exposing sensitive data            |
| **D**enial of Service | Making a service unavailable            |
| **E**levation of Privilege | Gaining unauthorized permissions   |

---

## 2. Risk Register

### Threat 1 — Spoofing: Unauthorized Lambda Invocation
| Attribute     | Detail                                                          |
|---------------|-----------------------------------------------------------------|
| **Threat**    | Attacker invokes Lambda directly using stolen AWS credentials   |
| **Component** | Lambda function `aiops-incident-processor-dev`                  |
| **Likelihood**| Medium — AWS credentials are common targets                     |
| **Impact**    | High — could trigger false alerts, exhaust Bedrock quota        |
| **Risk Level**| **HIGH**                                                        |
| **Mitigation**| Lambda invocation restricted to SNS topic ARN only (resource-based policy). IAM role does not allow direct `lambda:InvokeFunction` from external principals. CloudTrail logs all invocations. |
| **Residual**  | Low — SNS is the only authorized invoke source                  |

---

### Threat 2 — Tampering: Log Injection Attack
| Attribute     | Detail                                                          |
|---------------|-----------------------------------------------------------------|
| **Threat**    | Attacker writes malicious content to CloudWatch Logs that manipulates the AI prompt (prompt injection) |
| **Component** | `log_fetcher.py` → `log_sanitizer.py` → `rca_prompt.py`        |
| **Likelihood**| Low — requires write access to CloudWatch Logs                  |
| **Impact**    | Medium — could cause misleading RCA output                      |
| **Risk Level**| **MEDIUM**                                                      |
| **Mitigation**| Log sanitizer strips control characters and dangerous patterns. Prompt template uses strict JSON output schema with field validation. AI response validated before use — malformed JSON rejected. |
| **Residual**  | Low — structured prompt limits injection surface                |

---

### Threat 3 — Repudiation: No Audit Trail for AI Decisions
| Attribute     | Detail                                                          |
|---------------|-----------------------------------------------------------------|
| **Threat**    | AI makes an incorrect incident classification; no record of the AI decision exists for audit |
| **Component** | `bedrock_client.py` → DynamoDB                                  |
| **Likelihood**| High — AI errors are expected                                   |
| **Impact**    | Medium — compliance risk, cannot investigate false positives    |
| **Risk Level**| **MEDIUM**                                                      |
| **Mitigation**| Every incident + full AI analysis JSON stored in DynamoDB with TTL 30 days. `confidence` and `severity_reason` fields preserved. CloudTrail logs every `bedrock:InvokeModel` API call with timestamp, model ID, and IAM identity. |
| **Residual**  | Low — complete audit trail from alarm to AI decision            |

---

### Threat 4 — Information Disclosure: Log Exfiltration to External AI
| Attribute     | Detail                                                          |
|---------------|-----------------------------------------------------------------|
| **Threat**    | Internal infrastructure details (IPs, credentials, internal hostnames) sent to third-party AI APIs (OpenRouter fallback) |
| **Component** | `groq_client.py` — OpenRouter fallback                          |
| **Likelihood**| Medium — OpenRouter fallback is invoked when Bedrock fails      |
| **Impact**    | High — internal network topology, credentials, emails exposed   |
| **Risk Level**| **HIGH**                                                        |
| **Mitigation**| Log sanitizer runs BEFORE any AI invocation. 8 regex patterns redact: IPv4 addresses, AWS access keys, AWS secret keys, passwords, tokens, emails, VPC DNS names, local paths. Both Bedrock and OpenRouter receive only sanitized logs. |
| **Residual**  | Low — sanitization is the first processing step, no bypass path |

---

### Threat 5 — Information Disclosure: Slack Webhook Exposure
| Attribute     | Detail                                                          |
|---------------|-----------------------------------------------------------------|
| **Threat**    | Slack webhook URL hardcoded in code or Lambda env vars; exposed in CI/CD logs or GitHub |
| **Component** | `notifier.py`, Lambda environment variables                     |
| **Likelihood**| High without controls — env vars visible in Lambda console      |
| **Impact**    | High — attacker sends spam/phishing messages to team channel    |
| **Risk Level**| **HIGH**                                                        |
| **Mitigation**| Webhook stored in AWS Secrets Manager (`aiops/slack/webhook`). Fetched at runtime using Lambda execution role. IAM scoped to `aiops/*` secrets only. Not present in any code file or environment variable in production. `.gitignore` excludes `.env` files. |
| **Residual**  | Low — no secret in code, logs, or CI/CD                         |

---

### Threat 6 — Denial of Service: Bedrock Quota Exhaustion
| Attribute     | Detail                                                          |
|---------------|-----------------------------------------------------------------|
| **Threat**    | Mass CloudWatch alarms (e.g., deployment failure across 100 instances) flood Lambda and exhaust Bedrock rate limits |
| **Component** | `bedrock_client.py`, Lambda concurrency                         |
| **Likelihood**| Medium — common during deployments                              |
| **Impact**    | Medium — AI analysis delayed, but system continues              |
| **Risk Level**| **MEDIUM**                                                      |
| **Mitigation**| Bedrock client has 3-attempt exponential retry with jitter. OpenRouter fallback activates on throttle errors (`ThrottlingException`). SQS DLQ retains unprocessed events for up to 14 days. Lambda reserved concurrency limits blast radius. |
| **Residual**  | Low — multi-layer retry + fallback prevents total outage        |

---

### Threat 7 — Denial of Service: S3 Log Archive Abuse
| Attribute     | Detail                                                          |
|---------------|-----------------------------------------------------------------|
| **Threat**    | Unexpected log volume fills S3 bucket, causing runaway storage costs |
| **Component** | S3 bucket `aiops-log-archive-dev`                               |
| **Likelihood**| Low                                                             |
| **Impact**    | Medium — financial impact, not service outage                   |
| **Risk Level**| **LOW**                                                         |
| **Mitigation**| S3 lifecycle policy: STANDARD → IA (30d) → GLACIER (90d) → DELETE (365d). S3 Block Public Access prevents external writes. IAM scoped write permission for Lambda only. |
| **Residual**  | Very low — lifecycle keeps costs bounded                        |

---

### Threat 8 — Elevation of Privilege: Lambda IAM Role Abuse
| Attribute     | Detail                                                          |
|---------------|-----------------------------------------------------------------|
| **Threat**    | Compromised Lambda execution role used to access other AWS services beyond its purpose |
| **Component** | IAM role `aiops-lambda-role-dev`                                |
| **Likelihood**| Low — requires Lambda code execution vulnerability              |
| **Impact**    | High — could compromise other AWS resources                     |
| **Risk Level**| **MEDIUM**                                                      |
| **Mitigation**| Role scoped with 8 least-privilege statements: DynamoDB only for `aiops-incidents*` tables, S3 only for `aiops-log-archive*`, Secrets Manager only for `aiops/*`, Bedrock only `inference-profile/*`, no wildcard resource permissions. EC2 can only reboot/start (no delete/create). |
| **Residual**  | Low — blast radius limited to `aiops-*` named resources only   |

---

## 3. Risk Matrix

```
      I M P A C T
      Low    Medium    High
H  ┌────────┬─────────┬──────────┐
I  │        │  [T4]   │  [T5]    │
G  │  [T7]  │  [T3]   │  [T1]    │
H  │        │  [T6]   │          │
   ├────────┼─────────┼──────────┤
M  │        │  [T2]   │  [T8]    │
E  │        │         │          │
D  │        │         │          │
   ├────────┼─────────┼──────────┤
L  │        │         │          │
O  │        │         │          │
W  │        │         │          │
   └────────┴─────────┴──────────┘
L I K E L I H O O D ↑
```

| Ref | Threat                           | Risk Level | Status     |
|-----|----------------------------------|------------|------------|
| T1  | Unauthorized Lambda invocation   | HIGH       | Mitigated  |
| T2  | Log injection / prompt injection | MEDIUM     | Mitigated  |
| T3  | No AI audit trail                | MEDIUM     | Mitigated  |
| T4  | Log exfiltration to external AI  | HIGH       | Mitigated  |
| T5  | Slack webhook exposure           | HIGH       | Mitigated  |
| T6  | Bedrock quota exhaustion         | MEDIUM     | Mitigated  |
| T7  | S3 log archive cost abuse        | LOW        | Mitigated  |
| T8  | Lambda IAM role privilege abuse  | MEDIUM     | Mitigated  |

**All identified threats have active mitigations. No unmitigated HIGH risks remain.**

---

## 4. Security Controls Summary

| Control                        | Threats Addressed | Implementation                      |
|--------------------------------|-------------------|-------------------------------------|
| IAM Least Privilege            | T1, T8            | `terraform/modules/iam/main.tf`     |
| AWS Secrets Manager            | T5                | `lambda/notification_handler/secrets.py` |
| Log Sanitization (8 patterns)  | T2, T4            | `lambda/log_processor/log_sanitizer.py` |
| DynamoDB Incident Store        | T3                | `terraform/environments/dev/main.tf`|
| CloudTrail API Logging         | T1, T3            | `docs/security_hardening.md`        |
| S3 Encryption + Lifecycle      | T4, T7            | `terraform/environments/dev/main.tf`|
| Lambda DLQ (SQS)               | T6                | `terraform/modules/lambda/main.tf`  |
| Bedrock Retry + Fallback       | T6                | `lambda/ai_analyzer/bedrock_client.py` |
| VPC Network Isolation          | T1, T8            | `terraform/modules/networking/`     |
| X-Ray Distributed Tracing      | T3, T6            | `terraform/modules/lambda/main.tf`  |

---

## 5. Compliance Posture

| Standard       | Relevant Controls                                | Status       |
|----------------|--------------------------------------------------|--------------|
| AWS Well-Architected (Security Pillar) | IAM, Secrets Manager, VPC, encryption | ✅ Implemented |
| OWASP Cloud Top 10 | No hardcoded secrets, log sanitization, IAM scoping | ✅ Addressed |
| Data Privacy   | PII redaction in logs (emails, IPs) before AI    | ✅ Implemented |
| Audit Trail    | DynamoDB + CloudTrail for all decisions          | ✅ Implemented |
| Encryption at Rest | S3 AES-256, DynamoDB default, Secrets Manager KMS | ✅ Implemented |
| Encryption in Transit | HTTPS for Slack, Bedrock, Secrets Manager APIs | ✅ Implemented |

---

## 6. Interview Talking Points

**Q: What is your biggest security risk and how did you address it?**
"The biggest risk was log exfiltration — our system reads CloudWatch logs
(which can contain IPs, credentials, email addresses) and sends them to an
external AI API (OpenRouter fallback). We addressed this with a mandatory
log sanitization step that runs 8 regex patterns before ANY AI invocation.
The sanitizer redacts AWS access keys, IPv4 addresses, passwords, emails,
and internal DNS names. Both Bedrock and OpenRouter receive only sanitized
content. This was a deliberate, security-first design decision."

**Q: How do you handle secrets in this system?**
"Zero secrets in code, environment variables, or CI/CD logs. The Slack webhook
lives in AWS Secrets Manager, fetched at Lambda runtime using the execution role.
The IAM policy scopes access to `aiops/*` secrets only — if the Lambda is
compromised, the attacker cannot read any other organization's secrets."

**Q: What would you improve for production hardening?**
"Three additions for production: (1) Enable KMS customer-managed keys on S3 and
DynamoDB instead of AWS-managed keys — gives key rotation control. (2) Add WAF
on the ALB to block common web attack patterns. (3) Enable GuardDuty for
ML-based threat detection — it would catch anomalous Bedrock API call patterns
that indicate credential compromise."
