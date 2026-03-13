# Commands Reference

Complete reference for all kvpass commands.

## Global Options

```bash
kvpass --help           # Show help
kvpass --version        # Show version (if configured)
kvpass --vault NAME     # Select vault by name (or -v NAME)
```

### `--vault` / `-v`

Select which vault to use for the command. The vault name must match a section in your config file.

```bash
# Use "production" vault
kvpass --vault production ls

# Short form
kvpass -v dev get myapp/password
```

If not specified, kvpass uses:
1. The vault marked with `default = true` in config
2. The only vault (if just one is configured)

---

## `config` — Edit Configuration

Open the configuration file in your text editor.

```bash
kvpass config
```

If the config file does not exist, a template is created automatically before the editor opens.

### Environment

Uses `$EDITOR` or `$VISUAL` environment variable.

```bash
export EDITOR=nano
export EDITOR=vim
export EDITOR="code --wait"
```

### Examples

```bash
kvpass config
```

---

## `vaults` — List Configured Vaults

List all vaults from your configuration file.

```bash
kvpass vaults
```

### Output

```
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┓
┃ Name        ┃ URL                                     ┃ Subscription  ┃ Prefix   ┃ Default ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━┩
│ development │ https://dev-vault.vault.azure.net/      │ (current)     │ kvp-dev- │         │
│ production  │ https://prod-vault.vault.azure.net/     │ my-sub        │ kvp-     │ ✓       │
│ staging     │ https://staging-vault.vault.azure.net/  │ (current)     │ (none)   │         │
└─────────────┴─────────────────────────────────────────┴───────────────┴──────────┴─────────┘

Use --vault <name> to select a specific vault
```

---

## `ls` — List Secrets

List all secrets managed by kvpass.

```bash
kvpass ls [PREFIX] [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `PREFIX` | Optional. Filter by path prefix (e.g., `prod`, `staging/db`) |

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--show-pass` | | Show secret values in the table (unsafe) |
| `--show-tags` | `-t` | Show tags in the output |
| `--tag` | | Filter by tag (format: `key=value`) |

### Examples

```bash
# List all secrets
kvpass ls

# List secrets starting with "prod"
kvpass ls prod

# List secrets with values
kvpass ls --show-pass

# Show tags
kvpass ls --show-tags
kvpass ls -t

# Filter by tag
kvpass ls --tag env=prod
kvpass ls --tag team=backend --show-tags

# Combined
kvpass ls staging --show-pass --show-tags
```

