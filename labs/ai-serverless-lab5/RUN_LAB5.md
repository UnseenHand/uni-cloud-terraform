# Lab 5 Runbook

This runbook covers the setup, deployment, manual `curl` checks, automated tests, and cleanup for `ai-serverless-lab5`, variant 19.

## Prerequisites

- Terraform `>= 1.10`
- Python `3.12`
- AWS CLI configured with credentials for:
  - S3 backend access
  - API Gateway
  - Lambda
  - DynamoDB
  - SNS
  - IAM
  - CloudWatch Logs
  - Amazon Comprehend
- `curl`

Notes:

- In PowerShell, prefer `curl.exe` instead of `curl` to avoid the built-in alias.
- The integration tests call the deployed API. They do not start a local server.

## Files To Prepare

Work from:

```powershell
cd C:\Code\University\T3\cloud\uni-cloud-terraform\labs\ai-serverless-lab5\variants\variant-19\envs\dev
```

Create local config files from the examples:

```powershell
Copy-Item backend.hcl.example backend.hcl
Copy-Item terraform.tfvars.example terraform.tfvars
```

Edit `backend.hcl`:

- set your real S3 bucket name for Terraform state
- keep or adjust the state `key`
- keep the AWS region if you deploy to `eu-central-1`

Edit `terraform.tfvars`:

- set `aws_region`
- set a unique `prefix`
- set `notification_email` to a real email address you can confirm in SNS

## Deploy

From `variants/variant-19/envs/dev`:

```powershell
terraform init -backend-config=backend.hcl
terraform fmt -recursive
terraform validate
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

After `apply`, confirm the SNS subscription email. Without confirmation, SNS publishes will succeed but the messages will not be delivered to your mailbox.

## Get The API URL

From `variants/variant-19`:

```powershell
cd ..
$API_URL = terraform -chdir=envs/dev output -raw api_url
$env:API_URL = $API_URL
$API_URL
```

## Manual Checks With curl

Register two participants:

```powershell
curl.exe -X POST "$API_URL/registrations/event-19" `
  -H "Content-Type: application/json" `
  -d "{\"email\":\"oksana@example.com\",\"name\":\"Оксана Коваленко\"}"

curl.exe -X POST "$API_URL/registrations/event-19" `
  -H "Content-Type: application/json" `
  -d "{\"email\":\"taras@example.com\",\"name\":\"Taras Melnyk\"}"
```

Check participant count:

```powershell
curl.exe -X GET "$API_URL/registrations/event-19/count"
```

Run language analysis:

```powershell
curl.exe -X GET "$API_URL/registrations/event-19/lang"
```

Expected behavior:

- both `POST` requests return `201`
- count endpoint returns `200` with `count = 2`
- language endpoint returns `200` and includes fields such as:
  - `event_id`
  - `source_registrations_count`
  - `detected_language`
  - `language_candidates`
  - `analysis_record_id`
  - `analysis_status`

## Automated Integration Tests

From `variants/variant-19`:

```powershell
python -m unittest tests/test_api_integration.py -v
```

The test suite expects `API_URL` to be set in the environment.

The tests cover:

- successful registration flow
- duplicate `participant_id` conflict handling
- invalid email validation
- invalid JSON handling
- AI language endpoint behavior
- count consistency after AI analysis

## Optional Verification

Query DynamoDB:

```powershell
aws dynamodb query `
  --table-name "<your-table-name>" `
  --key-condition-expression "event_id = :event_id" `
  --expression-attribute-values '{":event_id":{"S":"event-19"}}' `
  --region eu-central-1
```

Tail Lambda logs:

```powershell
aws logs tail "/aws/lambda/<your-prefix>-api-handler" --since 30m --follow --region eu-central-1
```

## Cleanup

From `variants/variant-19/envs/dev`:

```powershell
terraform destroy -var-file=terraform.tfvars
```

## Common Issues

- `terraform init` fails:
  - verify the S3 backend bucket exists
  - verify your AWS credentials can access it
- SNS email does not arrive:
  - check the mailbox and confirm the subscription
- `python -m unittest` skips or fails immediately:
  - make sure `API_URL` is set
- Comprehend returns subscription or access errors:
  - verify the AWS account has Amazon Comprehend available in the target region
  - verify the Lambda role includes the required Comprehend actions
