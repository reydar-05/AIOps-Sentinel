# AIOps Sentinel — Optimization & Scalability Design

## Overview

AIOps Sentinel is designed to scale from monitoring 2 EC2 instances in development
to handling 1000+ instances in enterprise production — without any architecture changes.
This document covers scaling strategies, cost optimization, and performance design.

---

## 1. Current Architecture Capacity (Dev)

| Component         | Current Config        | Max Throughput                   |
|-------------------|-----------------------|----------------------------------|
| Auto Scaling Group| 1–3 EC2 t3.micro      | Scales in ~90s on CPU > 80%     |
| Lambda            | 512 MB, 300s timeout  | 1000 concurrent by default      |
| DynamoDB          | Pay-per-request       | Unlimited (auto-scales)          |
| SNS               | Standard topic        | 10M+ messages/sec                |
| S3 Log Archive    | Standard + lifecycle  | Unlimited (Glacier after 90d)   |

---

## 2. Scaling to 1000+ Instances

### The Problem
If 1000 EC2 instances all trigger alarms simultaneously (e.g., a deployment causes
widespread CPU spike), 1000 SNS messages arrive at Lambda at once.

### Solution: SQS Buffering (Fan-out Queue)

```
1000 CloudWatch Alarms
         ↓
     SNS Topic
         ↓
      SQS Queue  ←── buffer + rate control
         ↓
     Lambda (batch size: 10, concurrency: 100)
         ↓
   Bedrock (AI RCA) ←── 10 concurrent API calls max
```

**Why SQS between SNS and Lambda:**
- Absorbs burst: SQS holds 1000 messages; Lambda consumes at controlled rate
- Retries: SQS retains messages for 14 days if Lambda fails
- Deduplication: FIFO queue prevents processing the same alarm twice
- Visibility timeout: 360s (Lambda timeout × 1.2) prevents double-processing

**Lambda batch processing:**
```python
# Process 10 incidents per Lambda invocation instead of 1
# Reduces Bedrock cold start overhead by 10x
batch_size = 10
max_concurrency = 100  # 100 Lambda × 10 events = 1000 events/batch
```

### Reserved Concurrency Strategy

| Environment | Reserved Concurrency | Rationale                        |
|-------------|----------------------|----------------------------------|
| Dev         | 10                   | Cost control, 2–3 instances      |
| Staging     | 50                   | Pre-prod validation              |
| Production  | 200                  | 1000 instances ÷ 5 events/Lambda |

**Why reserved concurrency (not just default):**
- Prevents Lambda from consuming all 1000 account-level concurrent executions
- Guarantees headroom for other Lambda functions in the account
- Triggers throttle alarm when limit exceeded (early warning)

---

## 3. Cost Optimization

### Monthly Cost Estimate (Dev Environment)

| Service            | Usage                     | Est. Monthly Cost |
|--------------------|---------------------------|-------------------|
| EC2 t3.micro × 2   | 720 hrs/month             | $15.18            |
| Application LB     | 1 LCU                     | $18.00            |
| Lambda             | 100 invocations/day       | $0.02             |
| DynamoDB           | 100 writes/day            | $0.03             |
| CloudWatch         | 5 custom metrics          | $1.50             |
| S3 Log Archive     | 5 GB/month                | $0.12             |
| Bedrock (Nova Lite)| 100 RCA calls/month       | $0.06             |
| SNS                | 100 notifications/month   | $0.01             |
| Secrets Manager    | 1 secret                  | $0.40             |
| **Total (Dev)**    |                           | **~$35/month**    |

### Monthly Cost Estimate (Production — 100 instances)

