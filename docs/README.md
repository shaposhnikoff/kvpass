# kvpass Documentation

**kvpass** is a command-line password manager that uses Azure Key Vault as a secure backend for storing secrets.

Think of it as [pass](https://www.passwordstore.org/) (the Unix password manager), but with Azure Key Vault instead of GPG-encrypted files.

## Features

- 🔐 **Secure storage** — secrets are stored in Azure Key Vault with enterprise-grade encryption
- 📋 **Clipboard integration** — passwords are copied to clipboard with auto-clear TTL
- 📁 **Hierarchical paths** — organize secrets like `prod/db/password`, `staging/api/key`
- 🔍 **Search** — find secrets by substring or regex
- 📝 **Editor support** — edit secrets in your favorite `$EDITOR`
- 🕐 **Version history** — access previous versions of any secret
- 🏷️ **Namespace isolation** — prefix separates kvpass secrets from others in the vault

## Table of Contents

- [Installation](installation.md)
- [Configuration](configuration.md)
- [Usage](usage.md)
- [Commands Reference](commands.md)

## Quick Start

```bash
# Install
uv sync

# Configure
mkdir -p ~/.config/kvpass
cat > ~/.config/kvpass/config.toml << 'EOF'
[vault]
url = "https://YOUR-VAULT-NAME.vault.azure.net/"
prefix = "kvp-"
clipboard_ttl_seconds = 25
default_copy = true
EOF

# Authenticate with Azure
az login

# Use it
uv run kvpass ls
uv run kvpass set prod/db/password
uv run kvpass get prod/db/password
```

## License

MIT