### Output

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ raw_name                ┃ path              ┃ tags                     ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ kvp-prod--db--password  │ prod/db/password  │ env=prod, team=backend   │
│ kvp-prod--db--user      │ prod/db/user      │ env=prod                 │
│ kvp-staging--api--key   │ staging/api/key   │ env=staging              │
└─────────────────────────┴───────────────────┴──────────────────────────┘
```

---

## `search` — Search Secrets

Search secrets by path pattern.

```bash
kvpass search PATTERN [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `PATTERN` | Search pattern (substring or regex) |

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--regex` | `-r` | Treat pattern as regular expression |
| `--show-pass` | | Show secret values (unsafe) |
| `--show-tags` | `-t` | Show tags in the output |
| `--tag` | | Filter by tag (format: `key=value`) |

### Examples

```bash
# Substring search (case-insensitive)
kvpass search "password"
kvpass search "db"

# Regex search
kvpass search --regex "prod/.*/password"
kvpass search -r "^staging/.*"
kvpass search -r "(dev|staging)/api/.*"

# With values
kvpass search "api" --show-pass

# With tags
kvpass search "password" --show-tags

# Filter by tag
kvpass search "db" --tag env=prod
```

---

## `get` — Get Secret

Retrieve a secret value.

```bash
kvpass get PATH [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `PATH` | Secret path (e.g., `prod/db/password`) |

### Options

| Option | Description |
|--------|-------------|
| `--copy / --no-copy` | Copy to clipboard (default: from config) |
| `--print` | Print value to stdout (unsafe) |
| `--version TEXT` | Get specific version |

### Examples

```bash
# Copy to clipboard (default)
kvpass get prod/db/password

# Print to stdout
kvpass get prod/db/password --print

# Force copy
kvpass get prod/db/password --copy

# Get specific version
kvpass get prod/db/password --version abc123

# Use in script
PASSWORD=$(kvpass get prod/db/password --print)
```

---

## `set` — Set Secret

Create or update a secret.

```bash
kvpass set PATH [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `PATH` | Secret path (e.g., `prod/db/password`) |

### Options

| Option | Description |
|--------|-------------|
| `--value TEXT` | Provide value directly (not recommended) |

### Input Methods

1. **Interactive prompt** (recommended):
   ```bash
   kvpass set prod/db/password
   # Secret value (hidden): ****
   ```

2. **Stdin pipe** (good for scripts):
   ```bash
   echo "mypassword" | kvpass set prod/db/password
   cat secret.txt | kvpass set prod/db/password
   ```

3. **Direct value** (not recommended — visible in history):
   ```bash
   kvpass set prod/db/password --value "mypassword"
   ```

### Examples

```bash
# Interactive
kvpass set prod/db/password

# From file
cat ~/.ssh/id_rsa | kvpass set keys/ssh/private

# From command output
openssl rand -base64 32 | kvpass set prod/jwt/secret
```

---

## `edit` — Edit Secret

Edit a secret in your text editor.

```bash
kvpass edit PATH
```

### Arguments

| Argument | Description |
|----------|-------------|
| `PATH` | Secret path to edit |

### Environment

Uses `$EDITOR` or `$VISUAL` environment variable.

```bash
export EDITOR=vim
# or
export EDITOR=nano
# or
export EDITOR="code --wait"
```

### Examples

```bash
kvpass edit prod/db/password
```

The editor opens with the current value. Save and close to update.

---

## `versions` — List Versions

List all versions of a secret.

```bash
kvpass versions PATH
```

### Arguments

| Argument | Description |
|----------|-------------|
| `PATH` | Secret path |

### Examples

```bash
kvpass versions prod/db/password
```

### Output

```
abc123def456789...
def456abc789012...
ghi789def012345...
```

Use these version IDs with `kvpass get --version`.

---

## `rm` — Delete Secret

Delete a secret from Key Vault.

```bash
kvpass rm PATH [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `PATH` | Secret path to delete |

### Options

| Option | Description |
|--------|-------------|
| `--purge` | Permanently purge after deletion |

### Behavior

- Without `--purge`: Soft delete (recoverable if soft-delete is enabled on vault)
- With `--purge`: Permanent deletion (requires purge permission)

### Examples

```bash
# Soft delete
kvpass rm old/secret

# Permanent delete
kvpass rm old/secret --purge
```

---

## Tag Commands

Azure Key Vault secrets support tags — key-value pairs for organizing and filtering secrets.

### `tags` — Show Tags

Show all tags for a secret.

```bash
kvpass tags PATH
```

#### Examples

```bash
kvpass tags prod/db/password
```

#### Output

```
┏━━━━━━━┳━━━━━━━━━━┓
┃ Key   ┃ Value    ┃
┡━━━━━━━╇━━━━━━━━━━┩
│ env   │ prod     │
│ owner │ alice    │
│ team  │ backend  │
└───────┴──────────┘
```

---

### `tag` — Add/Update Tags

Add or update tags on a secret.

```bash
kvpass tag PATH ... [OPTIONS]
```

#### Arguments

| Argument | Description |
|----------|-------------|
| `PATH` | Secret path |
| `TAG_VALUES` | One or more `key=value` pairs |

#### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--replace` | `-r` | Replace all tags instead of merging |

#### Examples

```bash
# Add a single tag
kvpass tag prod/db/password env=prod

# Add multiple tags
kvpass tag prod/db/password env=prod team=backend owner=alice

# Update existing tag
kvpass tag prod/db/password env=staging

# Replace all tags (removes existing tags not specified)
kvpass tag prod/db/password env=prod --replace
```

---

### `untag` — Remove Tags

Remove tags from a secret.

```bash
kvpass untag PATH KEYS...
```

#### Arguments

| Argument | Description |
|----------|-------------|
| `PATH` | Secret path |
| `KEYS` | One or more tag keys to remove |

#### Examples

```bash
# Remove single tag
kvpass untag prod/db/password team

# Remove multiple tags
kvpass untag prod/db/password team owner
```

---

## `firewall` — Check Firewall Access

Check whether your current public IP is allowed by the Key Vault firewall.

```bash
kvpass firewall [VAULT_NAME] [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `VAULT_NAME` | Optional. Key Vault name to check (uses current/default vault if omitted) |

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--all` | `-a` | Check all vaults from config |
| `--ip TEXT` | | Check a specific IP instead of your current public IP |
| `--subscription TEXT` | `-s` | Azure subscription ID or name |

### Examples

```bash
# Check current (default) vault
kvpass firewall

# Check a specific vault by name
kvpass firewall myvault

# Check with explicit subscription
kvpass firewall myvault --subscription "My Subscription"
kvpass firewall myvault -s "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

# Check all vaults defined in config
kvpass firewall --all

# Check using a vault selected via --vault flag
kvpass --vault prod firewall

# Check a specific IP address (instead of your current public IP)
kvpass firewall --ip 1.2.3.4
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Invalid arguments |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `EDITOR` / `VISUAL` | Text editor for `kvpass edit` |
| `AZURE_TENANT_ID` | Azure tenant ID (for service principal auth) |
| `AZURE_CLIENT_ID` | Azure client ID (for service principal auth) |
| `AZURE_CLIENT_SECRET` | Azure client secret (for service principal auth) |

