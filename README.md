# Cloud Infrastructure (Terraform)

This project provisions AWS infrastructure using Terraform and includes a user-data script to configure an Apache web server on the created instance.

## Prerequisites

- Terraform installed (v1.x recommended).
- AWS account with credentials configured locally (for example, via `aws configure` or environment variables).
- Permissions to create the required AWS resources (VPC, subnets, security groups, EC2, etc., depending on the configuration).

## Usage

From the project directory, run:

```bash
terraform init
```

Review the planned changes:

```bash
terraform apply
```

When prompted, type `yes` to confirm. Terraform will create the infrastructure.

To remove the infrastructure:

```bash
terraform destroy
```

When prompted, type `yes` to confirm. Terraform will delete the resources it created.
