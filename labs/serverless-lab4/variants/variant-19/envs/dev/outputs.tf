output "api_url" {
  description = "Base URL of deployed HTTP API"
  value       = module.api.api_endpoint
}

output "sns_topic_arn" {
  description = "SNS topic ARN for registration notifications"
  value       = module.notifications.topic_arn
}
