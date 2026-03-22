terraform {
  backend "s3" {
    bucket       = "tf-state-lab3-uhera-vitalii-09"
    key          = "env/dev/var-09.tfstate"
    region       = "eu-central-1"
    encrypt      = true
    use_lockfile = true
  }
}
