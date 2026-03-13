# Shell Completion

kvpass supports tab-completion for Bash, Zsh, and Fish shells.

## Features

The completion scripts provide:

- **Command completion**: `kvpass <TAB>` → `ls`, `get`, `set`, `tag`, etc.
- **Option completion**: `kvpass ls --<TAB>` → `--show-pass`, `--show-tags`, `--tag`
- **Vault names**: `kvpass --vault <TAB>` → lists vaults from config
- **Secret paths**: `kvpass get <TAB>` → dynamically completes secret paths
- **Tag keys** (for `untag`): `kvpass untag mypath <TAB>` → lists existing tag keys

## Installation

### Option 1: Typer Built-in (Simplest)

kvpass uses Typer which has built-in completion support:

```bash
# Bash
kvpass --install-completion bash

# Zsh
kvpass --install-completion zsh

# Fish
kvpass --install-completion fish
```

This adds a line to your shell config file. Restart your shell or source the file.

## Usage Examples

```bash
# Complete commands
kvpass <TAB>
# → config  vaults  ls  search  get  set  edit  versions  rm  tags  tag  untag  firewall

# Complete vault names
kvpass --vault <TAB>
# → prod  dev  staging

# Complete options
kvpass ls --<TAB>
# → --show-pass  --show-tags  --tag

# Complete secret paths
kvpass get <TAB>
# → prod/db/password  prod/api/key  staging/db/user  ...

# Complete tag keys for untag
kvpass untag prod/db/password <TAB>
# → env  team  owner
```

## Performance Notes

- Path completion fetches secrets from Azure Key Vault
- Results are cached for 60 seconds to improve performance
- First completion may be slow (~1-3 seconds) while fetching
- Subsequent completions within 60 seconds are instant

## Troubleshooting

### Completion not working

1. Make sure you've sourced/reloaded your shell config
2. Check that kvpass is in your PATH: `which kvpass`
3. For Zsh, ensure compinit is called: `autoload -Uz compinit && compinit`

### Path completion not showing secrets

1. Make sure you're authenticated: `az login`
2. Check that kvpass can list secrets: `kvpass ls`
3. Path completion requires network access to Azure

### Slow completion

- First completion fetches from Azure (1-3 seconds)
- Use `--vault` to select a specific vault before `<TAB>`
- Cached results are used for 60 seconds
