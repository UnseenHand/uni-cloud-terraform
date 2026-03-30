# 1. Створення HTTP API (v2)
resource "aws_apigatewayv2_api" "http_api" {
  name          = var.api_name
  protocol_type = "HTTP"
}
# 2. Створення стадії розгортання $default
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}
# 3. Налаштування проксі-інтеграції з Lambda
resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id             = aws_apigatewayv2_api.http_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = var.lambda_invoke_arn
}

# 4. Конфігурація маршруту реєстрації
resource "aws_apigatewayv2_route" "register_participant" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /registrations/{event_id}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# 5. Конфігурація маршруту кількості учасників
resource "aws_apigatewayv2_route" "registration_count" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /registrations/{event_id}/count"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# 6. Надання дозволу API Gateway на виклик функції Lambda
resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}