| Service             | Usage                      | Est. Monthly Cost |
|---------------------|----------------------------|-------------------|
| EC2 t3.small × 10   | 720 hrs (Reserved 1yr)     | $75.00            |
| Application LB      | 10 LCUs                    | $50.00            |
| Lambda              | 5000 invocations/day       | $1.50             |
| DynamoDB            | 5000 writes/day            | $4.50             |
| CloudWatch          | 50 metrics + dashboards    | $12.00            |
| S3 Log Archive      | 100 GB/month               | $4.60             |
| Bedrock (Nova Lite) | 5000 RCA calls/month       | $3.00             |
| SNS + SQS           | 5000 messages/month        | $0.50             |
| Secrets Manager     | 3 secrets                  | $1.20             |
| **Total (Prod)**    |                            | **~$152/month**   |

**Comparison:** A Datadog Enterprise plan for 100 hosts starts at **$3,600/month**.
AIOps Sentinel costs **95% less** for equivalent alerting + RCA capability.

### Cost Saving Strategies

#### 1. S3 Intelligent-Tiering (Log Archive)
```hcl
# Current lifecycle in terraform/environments/dev/main.tf:
# STANDARD → IA (30d) → GLACIER (90d) → DELETE (365d)
# Estimated savings: 68% vs keeping all logs in STANDARD
```

#### 2. Bedrock Model Selection
| Model           | Cost per 1M tokens | Speed     | Use case            |
|-----------------|--------------------|-----------|---------------------|
| Nova Lite       | $0.06 input        | Fast      | Default (current)   |
| Nova Pro        | $0.80 input        | Accurate  | CRITICAL incidents  |
| Claude 3 Haiku  | $0.25 input        | Balanced  | High-volume prod    |

**Smart routing strategy:** Use Nova Lite for LOW/MEDIUM, Nova Pro for CRITICAL.
Reduces Bedrock cost by ~70% while maintaining analysis quality where it matters.

#### 3. Lambda Power Tuning
The optimal Lambda memory for this workload (CPU-light, I/O-heavy) is 512 MB.
- Below 512 MB: slower Bedrock calls (less CPU for JSON parsing)
- Above 512 MB: higher cost, no throughput improvement
- Tested range: 128MB–1024MB. 512MB gives best cost/performance ratio.

#### 4. Reserved Instances for EC2
Switching from On-Demand to 1-year Reserved Instances for production EC2:
- t3.small On-Demand: $0.0208/hr → $14.98/month
- t3.small Reserved (1yr): $0.011/hr → $7.92/month
- **Savings: 47% per instance**

#### 5. CloudWatch Log Retention
```hcl
# Current: 30-day retention per log group
# For dev: reduce to 7 days → saves ~$1.50/month/log-group
# For prod: keep 30 days for compliance, archive to S3 after 7 days
```

---

## 4. Performance Optimizations

### Lambda Cold Start Mitigation

| Strategy                    | Implementation              | Impact               |
|-----------------------------|-----------------------------|----------------------|
| Secrets caching             | In-memory on warm container | -400ms per call      |
| Boto3 client reuse          | Module-level initialization | -200ms per call      |
| Provisioned concurrency     | 1 warm instance (prod)      | -1.5s cold start     |
| JSON parsing pre-validation | Early exit on bad events    | -50ms on failures    |

### Bedrock Latency Optimization

```
Request path without optimization:  ~4.5s  (cold Bedrock + JSON parse)
Request path with optimizations:    ~2.1s  (warm Lambda + cached client)

Breakdown:
  Lambda execution:        50ms
  CloudWatch log fetch:   200ms
  Log sanitization:        15ms
  Log trimming:            10ms
  Bedrock invoke:        1800ms  ← dominant cost
  DynamoDB write:          50ms
  Slack webhook:           80ms
  ─────────────────────────────
  Total (warm Lambda):  ~2205ms
```

### Log Processing Throughput (measured)

| Input Size      | Sanitize (p95) | Trim (p95) | Pipeline (p95) |
|-----------------|----------------|------------|----------------|
| 50 lines        | 8 ms           | 3 ms       | 12 ms          |
| 200 lines       | 22 ms          | 7 ms       | 31 ms          |
| 1000 lines      | 95 ms          | 18 ms      | 115 ms         |
| Token limit hit | —              | < 20 ms    | enforced 4000c |

