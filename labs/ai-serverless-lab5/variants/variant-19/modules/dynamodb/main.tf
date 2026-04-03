resource "aws_dynamodb_table" "main" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "event_id"
  range_key    = "participant_id"

  attribute {
    name = "event_id"
    type = "S"
  }

  attribute {
    name = "participant_id"
    type = "S"
  }
}
