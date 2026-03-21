# ── High CPU Alarm ────────────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "aiops-high-cpu-${var.environment}"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Average"
  threshold           = var.cpu_alarm_threshold
  alarm_description   = "EC2 CPU utilization exceeded ${var.cpu_alarm_threshold}%"
  treat_missing_data  = "notBreaching"

  dimensions = {
    AutoScalingGroupName = var.autoscaling_group_name
  }

  alarm_actions = [var.sns_topic_arn]
  ok_actions    = [var.sns_topic_arn]
}

# ── Low CPU (scale down signal) ───────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "low_cpu" {
  alarm_name          = "aiops-low-cpu-${var.environment}"
  comparison_operator = "LessThanOrEqualToThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Average"
  threshold           = 20
  alarm_description   = "EC2 CPU utilization is low — consider scaling down"
  treat_missing_data  = "notBreaching"

  dimensions = {
    AutoScalingGroupName = var.autoscaling_group_name
  }

  alarm_actions = [var.sns_topic_arn]
}

# ── Status Check Failed ───────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "status_check_failed" {
  alarm_name          = "aiops-status-check-failed-${var.environment}"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Maximum"
  threshold           = 1
  alarm_description   = "EC2 instance status check failed — possible crash"
  treat_missing_data  = "breaching"

  dimensions = {
    AutoScalingGroupName = var.autoscaling_group_name
  }

  alarm_actions = [var.sns_topic_arn]
}

# ── Network In Anomaly ────────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "network_anomaly" {
  alarm_name          = "aiops-network-in-high-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "NetworkIn"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 50000000  # 50 MB — adjust for your traffic
  alarm_description   = "High inbound network traffic detected"
  treat_missing_data  = "notBreaching"

  dimensions = {
    AutoScalingGroupName = var.autoscaling_group_name
  }

  alarm_actions = [var.sns_topic_arn]
}
