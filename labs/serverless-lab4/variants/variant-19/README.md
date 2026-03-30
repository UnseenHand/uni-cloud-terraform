## Variant 19

Short name: `Розсилка учасникам`

Business logic:
- `POST /registrations/{event_id}` stores a participant in DynamoDB and publishes a confirmation message to SNS.
- `GET /registrations/{event_id}/count` returns the number of registered participants for that event.

AWS services used:
- API Gateway HTTP API
- Lambda
- DynamoDB
- SNS
- S3 backend for Terraform state

### Layout

```text
variants/variant-19/
  envs/dev/
  modules/
  src/
```

### Prerequisites

- Terraform `>= 1.10.0`
- AWS CLI configured with credentials for the target account
- Existing S3 bucket for Terraform state
- `uv` installed for Python dependency management

### 1. Create the S3 State Bucket

Recommended bucket naming for multi-variant work:

```powershell
$env:BUCKET_NAME = "tf-state-lab4-surname-name"
aws s3api create-bucket --bucket $env:BUCKET_NAME --region eu-central-1 --create-bucket-configuration LocationConstraint=eu-central-1
aws s3api put-bucket-versioning --bucket $env:BUCKET_NAME --versioning-configuration Status=Enabled
aws s3api get-bucket-versioning --bucket $env:BUCKET_NAME
```

One shared bucket is enough. Separate variants should use different state keys, not different buckets.

### 2. Configure Backend

In [`envs/dev`](C:\Code\University\T3\cloud\terraform-lab4\variants\variant-19\envs\dev), create `backend.hcl` from [`backend.hcl.example`](C:\Code\University\T3\cloud\terraform-lab4\variants\variant-19\envs\dev\backend.hcl.example) and set your real bucket name.

Example content:

```hcl
bucket       = "tf-state-lab4-surname-name"
key          = "variants/variant-19/envs/dev/terraform.tfstate"
region       = "eu-central-1"
encrypt      = true
use_lockfile = true
```

### 3. Configure Terraform Variables

Create `terraform.tfvars` in [`envs/dev`](C:\Code\University\T3\cloud\terraform-lab4\variants\variant-19\envs\dev):

```hcl
aws_region          = "eu-central-1"
prefix              = "surname-name-19"
notification_email  = "your-email@example.com"
```

Notes:
- `prefix` is used in AWS resource names.
- `notification_email` must be real because SNS email subscriptions require confirmation.

### 4. Initialize and Apply

Run from [`envs/dev`](C:\Code\University\T3\cloud\terraform-lab4\variants\variant-19\envs\dev):

```powershell
terraform init -backend-config=backend.hcl
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

### 5. Confirm SNS Subscription

AWS SNS will send a confirmation email to `notification_email`. Until that confirmation link is accepted, the topic exists but email delivery will not work.

### 6. Test the API

Get the deployed API URL:

```powershell
$API_URL = terraform output -raw api_url
$API_URL
```

Register a participant:

```powershell
curl -X POST "$API_URL/registrations/42" `
  -H "Content-Type: application/json" `
  -d '{"email":"test@example.com","name":"Test User"}'
```

Expected shape:

```json
{
  "message": "Created",
  "item": {
    "event_id": "42",
    "participant_id": "...",
    "email": "test@example.com",
    "name": "Test User",
    "created_at": "..."
  }
}
```

Get the participant count:

```powershell
curl -X GET "$API_URL/registrations/42/count"
```

Expected shape:

```json
{
  "count": 1
}
```

### 7. Local Validation

Run Terraform validation:

```powershell
terraform fmt -recursive
terraform validate
```

Python dependencies are managed from the repository root:

```powershell
uv sync
```

### 8. Automated API Tests

Integration tests for `src/app.py` are in `tests/test_api_integration.py`.

Run them after `terraform apply`:

```powershell
uv sync
$API_URL = terraform output -raw api_url
$env:API_URL = $API_URL
uv run python -m unittest tests/test_api_integration.py -v
```

What is covered:
- successful registration flow and count endpoint;
- duplicate `participant_id` handling (`409`);
- invalid email validation (`400`);
- invalid JSON payload handling (`400`).

### 9. Cost Notes

This variant is low-cost for lab usage because:

- API Gateway HTTP API is request-based.
- Lambda is request and execution-time based.
- DynamoDB uses on-demand billing.
- SNS email delivery is usage-based.
- No always-on compute instances are created.

To minimize cost further:

- destroy the stack when finished;
- keep Lambda memory and timeout low;
- keep CloudWatch log retention short;
- avoid unnecessary test traffic.

### 10. Destroy

```powershell
terraform destroy -var-file=terraform.tfvars
```
