## Variant 19 (Lab 5 AI Extension)

Short name: `Розсилка учасникам`

This Lab 5 variant extends Lab 4 with Amazon Comprehend.

### Endpoints

- `POST /registrations/{event_id}`: create registration, detect language of registration text, store AI fields in DynamoDB, and send SNS confirmation.
- `GET /registrations/{event_id}/count`: return participant count (AI-analysis rows are excluded).
- `GET /registrations/{id}/lang`: run Comprehend dominant-language analysis for registrations in that group and persist analysis result in DynamoDB.

### Required IAM Actions for Comprehend

Lambda execution role includes:

- `comprehend:DetectSentiment`
- `comprehend:DetectEntities`
- `comprehend:DetectKeyPhrases`
- `comprehend:DetectDominantLanguage`

### Deploy

From `variants/variant-19/envs/dev`:

```powershell
terraform init -backend-config=backend.hcl
terraform fmt -recursive
terraform validate
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

Get URL and table name:

```powershell
$API_URL = terraform output -raw api_url
$TABLE_NAME = terraform state show module.database.aws_dynamodb_table.this | Select-String "name" | Select-Object -First 1
$API_URL
```

### CURL Tests

Register participants:

```powershell
curl -X POST "$API_URL/registrations/event-19" `
  -H "Content-Type: application/json" `
  -d '{"email":"oksana@example.com","name":"Оксана Коваленко"}'

curl -X POST "$API_URL/registrations/event-19" `
  -H "Content-Type: application/json" `
  -d '{"email":"taras@example.com","name":"Taras Melnyk"}'
```

Check count:

```powershell
curl -X GET "$API_URL/registrations/event-19/count"
```

Run Comprehend endpoint:

```powershell
curl -X GET "$API_URL/registrations/event-19/lang"
```

Expected response shape:

```json
{
  "event_id": "event-19",
  "source_registrations_count": 2,
  "detected_language": "uk",
  "language_candidates": [
    {
      "LanguageCode": "uk",
      "Score": 0.99
    }
  ],
  "analysis_record_id": "ai-analysis-...",
  "analysis_status": "ok"
}
```

### Verify Saved AI Results and Logs

Inspect DynamoDB rows for AI metadata:

```powershell
aws dynamodb query `
  --table-name "<your-table-name>" `
  --key-condition-expression "event_id = :event_id" `
  --expression-attribute-values '{":event_id":{"S":"event-19"}}' `
  --region eu-central-1
```

Inspect Lambda logs:

```powershell
aws logs tail "/aws/lambda/<your-prefix>-api-handler" --since 30m --follow --region eu-central-1
```

### Integration Tests

Run after deploy:

```powershell
$env:API_URL = $API_URL
python -m unittest tests/test_api_integration.py -v
```

### Cleanup

```powershell
terraform destroy -var-file=terraform.tfvars
```
