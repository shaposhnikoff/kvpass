# Installation

## Prerequisites

- **Python 3.11+**
- **uv** (recommended) or pip
- **Azure CLI** (for authentication)
- An **Azure Key Vault** instance with appropriate permissions

## Install with uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package manager.

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/kvpass.git
cd kvpass

# Ensure Python 3.11+ is used
uv python pin 3.11

# Install dependencies and create virtual environment
uv sync

# Run kvpass
uv run kvpass --help
```

## Install with pip

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/kvpass.git
cd kvpass

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e .

# Run kvpass
kvpass --help
```

## Install from wheel

```bash
# Build the package
uv build

# Install the wheel
pip install dist/kvpass-0.1.0-py3-none-any.whl
```

## Azure Authentication

kvpass uses `DefaultAzureCredential` from the Azure SDK, which automatically tries multiple authentication methods in order:

### Option 1: Azure CLI (Recommended for development)

```bash
# Login to Azure
az login

# Verify you're logged in
az account show
```

### Option 2: Environment Variables

Set these environment variables for service principal authentication:

```bash
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
```

### Option 3: Managed Identity

If running on Azure (VM, AKS, App Service), Managed Identity is automatically used.

## Azure Key Vault Permissions

The authenticated identity needs these permissions on the Key Vault:

| Permission | Required For |
|------------|--------------|
| `Get` | Reading secrets |
| `List` | Listing secrets |
| `Set` | Creating/updating secrets |
| `Delete` | Deleting secrets |
| `Purge` | Purging deleted secrets (optional) |

### Using Azure RBAC

Assign the **Key Vault Secrets Officer** role:

```bash
az role assignment create \
  --role "Key Vault Secrets Officer" \
  --assignee YOUR_EMAIL_OR_OBJECT_ID \
  --scope /subscriptions/SUB_ID/resourceGroups/RG_NAME/providers/Microsoft.KeyVault/vaults/VAULT_NAME
```

### Using Access Policies

```bash
az keyvault set-policy \
  --name YOUR_VAULT_NAME \
  --upn YOUR_EMAIL \
  --secret-permissions get list set delete purge
```

## Verify Installation

```bash
# Should display help
uv run kvpass --help

# Should list secrets (empty if new vault)
uv run kvpass ls
```

## Next Steps

- [Configure kvpass](configuration.md)
- [Learn the commands](usage.md)

