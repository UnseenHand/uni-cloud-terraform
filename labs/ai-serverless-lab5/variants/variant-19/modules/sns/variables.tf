variable "topic_name" {
  description = "SNS topic name for registration notifications"
  type        = string
}

variable "subscription_email" {
  description = "Email that receives registration notifications"
  type        = string
}
