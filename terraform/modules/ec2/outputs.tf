output "autoscaling_group_name" {
  value = aws_autoscaling_group.app.name
}

output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "target_group_arn" {
  value = aws_lb_target_group.app.arn
}
