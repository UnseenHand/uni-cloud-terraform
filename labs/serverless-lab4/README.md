## Terraform Lab Variants

This repository is organized around separate business-logic variants under [`variants`](C:\Code\University\T3\cloud\terraform-lab4\variants). Each variant can contain its own Terraform root module, child modules, Lambda source code, and documentation.

Current implemented variant:
- [`variants/variant-19`](C:\Code\University\T3\cloud\terraform-lab4\variants\variant-19): participant registration service backed by DynamoDB and SNS.

### Repository Layout

```text
variants/
  variant-19/
    envs/dev/
    modules/
    src/
    README.md
pyproject.toml
uv.lock
```

`pyproject.toml` and `uv.lock` stay at the repository root so Python tooling is shared across variants.

### State Bucket Strategy

If you will have many variants such as `variant-01` through `variant-20`, the conventional choice is:

- Use one shared S3 bucket for Terraform state for this lab or repository.
- Use a different `key` per variant and environment.

Recommended example:

```hcl
bucket = "tf-state-lab4-surname-name"
key    = "variants/variant-19/envs/dev/terraform.tfstate"
```

This is usually better than creating 20 buckets because:

- it is easier to manage and document;
- S3 bucket names are globally unique and become annoying to maintain at scale;
- state separation is still preserved by unique keys;
- cost is effectively the same for small Terraform state files.

Create a separate bucket per variant only if you need hard isolation between variants, accounts, or teams. For a university lab, one bucket with one key per variant is the cleaner default.

### Backend Configuration

Do not hardcode personal bucket names into `backend.tf`. Backend values are not regular Terraform variables. Each variant should use partial backend config and pass real values during `terraform init`.

Example pattern:

```powershell
cd variants/variant-19/envs/dev
Copy-Item backend.hcl.example backend.hcl
terraform init -backend-config=backend.hcl
```

`backend.hcl` is ignored by Git via [`.gitignore`](C:\Code\University\T3\cloud\terraform-lab4\.gitignore).

### Variant Configuration

Each variant should keep personal or environment-specific values in local `terraform.tfvars` files, which are also Git-ignored. Commit only example files such as:

- `backend.hcl.example`
- `terraform.tfvars.example`

### When to Split Into Separate Variants

Use a separate `variants/variant-xx` folder when the API shape, resources, or business logic differ meaningfully.

If variants only differ by small parameter changes, separate folders are usually not worth it. In that case, one implementation plus different `tfvars` files is simpler.

### Automation

If you add many variants, there is a point in automating the scaffolding. The useful automation is not creating buckets, but generating a new `variant-xx` folder from a template and pre-filling:

- `envs/dev/backend.hcl.example`
- `envs/dev/terraform.tfvars.example`
- `README.md`
- `src/app.py`

For now, this repository has one implemented variant and the structure is ready to grow without changing the root workflow.
