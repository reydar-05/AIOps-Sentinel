# ── Launch Template ───────────────────────────────────────────────
resource "aws_launch_template" "app" {
  name_prefix   = "aiops-lt-${var.environment}-"
  image_id      = var.ami_id
  instance_type = var.instance_type

  iam_instance_profile {
    name = var.ec2_instance_profile_name
  }

  network_interfaces {
    associate_public_ip_address = true
    security_groups             = [var.ec2_security_group_id]
  }

  monitoring {
    enabled = true  # Detailed monitoring (1-minute intervals)
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash
    yum update -y
    yum install -y amazon-cloudwatch-agent stress-ng

    # Start CloudWatch agent
    /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
      -a fetch-config -m ec2 -s -c default

    # Simple web server for health checks
    yum install -y httpd
    systemctl start httpd
    systemctl enable httpd
    echo "<h1>AIOps Sentinel - Instance $(hostname)</h1>" > /var/www/html/index.html
  EOF
  )

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name        = "aiops-instance-${var.environment}"
      Environment = var.environment
      Project     = "AIOps-Sentinel"
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Security groups are managed by the networking module
# and passed in via variables to avoid duplicate resource conflicts

# ── Application Load Balancer ─────────────────────────────────────
resource "aws_lb" "main" {
  name               = "aiops-alb-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_security_group_id]
  subnets            = var.public_subnet_ids

  enable_deletion_protection = false  # Set true in prod

  tags = { Name = "aiops-alb-${var.environment}" }
}

resource "aws_lb_target_group" "app" {
  name     = "aiops-tg-${var.environment}"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# ── Auto Scaling Group ────────────────────────────────────────────
resource "aws_autoscaling_group" "app" {
  name                = "aiops-asg-${var.environment}"
  vpc_zone_identifier = var.public_subnet_ids
  target_group_arns   = [aws_lb_target_group.app.arn]
  min_size            = var.min_size
  max_size            = var.max_size
  desired_capacity    = var.desired_capacity
  health_check_type   = "ELB"
  health_check_grace_period = 120

  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "aiops-instance-${var.environment}"
    propagate_at_launch = true
  }

  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
    }
  }
}

# ── ASG Scaling Policies ──────────────────────────────────────────
resource "aws_autoscaling_policy" "scale_up" {
  name                   = "aiops-scale-up-${var.environment}"
  scaling_adjustment     = 1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300
  autoscaling_group_name = aws_autoscaling_group.app.name
}

resource "aws_autoscaling_policy" "scale_down" {
  name                   = "aiops-scale-down-${var.environment}"
  scaling_adjustment     = -1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300
  autoscaling_group_name = aws_autoscaling_group.app.name
}
