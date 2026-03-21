# AIOps Sentinel — Security Hardening Guide

## Security Controls Implemented

### 1. IAM Least Privilege
**What:** Each role has ONLY the permissions it needs — nothing more.

**Why (interview answer):**
"The principle of least privilege limits blast radius. If our Lambda is
compromised, the attacker can only access aiops-* resources — not the
entire AWS account. We scope Bedrock to inference-profile/* only,
DynamoDB to the incidents table only, and S3 to the log-archive bucket only."

**Implementation:**
- Lambda role: 8 scoped statements, no wildcards on actions
- EC2 role: SSM + CloudWatch agent only
- Secrets Manager: only aiops/* secrets accessible

---

### 2. Secrets Manager (No hardcoded secrets)
**What:** Slack webhook, API keys stored in Secrets Manager.

**Why (interview answer):**
"Hardcoded secrets in environment variables are visible in Lambda console,
CloudFormation templates, and CI/CD logs. Secrets Manager encrypts at rest
with KMS, supports automatic rotation, and provides audit logs of every
access via CloudTrail. Cost is $0.40/secret/month — worth it."

**Implementation:**
- secrets.py fetches webhook at runtime
- In-memory caching reduces API calls
- Lambda IAM scoped to aiops/* secrets only

---

### 3. CloudTrail Logging
**What:** Every AWS API call is logged.

**Why (interview answer):**
"CloudTrail gives us a complete audit trail — who called what API, when,
from where. Essential for security investigations, compliance (SOC2, ISO27001),
and detecting credential abuse. We can detect if someone calls
bedrock:InvokeModel from an unexpected IP or role."

**Key events to monitor:**
- iam:CreateRole, iam:AttachRolePolicy
- bedrock:InvokeModel
- secretsmanager:GetSecretValue
- lambda:UpdateFunctionCode

---

### 4. S3 Encryption + Block Public Access
**What:** All log archives encrypted with AES-256. No public access.

**Why (interview answer):**
"Logs contain operational data that could reveal system architecture.
Server-side encryption ensures data at rest is protected. Block Public Access
prevents accidental exposure via bucket policies or ACLs."

**Implementation:**
- SSE-AES256 on all objects
- All four Block Public Access flags enabled
- Lifecycle policy: S3 → IA (30d) → Glacier (90d) → Delete (365d)

---

### 5. Lambda Dead Letter Queue (SQS)
**What:** Failed Lambda invocations go to SQS DLQ.

**Why (interview answer):**
"Without a DLQ, failed events are silently dropped. With DLQ, we retain
failed events for 14 days, can replay them after fixing bugs, and get
CloudWatch alarms on queue depth. This is critical for incident data
integrity — we never lose an alert."

---

### 6. X-Ray Tracing
**What:** Distributed tracing across Lambda → Bedrock → DynamoDB.

**Why (interview answer):**
"X-Ray gives us end-to-end visibility into our serverless pipeline.
We can see exactly where latency occurs — is Bedrock slow? Is DynamoDB
throttling? Is Slack timing out? Without tracing, debugging distributed
systems is guesswork."

---

### 7. VPC Security Groups
**What:** EC2 instances only accept traffic from ALB. No direct internet access.

**Why (interview answer):**
"Defense in depth — even if an attacker finds an EC2 instance, they cannot
reach it directly. All traffic must flow through the ALB, which provides
WAF integration, TLS termination, and access logging."

---

## Security Checklist

| Control                    | Status | Why It Matters              |
|----------------------------|--------|-----------------------------|
| IAM least privilege        | ✅     | Blast radius reduction      |
| No hardcoded secrets       | ✅     | Credential theft prevention |
| S3 block public access     | ✅     | Data exposure prevention    |
| S3 encryption at rest      | ✅     | Compliance requirement      |
| CloudTrail enabled         | ✅     | Audit trail                 |
| Lambda DLQ                 | ✅     | Data integrity              |
| X-Ray tracing              | ✅     | Observability               |
| VPC security groups        | ✅     | Network isolation           |
| Secrets Manager rotation   | ⚠️    | Configure in prod           |
| KMS customer managed keys  | ⚠️    | Add in prod                 |
| WAF on ALB                 | ⚠️    | Add in prod                 |
| GuardDuty                  | ⚠️    | Threat detection            |

---

## Interview Talking Points

**Q: How do you handle secrets in AWS Lambda?**
"We never put secrets in environment variables or code. We store them in
Secrets Manager and fetch at runtime using the Lambda execution role.
The role is scoped to only the specific secret ARN patterns we need.
We also cache the secret in Lambda memory to reduce API calls on warm starts."

**Q: How do you ensure least privilege in a serverless architecture?**
"We define a separate IAM role for each Lambda function. Each role has
inline policies scoped to specific resources — not * wildcards. For example,
our incident processor can only write to aiops-incidents* DynamoDB table,
read from aiops-log-archive* S3 bucket, and invoke apac.* Bedrock profiles.
We use CloudTrail to audit all IAM and API activity."

**Q: What happens if your Lambda fails?**
"Failed invocations go to an SQS Dead Letter Queue with 14-day retention.
We alert on DLQ depth via CloudWatch. After fixing the bug, we replay
events from the DLQ. X-Ray tracing tells us exactly where the failure
occurred in the pipeline."
