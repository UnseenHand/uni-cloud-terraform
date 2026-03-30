terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0" # Семантичне версіонування: будь-яка 5.x.x
    }
  }
  # Backend values are provided from backend.hcl during `terraform init`.
  backend "s3" {}
}
