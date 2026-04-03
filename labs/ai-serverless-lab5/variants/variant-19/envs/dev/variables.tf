variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "eu-central-1"
}

variable "prefix" {
  description = "Unique prefix in format surname-name-variant"
  type        = string
  default     = "surname-name-xx"
}

variable "notification_email" {
  description = "Email for SNS registration notifications"
  type        = string
}
