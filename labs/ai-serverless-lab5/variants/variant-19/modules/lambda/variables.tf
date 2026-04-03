variable "function_name" {
  type = string
}

variable "source_file" {
  type = string
}

variable "dynamodb_table_arn" {
  type = string
}

variable "dynamodb_table_name" {
  type = string
}

variable "sns_topic_arn" {
  type = string
}

variable "timeout_seconds" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 5
}

variable "memory_size_mb" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 128
}

variable "log_retention_days" {
  description = "CloudWatch logs retention in days"
  type        = number
  default     = 7
}