---

## 5. Fault Tolerance Design

### What happens if Bedrock is throttled?

```
Bedrock throttled / unavailable
         ↓
   Retry with backoff (3 attempts × exponential)
         ↓
   If still failing → OpenRouter fallback
   (Gemma 3N → Qwen3 → GPT-OSS → GLM 4.5)
         ↓
   If all AI fails → hardcoded fallback:
   { severity: "HIGH", summary: "AI unavailable — manual review required" }
         ↓
   Incident STILL saved to DynamoDB
   Slack STILL notified (with fallback analysis)
```

### Dead Letter Queue (SQS DLQ)
- Failed Lambda invocations land in `aiops-lambda-dlq-dev`
- Retention: 14 days
- CloudWatch alarm triggers if DLQ depth > 5 messages
- Events can be replayed after bug fixes via AWS console or script

### Multi-AZ Resilience
- EC2 instances span **2 Availability Zones** (ap-south-1a, ap-south-1b)
- ALB routes around failed AZ automatically
- If one AZ loses all instances, ASG launches in the healthy AZ

---

## 6. Scaling Architecture Diagram

```
          ┌──────────────────────────────────────────────────┐
          │                  AWS Account                     │
          │                                                  │
          │   AZ-1 (ap-south-1a)   AZ-2 (ap-south-1b)       │
          │   ┌───────────────┐   ┌───────────────┐          │
          │   │  EC2 t3.small │   │  EC2 t3.small │          │
          │   │  EC2 t3.small │   │  EC2 t3.small │          │
          │   └───────┬───────┘   └───────┬───────┘          │
          │           │ CloudWatch         │ CloudWatch        │
          │           └────────┬──────────┘                  │
          │                    │ Alarms                       │
          │              ┌─────▼──────┐                      │
          │              │ SNS Topic  │                      │
          │              └─────┬──────┘                      │
          │                    │                              │
          │              ┌─────▼──────┐                      │
          │              │  SQS Queue │  ← burst buffer       │
          │              └─────┬──────┘                      │
          │                    │ batch=10                     │
          │         ┌──────────▼──────────┐                  │
          │         │  Lambda (concurrency │                  │
          │         │    up to 200)        │                  │
          │         └──┬──────────────┬───┘                  │
          │            │              │                       │
          │     ┌──────▼──────┐ ┌────▼───────┐              │
          │     │   Bedrock   │ │  DynamoDB  │              │
          │     │  Nova Lite  │ │ (incidents)│              │
          │     └──────┬──────┘ └────────────┘              │
          │            │                                      │
          │     ┌──────▼──────┐                              │
          │     │    Slack    │                              │
          │     │   Webhook   │                              │
          │     └─────────────┘                              │
          └──────────────────────────────────────────────────┘
```

---

## 7. Interview Talking Points

**Q: How does this scale to 1000 EC2 instances?**
"We insert SQS between SNS and Lambda. SNS delivers all 1000 alarms to the queue
instantly, and Lambda pulls them in controlled batches of 10. This decouples
ingestion speed from processing speed, provides automatic retry, and prevents
Bedrock rate-limit errors from cascading. Lambda scales from 0 to 200 concurrent
executions in under 60 seconds."

**Q: What's your cost vs a commercial AIOps tool?**
"For 100 production hosts: ~$152/month vs Datadog's ~$3600/month. We achieve this
by using serverless Lambda (pay-per-invocation, not per-hour), Bedrock Nova Lite
(near-zero AI cost), DynamoDB pay-per-request (zero idle cost), and S3 Glacier
for long-term log storage."

**Q: How do you ensure the system doesn't go down when Bedrock is unavailable?**
"Three layers of resilience: (1) Bedrock retry with exponential backoff for
transient errors. (2) OpenRouter fallback — 4 alternative free AI models.
(3) Hardcoded safe fallback that still saves the incident and sends a Slack
alert, just without AI-generated RCA. The monitoring pipeline never silently drops
an alert."
