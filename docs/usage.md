# Usage Guide

This guide covers common workflows and best practices for using kvpass.

## Basic Workflow

### 1. Store a Secret

```bash
# Interactive (hidden input) — recommended
uv run kvpass set prod/db/password

# From stdin (good for scripts)
echo "mysecretpassword" | uv run kvpass set prod/db/password

# From file
cat secret.txt | uv run kvpass set prod/api/key

# Direct value (not recommended — visible in shell history)
uv run kvpass set prod/db/password --value "mysecretpassword"
```

### 2. Retrieve a Secret

```bash
# Copy to clipboard (default, safe)
uv run kvpass get prod/db/password
# → Copied: prod/db/password (TTL 25s)

# Print to stdout (explicit, use with caution)
uv run kvpass get prod/db/password --print

# Use in scripts
DB_PASS=$(uv run kvpass get prod/db/password --print)
```

### 3. List Secrets

```bash
# List all secrets
uv run kvpass ls

# Filter by prefix
uv run kvpass ls prod
uv run kvpass ls staging/db

# Show values (unsafe)
uv run kvpass ls --show-pass
```

### 4. Search Secrets

```bash
# Substring search (case-insensitive)
uv run kvpass search "password"
uv run kvpass search "db"

# Regex search
uv run kvpass search --regex "prod/.*/password"
uv run kvpass search -r "^staging/.*"
uv run kvpass search -r "(dev|staging)/db/.*"

# Search with values shown
uv run kvpass search "api" --show-pass
```

## Path Organization

kvpass uses `/` to create a hierarchical structure:

```
prod/
├── db/
│   ├── password
│   └── user
├── api/
│   └── key
└── redis/
    └── password

staging/
├── db/
│   └── password
└── api/
    └── key
```

### Naming Conventions

```bash
# By environment
prod/service/credential
staging/service/credential
dev/service/credential

# By service
aws/access-key
aws/secret-key
github/token
docker/registry-password

# By application
myapp/db/password
myapp/redis/password
myapp/jwt/secret
```

## Editing Secrets

Edit a secret using your preferred text editor:

```bash
# Uses $EDITOR environment variable
export EDITOR=vim  # or nano, code, etc.

uv run kvpass edit prod/db/password
```

The editor opens with the current value. Save and close to update, or close without saving to cancel.

## Version History

Azure Key Vault keeps all versions of a secret:

```bash
# List all versions
uv run kvpass versions prod/db/password

# Get a specific version
uv run kvpass get prod/db/password --version abc123def456
```

## Deleting Secrets

```bash
# Soft delete (can be recovered if soft-delete is enabled)
uv run kvpass rm prod/old/secret

# Permanently purge (cannot be recovered)
uv run kvpass rm prod/old/secret --purge
```

## Scripting Examples

### Database Connection String

```bash
#!/bin/bash
DB_USER=$(uv run kvpass get prod/db/user --print)
DB_PASS=$(uv run kvpass get prod/db/password --print)
DB_HOST="mydb.example.com"

export DATABASE_URL="postgres://${DB_USER}:${DB_PASS}@${DB_HOST}/myapp"
```

### Rotate a Password

```bash
#!/bin/bash
# Generate new password
NEW_PASS=$(openssl rand -base64 32)

# Store in Key Vault
echo "$NEW_PASS" | uv run kvpass set prod/db/password

echo "Password rotated. Old versions available via 'kvpass versions'"
```

### Backup Secrets

```bash
#!/bin/bash
# Export all secrets to encrypted file
uv run kvpass ls --show-pass | gpg -c > secrets-backup.gpg
```

### Sync to .env File

```bash
#!/bin/bash
{
  echo "DB_PASSWORD=$(uv run kvpass get prod/db/password --print)"
  echo "API_KEY=$(uv run kvpass get prod/api/key --print)"
  echo "JWT_SECRET=$(uv run kvpass get prod/jwt/secret --print)"
} > .env
chmod 600 .env
```

## Security Best Practices

### DO ✅

- Use `kvpass get` without `--print` (copies to clipboard)
- Clear clipboard manually if needed: `pbcopy < /dev/null`
- Use short clipboard TTL for sensitive secrets
- Use `kvpass set` without `--value` (hidden prompt)
- Pipe secrets from files: `cat secret.txt | kvpass set path`

### DON'T ❌

- Don't use `--value` with passwords (visible in shell history)
- Don't print secrets to terminal unless necessary
- Don't store secrets in shell scripts
- Don't commit `.env` files with secrets

### Shell History

If you accidentally used `--value`, clear it from history:

```bash
# Bash
history -d $(history | tail -1 | awk '{print $1}')

# Zsh
fc -W  # write history
sed -i '' '/--value/d' ~/.zsh_history
fc -R  # reload history
```

## Troubleshooting

### "Secret not found"

Check the exact path:

```bash
uv run kvpass ls | grep -i "keyword"
uv run kvpass search "keyword"
```

### Clipboard not working

On macOS, `pbcopy`/`pbpaste` should work automatically.

On Linux, install `xclip` or `xsel`:

```bash
# Debian/Ubuntu
sudo apt install xclip

# Fedora
sudo dnf install xclip
```

### Slow commands

Each command authenticates with Azure. For batch operations, consider caching the token:

```bash
# Force token refresh
az account get-access-token --resource https://vault.azure.net
```

