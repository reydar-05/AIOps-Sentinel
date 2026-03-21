variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "private_subnet_ids" { type = list(string) }
variable "ec2_instance_profile_name" { type = string }
variable "ami_id" { type = string }
variable "instance_type" { type = string }
variable "min_size" { type = number }
variable "max_size" { type = number }
variable "desired_capacity" { type = number }
variable "ec2_security_group_id" {
  description = "Security group ID for EC2 instances (from networking module)"
  type        = string
}
variable "alb_security_group_id" {
  description = "Security group ID for ALB (from networking module)"
  type        = string
}
