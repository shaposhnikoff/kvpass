# Configuration

kvpass reads its configuration from `~/.config/kvpass/config.toml`.

## Create Configuration

```bash
mkdir -p ~/.config/kvpass
nano ~/.config/kvpass/config.toml
```

## Configuration File Format

kvpass supports **multiple vaults** in a single configuration file. Each vault is defined as a separate TOML section:

```toml
[production]
default = true
url = "https://prod-vault.vault.azure.net/"
prefix = "kvp-"
clipboard_ttl_seconds = 25
default_copy = true

[development]
url = "https://dev-vault.vault.azure.net/"
prefix = "kvp-dev-"
clipboard_ttl_seconds = 30
default_copy = true

[staging]
url = "https://staging-vault.vault.azure.net/"
prefix = ""
clipboard_ttl_seconds = 25
default_copy = true
```

## Selecting a Vault

### Option 1: Default Vault

Set `default = true` on one vault. It will be used automatically:

```toml
[myvault]
default = true
url = "https://my-vault.vault.azure.net/"
```

### Option 2: Command-line Flag

Use `--vault` (or `-v`) to select a vault for any command:

```bash
kvpass --vault production ls
kvpass -v development get prod/db/password
```

### Option 3: Single Vault

If only one vault is configured, it's used automatically (no need for `default = true`).

## List Configured Vaults

```bash
kvpass vaults
```

Output:
```
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┓
┃ Name        ┃ URL                                     ┃ Subscription  ┃ Prefix   ┃ Default ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━┩
│ development │ https://dev-vault.vault.azure.net/      │ (current)     │ kvp-dev- │         │
│ production  │ https://prod-vault.vault.azure.net/     │ my-sub        │ kvp-     │ ✓       │
│ staging     │ https://staging-vault.vault.azure.net/  │ (current)     │ (none)   │         │
└─────────────┴─────────────────────────────────────────┴───────────────┴──────────┴─────────┘
```

## Configuration Options

### `url` (required)

The Azure Key Vault URL. Find it in the Azure Portal under your Key Vault's **Overview** → **Vault URI**.

```toml
url = "https://my-company-vault.vault.azure.net/"
```

### `default` (optional)

Default: `false`

Mark this vault as the default. Only one vault should have `default = true`.

```toml
default = true
```

### `subscription` (optional)

Default: `null` (uses the currently active Azure subscription)

The Azure subscription ID or name that contains the Key Vault. Useful when working with vaults across multiple subscriptions.

```toml
# Use subscription by name
subscription = "My Production Subscription"

# Or by ID
subscription = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

If not set, the currently active subscription (as set by `az account set`) is used.

### `prefix` (optional)

Default: `""`

A prefix added to all secret names in Key Vault. This isolates kvpass secrets from other secrets in the same vault.

```toml
# Secrets will be stored as: kvp-prod--db--password
prefix = "kvp-"

# Or use a custom prefix
prefix = "passwords-"

# Or no prefix (not recommended if vault has other secrets)
prefix = ""
```

**How it works:**

| User Path | Stored Name (with prefix `kvp-`) |
|-----------|----------------------------------|
| `prod/db/password` | `kvp-prod--db--password` |
| `staging/api/key` | `kvp-staging--api--key` |

### `clipboard_ttl_seconds` (optional)

Default: `25`

How long (in seconds) before the clipboard is automatically cleared after copying a secret.

```toml
# Clear after 10 seconds
clipboard_ttl_seconds = 10

# Clear after 1 minute
clipboard_ttl_seconds = 60
```

### `default_copy` (optional)

Default: `true`

Whether `kvpass get` copies to clipboard by default.

```toml
# Copy to clipboard by default (safe)
default_copy = true

# Don't copy by default (requires explicit --copy or --print)
default_copy = false
```

## Example Configurations

### Single Vault (Simple)

```toml
[vault]
url = "https://my-secrets.vault.azure.net/"
prefix = "kvp-"
```

### Multiple Vaults (Typical Setup)

```toml
[prod]
default = true
url = "https://prod-secrets.vault.azure.net/"
subscription = "Production Subscription"
prefix = "kvp-"
clipboard_ttl_seconds = 10
default_copy = true

[dev]
url = "https://dev-secrets.vault.azure.net/"
prefix = "kvp-dev-"
clipboard_ttl_seconds = 30
default_copy = true

[shared]
url = "https://shared-vault.vault.azure.net/"
subscription = "Shared Services"
prefix = ""
```

Usage:
```bash
# Uses prod (default)
kvpass ls

# Explicitly use dev
kvpass --vault dev ls

# Use shared vault
kvpass -v shared get api/key
```

## Troubleshooting

### Config not found

```
Config not found: /Users/you/.config/kvpass/config.toml
```

Create the configuration file as described above.

### No vault configurations found

```
No vault configurations found in config.toml
```

Make sure each vault section has a `url` key.

### Multiple vaults, none selected

```
Multiple vaults configured but none selected.
Use --vault <name> or set 'default = true' in config.
```

Either:
- Add `default = true` to one vault section
- Use `--vault <name>` when running commands

### Vault not found

```
Vault 'xyz' not found in config.
Available vaults: dev, prod, staging
```

Check the vault name matches a section in your config file.

### Authentication errors

Make sure you're authenticated:

```bash
az login
az account show
```

Check that your account has the required Key Vault permissions.
