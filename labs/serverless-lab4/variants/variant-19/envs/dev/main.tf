# Виклик модуля бази даних
module "database" {
  source     = "../../modules/dynamodb"
  table_name = "${var.prefix}-registrations"
}

module "notifications" {
  source             = "../../modules/sns"
  topic_name         = "${var.prefix}-registration-notifications"
  subscription_email = var.notification_email
}

# Виклик модуля обчислень з передачею ARN та імені таблиці
module "backend" {
  source              = "../../modules/lambda"
  function_name       = "${var.prefix}-api-handler"
  source_file         = "${path.root}/../../src/app.py"
  dynamodb_table_arn  = module.database.table_arn
  dynamodb_table_name = module.database.table_name
  sns_topic_arn       = module.notifications.topic_arn
}

# Виклик модуля шлюзу API
module "api" {
  source               = "../../modules/api_gateway"
  api_name             = "${var.prefix}-http-api"
  lambda_invoke_arn    = module.backend.invoke_arn
  lambda_function_name = module.backend.function_name
}
