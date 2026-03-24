# ============================================================
# AIOps Sentinel — CloudWatch Dashboard
# Phase 9: Monitoring Dashboard
# ============================================================

resource "aws_cloudwatch_dashboard" "aiops_main" {
  dashboard_name = "AIOps-Sentinel-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [

      # ── Row 1: Title banner ────────────────────────────────
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 2
        properties = {
          markdown = "# 🛡️ AIOps Sentinel — Live Infrastructure Intelligence\n**Environment:** `${upper(var.environment)}` &nbsp;|&nbsp; **Region:** `${var.aws_region}` &nbsp;|&nbsp; **Account:** `${var.aws_account_id}` &nbsp;|&nbsp; Powered by AI-driven RCA"
        }
      },

      # ── Row 2: CPU gauge ───────────────────────────────────
      {
        type   = "metric"
        x      = 0
        y      = 2
        width  = 6
        height = 6
        properties = {
          title   = "CPU Utilization"
          view    = "gauge"
          region  = var.aws_region
          period  = 60
          metrics = [
            ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", "aiops-asg-${var.environment}", { "stat" = "Average", "label" = "CPU %" }]
          ]
          yAxis = { "left" = { "min" = 0, "max" = 100 } }
          annotations = {
            horizontal = [
              { "value" = var.cpu_alarm_threshold, "label" = "Alarm", "color" = "#d62728", "fill" = "above" }
            ]
          }
        }
      },

      # ── Row 2: Memory gauge ────────────────────────────────
      {
        type   = "metric"
        x      = 6
        y      = 2
        width  = 6
        height = 6
        properties = {
          title   = "Memory Utilization"
          view    = "gauge"
          region  = var.aws_region
          period  = 60
          metrics = [
            ["CWAgent", "mem_used_percent", "AutoScalingGroupName", "aiops-asg-${var.environment}", { "stat" = "Average", "label" = "Memory %" }]
          ]
          yAxis = { "left" = { "min" = 0, "max" = 100 } }
          annotations = {
            horizontal = [
              { "value" = 85, "label" = "Threshold", "color" = "#d62728", "fill" = "above" }
            ]
          }
        }
      },

      # ── Row 2: KPI — Total Incidents ──────────────────────
      {
        type   = "metric"
        x      = 12
        y      = 2
        width  = 4
        height = 3
        properties = {
          title      = "Incidents Today"
          view       = "singleValue"
          sparkline  = true
          region     = var.aws_region
          period     = 86400
          annotations = { "horizontal" = [] }
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", "aiops-incident-processor-${var.environment}", { "stat" = "Sum", "label" = "Total" }]
          ]
        }
      },

      # ── Row 2: KPI — Failures ─────────────────────────────
      {
        type   = "metric"
        x      = 16
        y      = 2
        width  = 4
        height = 3
        properties = {
          title      = "Pipeline Failures"
          view       = "singleValue"
          sparkline  = true
          region     = var.aws_region
          period     = 86400
          annotations = { "horizontal" = [] }
          metrics = [
            ["AWS/Lambda", "Errors", "FunctionName", "aiops-incident-processor-${var.environment}", { "stat" = "Sum", "id" = "m1", "visible" = false }],
            [{ "expression" = "FILL(m1, 0)", "label" = "Failures", "color" = "#d62728" }]
          ]
        }
      },

      # ── Row 2: KPI — Incidents Saved ──────────────────────
      {
        type   = "metric"
        x      = 20
        y      = 2
        width  = 4
        height = 3
        properties = {
          title      = "Incidents Saved"
          view       = "singleValue"
          sparkline  = true
          region     = var.aws_region
          period     = 86400
          annotations = { "horizontal" = [] }
          metrics = [
            ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", "aiops-incidents-${var.environment}", "Operation", "PutItem", { "stat" = "SampleCount", "id" = "m1", "visible" = false }],
            [{ "expression" = "FILL(m1, 0)", "label" = "Saved", "color" = "#2ca02c" }]
          ]
        }
      },

      # ── Row 2 bottom: Avg Latency KPI ─────────────────────
      {
        type   = "metric"
        x      = 12
        y      = 5
        width  = 12
        height = 3
        properties = {
          title      = "Avg Lambda Duration"
          view       = "singleValue"
          sparkline  = true
          region     = var.aws_region
          period     = 300
          annotations = { "horizontal" = [] }
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", "aiops-incident-processor-${var.environment}", { "stat" = "Average", "label" = "Avg ms" }],
            ["AWS/Lambda", "Duration", "FunctionName", "aiops-incident-processor-${var.environment}", { "stat" = "p99", "label" = "P99 ms", "color" = "#d62728" }]
          ]
        }
      },

      # ── Row 3: CPU trend (full width) ─────────────────────
      {
        type   = "metric"
        x      = 0
        y      = 8
        width  = 12
        height = 6
        properties = {
          title   = "CPU Utilization — Trend"
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          period  = 60
          metrics = [
            ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", "aiops-asg-${var.environment}", { "label" = "Avg CPU %", "stat" = "Average", "color" = "#ff7f0e" }],
            ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", "aiops-asg-${var.environment}", { "label" = "Max CPU %", "stat" = "Maximum", "color" = "#d62728" }]
          ]
          annotations = {
            horizontal = [
              { "value" = var.cpu_alarm_threshold, "label" = "Alarm threshold", "color" = "#d62728", "fill" = "above" }
            ]
          }
          yAxis = { "left" = { "min" = 0, "max" = 100 } }
        }
      },

      # ── Row 3: Lambda Error Rate ───────────────────────────
      {
        type   = "metric"
        x      = 12
        y      = 8
        width  = 12
        height = 6
        properties = {
          title   = "Lambda Pipeline — Invocations vs Errors"
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          period  = 60
          annotations = { "horizontal" = [] }
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", "aiops-incident-processor-${var.environment}", { "stat" = "Sum", "label" = "Invocations", "color" = "#1f77b4", "id" = "m2" }],
            ["AWS/Lambda", "Errors", "FunctionName", "aiops-incident-processor-${var.environment}", { "stat" = "Sum", "label" = "Errors", "color" = "#d62728", "id" = "m1" }],
            [{ "expression" = "100*(m1/m2)", "label" = "Error Rate %", "id" = "e1", "color" = "#ff7f0e", "yAxis" = "right" }]
          ]
          yAxis = {
            "left"  = { "min" = 0, "label" = "Count" }
            "right" = { "min" = 0, "max" = 100, "label" = "Error %" }
          }
        }
      },

      # ── Row 4: Latency percentiles ────────────────────────
      {
        type   = "metric"
        x      = 0
        y      = 14
        width  = 12
        height = 6
        properties = {
          title   = "Lambda Latency — P50 / P90 / P99"
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          period  = 60
          annotations = {
            horizontal = [
              { "value" = 30000, "label" = "30s timeout warning", "color" = "#ff7f0e" }
            ]
          }
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", "aiops-incident-processor-${var.environment}", { "stat" = "p50", "label" = "P50 ms", "color" = "#2ca02c" }],
            ["AWS/Lambda", "Duration", "FunctionName", "aiops-incident-processor-${var.environment}", { "stat" = "p90", "label" = "P90 ms", "color" = "#ff7f0e" }],
            ["AWS/Lambda", "Duration", "FunctionName", "aiops-incident-processor-${var.environment}", { "stat" = "p99", "label" = "P99 ms", "color" = "#d62728" }]
          ]
          yAxis = { "left" = { "min" = 0 } }
        }
      },

      # ── Row 4: Recent log insights ────────────────────────
      {
        type   = "log"
        x      = 12
        y      = 14
        width  = 12
        height = 6
        properties = {
          title   = "Recent Incidents — Live Log Feed"
          region  = var.aws_region
          view    = "table"
          query   = "SOURCE '/aws/lambda/aiops-incident-processor-${var.environment}' | fields @timestamp, @message | filter @message like /Pipeline complete|AI analysis complete|severity/ | sort @timestamp desc | limit 20"
        }
      },

      # ── Row 5: Alarm status ────────────────────────────────
      {
        type   = "alarm"
        x      = 0
        y      = 20
        width  = 24
        height = 3
        properties = {
          title  = "🚨 Active Alarms"
          alarms = [
            "arn:aws:cloudwatch:${var.aws_region}:${data.aws_caller_identity.current.account_id}:alarm:aiops-high-cpu-${var.environment}"
          ]
        }
      }

    ]
  })
}

output "dashboard_url" {
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.aiops_main.dashboard_name}"
  description = "CloudWatch Dashboard URL"
}
