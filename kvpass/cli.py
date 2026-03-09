from __future__ import annotations

import re
import sys
from getpass import getpass
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .config import load_settings, load_all_vaults, set_selected_vault, CONFIG_PATH
from .kv import KV
from .mapping import encode_path, decode_name
from .clipboard import copy_with_ttl
from .editor import edit_in_editor

app = typer.Typer(add_completion=True, no_args_is_help=True)
console = Console()


def parse_tag_filter(tag_filter: str) -> tuple[str, str]:
    """Parse 'key=value' into (key, value) tuple."""
    if "=" not in tag_filter:
        raise typer.BadParameter(f"Invalid tag filter '{tag_filter}'. Use format: key=value")
    key, value = tag_filter.split("=", 1)
    return key.strip(), value.strip()


def parse_tags(tag_args: list[str]) -> dict[str, str]:
    """Parse list of 'key=value' strings into a dict."""
    tags = {}
    for arg in tag_args:
        if "=" not in arg:
            raise typer.BadParameter(f"Invalid tag '{arg}'. Use format: key=value")
        key, value = arg.split("=", 1)
        tags[key.strip()] = value.strip()
    return tags


def format_tags(tags: dict[str, str]) -> str:
    """Format tags dict as a readable string."""
    if not tags:
        return ""
    return ", ".join(f"{k}={v}" for k, v in sorted(tags.items()))


def vault_callback(vault: Optional[str]) -> Optional[str]:
    """Callback to set the selected vault globally before any command runs."""
    if vault:
        set_selected_vault(vault)
    return vault


@app.callback()
def main(
    vault: Optional[str] = typer.Option(
        None,
        "--vault",
        "-v",
        help="Select vault by name from config (e.g., vault1, vault2)",
        callback=vault_callback,
        is_eager=True,
    ),
):
    """
    kvpass — Azure Key Vault password manager.
    
    Use --vault/-v to select a specific vault, or set 'default = true' in config.
    """
    pass


def _ctx():
    s = load_settings()
    kv = KV.from_vault_url(s.vault_url)
    return s, kv


@app.command()
def config():
    """
    Open configuration file in editor.
    
    Creates the config file with a template if it doesn't exist.
    Uses $EDITOR or $VISUAL environment variable.
    """
    import os
    import subprocess
    
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    if not editor:
        console.print("[red]Set $EDITOR environment variable[/red]")
        console.print("  export EDITOR=nano")
        console.print("  export EDITOR=vim")
        console.print("  export EDITOR='code --wait'")
        raise typer.Exit(1)
    
    # Create config directory if needed
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Create template if file doesn't exist
    if not CONFIG_PATH.exists():
        template = '''\
# kvpass configuration
# Each section defines a vault. Set 'default = true' on one vault.

[myvault]
default = true
url = "https://YOUR-VAULT-NAME.vault.azure.net/"
subscription = ""              # Optional: Azure subscription ID or name
prefix = ""                    # Optional: prefix for secret names
clipboard_ttl_seconds = 25     # How long before clipboard is cleared
default_copy = true            # Copy to clipboard by default

# Add more vaults as needed:
# [production]
# url = "https://prod-vault.vault.azure.net/"
# subscription = "Production Subscription"
# prefix = "kvp-"
#
# [development]
# url = "https://dev-vault.vault.azure.net/"
# subscription = "Dev Subscription"
'''
        CONFIG_PATH.write_text(template, encoding="utf-8")
        console.print(f"[green]Created config template:[/green] {CONFIG_PATH}")
    
    console.print(f"[dim]Opening {CONFIG_PATH}...[/dim]")
    subprocess.run([editor, str(CONFIG_PATH)], check=False)
    
    # Validate config after editing
    try:
        vaults_loaded = load_all_vaults()
        console.print(f"[green]Config valid:[/green] {len(vaults_loaded)} vault(s) configured")
    except SystemExit as e:
        console.print(f"[yellow]Warning:[/yellow] {e}")


@app.command()
def vaults():
    """
    List all configured vaults.
    """
    all_vaults = load_all_vaults()
    
    table = Table(title="Configured Vaults")
    table.add_column("Name", style="cyan")
    table.add_column("URL", overflow="fold")
    table.add_column("Subscription", overflow="fold")
    table.add_column("Prefix")
    table.add_column("Default", justify="center")
    
    for name in sorted(all_vaults.keys()):
        cfg = all_vaults[name]
        default_mark = "✓" if cfg.is_default else ""
        table.add_row(
            name,
            cfg.url,
            cfg.subscription or "(current)",
            cfg.prefix or "(none)",
            default_mark,
        )
    
    console.print(table)
    console.print(f"\n[dim]Use --vault <name> to select a specific vault[/dim]")


@app.command()
def ls(
    prefix: str = typer.Argument("", help="Path prefix, e.g. prod/db"),
    show_pass: bool = typer.Option(False, "--show-pass", help="Show secret values (unsafe)"),
    show_tags: bool = typer.Option(False, "--show-tags", "-t", help="Show tags in output"),
    tag_filter: Optional[str] = typer.Option(None, "--tag", help="Filter by tag (key=value)"),
):
    """
    List secrets (filtered by kvpass prefix and optional path prefix).
    """
    s, kv = _ctx()
    console.print(f"[dim]Using vault: {s.vault_name}[/dim]\n")
    enc_prefix = encode_path(prefix, s.prefix) if prefix else s.prefix

    # Parse tag filter if provided
    filter_key, filter_value = None, None
    if tag_filter:
        filter_key, filter_value = parse_tag_filter(tag_filter)

    rows = []
    for info in kv.list_secrets_with_tags():
        if not info.name.startswith(s.prefix):
            continue
        if prefix and not info.name.startswith(enc_prefix):
            continue
        
        # Apply tag filter
        if filter_key:
            if info.tags.get(filter_key) != filter_value:
                continue
        
        path = decode_name(info.name, s.prefix)
        value = None
        if show_pass:
            value = kv.get_secret_value(info.name)
        rows.append((info.name, path, value, info.tags))

    table = Table(title="Key Vault secrets (kvpass)")
    table.add_column("raw_name", overflow="fold")
    table.add_column("path", overflow="fold")
    if show_tags:
        table.add_column("tags", overflow="fold")
    if show_pass:
        table.add_column("value", overflow="fold")

    for row in sorted(rows, key=lambda x: x[1]):
        row_data = [row[0], row[1]]
        if show_tags:
            row_data.append(format_tags(row[3]))
        if show_pass:
            row_data.append(row[2] or "")
        table.add_row(*row_data)
    console.print(table)


@app.command()
def search(
    pattern: str = typer.Argument(..., help="Search pattern (substring or regex)"),
    regex: bool = typer.Option(False, "--regex", "-r", help="Treat pattern as regex"),
    show_pass: bool = typer.Option(False, "--show-pass", help="Show secret values (unsafe)"),
    show_tags: bool = typer.Option(False, "--show-tags", "-t", help="Show tags in output"),
    tag_filter: Optional[str] = typer.Option(None, "--tag", help="Filter by tag (key=value)"),
):
    """
    Search secrets by path. Supports substring or regex matching.
    """
    s, kv = _ctx()
    console.print(f"[dim]Using vault: {s.vault_name}[/dim]\n")

    if regex:
        try:
            compiled = re.compile(pattern)
        except re.error as e:
            raise typer.BadParameter(f"Invalid regex: {e}")
        match_fn = lambda path: compiled.search(path) is not None
    else:
        match_fn = lambda path: pattern.lower() in path.lower()

    # Parse tag filter if provided
    filter_key, filter_value = None, None
    if tag_filter:
        filter_key, filter_value = parse_tag_filter(tag_filter)

    rows = []
    for info in kv.list_secrets_with_tags():
        if not info.name.startswith(s.prefix):
            continue
        path = decode_name(info.name, s.prefix)
        if not match_fn(path):
            continue
        
        # Apply tag filter
        if filter_key:
            if info.tags.get(filter_key) != filter_value:
                continue
        
        value = None
        if show_pass:
            value = kv.get_secret_value(info.name)
        rows.append((info.name, path, value, info.tags))

    if not rows:
        console.print(f"No secrets matching '{pattern}'")
        return

    table = Table(title=f"Search results: '{pattern}'")
    table.add_column("raw_name", overflow="fold")
    table.add_column("path", overflow="fold")
    if show_tags:
        table.add_column("tags", overflow="fold")
    if show_pass:
        table.add_column("value", overflow="fold")

    for row in sorted(rows, key=lambda x: x[1]):
        row_data = [row[0], row[1]]
        if show_tags:
            row_data.append(format_tags(row[3]))
        if show_pass:
            row_data.append(row[2] or "")
        table.add_row(*row_data)
    console.print(table)


@app.command()
def get(
    path: str = typer.Argument(..., help="Path like prod/db/password"),
    version: str = typer.Option(None, "--version", help="Specific version id"),
    copy: bool = typer.Option(None, "--copy/--no-copy", help="Copy to clipboard"),
    print_value: bool = typer.Option(False, "--print", help="Print secret to stdout (unsafe)"),
):
    """
    Get secret. Default behavior: copy to clipboard (safe).
    """
    s, kv = _ctx()
    name = encode_path(path, s.prefix)
    val = kv.get_secret_value(name, version=version)

    do_copy = s.default_copy if copy is None else copy

    if print_value:
        # Explicitly unsafe; user requested
        sys.stdout.write(val + "\n")
        return

    if do_copy:
        copy_with_ttl(val, s.clipboard_ttl_seconds)
        console.print(f"[dim]({s.vault_name})[/dim] Copied: {path}  (TTL {s.clipboard_ttl_seconds}s)")
    else:
        console.print("Refusing to print secret. Use --print or --copy.")


@app.command()
def set(
    path: str = typer.Argument(..., help="Path like prod/db/password"),
    value: str = typer.Option(None, "--value", help="Provide value via flag (not recommended)"),
):
    """
    Set secret value. If --value is not provided:
      - reads from stdin if piped
      - otherwise asks via hidden prompt
    """
    s, kv = _ctx()
    name = encode_path(path, s.prefix)

    if value is None:
        if not sys.stdin.isatty():
            value = sys.stdin.read()
            value = value.rstrip("\n")
        else:
            value = getpass("Secret value (hidden): ")

    if value is None or value == "":
        raise typer.BadParameter("Empty value")

    kv.set_secret_value(name, value)
    console.print(f"[dim]({s.vault_name})[/dim] Updated: {path}")


@app.command()
def edit(path: str = typer.Argument(..., help="Path like prod/db/password")):
    """
    Edit secret in $EDITOR, then save back.
    """
    s, kv = _ctx()
    name = encode_path(path, s.prefix)
    current = kv.get_secret_value(name)
    updated = edit_in_editor(current)
    if updated == current:
        console.print("No changes.")
        return
    kv.set_secret_value(name, updated)
    console.print(f"[dim]({s.vault_name})[/dim] Updated: {path}")


@app.command()
def versions(path: str = typer.Argument(..., help="Path like prod/db/password")):
    """
    List versions for a secret.
    """
    s, kv = _ctx()
    console.print(f"[dim]Using vault: {s.vault_name}[/dim]\n")
    name = encode_path(path, s.prefix)
    vers = kv.list_versions(name)
    for v in vers:
        console.print(v)


@app.command()
def rm(
    path: str = typer.Argument(..., help="Path like prod/db/password"),
    purge: bool = typer.Option(False, "--purge", help="Purge after delete (if soft-delete enabled)"),
):
    """
    Delete secret (and optionally purge).
    """
    s, kv = _ctx()
    name = encode_path(path, s.prefix)
    kv.delete_secret(name)
    console.print(f"[dim]({s.vault_name})[/dim] Deleted: {path}")
    if purge:
        kv.purge_deleted_secret(name)
        console.print(f"[dim]({s.vault_name})[/dim] Purged: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Tag Commands
# ─────────────────────────────────────────────────────────────────────────────


@app.command()
def tags(path: str = typer.Argument(..., help="Path like prod/db/password")):
    """
    Show tags for a secret.
    """
    s, kv = _ctx()
    name = encode_path(path, s.prefix)
    secret_tags = kv.get_secret_tags(name)

    if not secret_tags:
        console.print(f"[dim]({s.vault_name})[/dim] {path}: no tags")
        return

    table = Table(title=f"Tags for {path}")
    table.add_column("Key", style="cyan")
    table.add_column("Value")

    for key, value in sorted(secret_tags.items()):
        table.add_row(key, value)
    
    console.print(f"[dim]Using vault: {s.vault_name}[/dim]\n")
    console.print(table)


@app.command()
def tag(
    path: str = typer.Argument(..., help="Path like prod/db/password"),
    tag_values: list[str] = typer.Argument(..., help="Tags as key=value pairs"),
    replace: bool = typer.Option(False, "--replace", "-r", help="Replace all tags instead of merging"),
):
    """
    Add or update tags on a secret.
    
    Examples:
        kvpass tag prod/db/password env=prod
        kvpass tag prod/db/password env=prod team=backend owner=alice
        kvpass tag prod/db/password env=staging --replace  # replaces all tags
    """
    s, kv = _ctx()
    name = encode_path(path, s.prefix)
    new_tags = parse_tags(tag_values)

    if replace:
        kv.set_tags(name, new_tags)
        console.print(f"[dim]({s.vault_name})[/dim] Replaced tags on: {path}")
    else:
        kv.update_tags(name, new_tags)
        console.print(f"[dim]({s.vault_name})[/dim] Updated tags on: {path}")

    # Show current tags
    current = kv.get_secret_tags(name)
    for key, value in sorted(current.items()):
        console.print(f"  {key}={value}")


@app.command()
def untag(
    path: str = typer.Argument(..., help="Path like prod/db/password"),
    keys: list[str] = typer.Argument(..., help="Tag keys to remove"),
):
    """
    Remove tags from a secret.
    
    Examples:
        kvpass untag prod/db/password team
        kvpass untag prod/db/password team owner  # remove multiple
    """
    s, kv = _ctx()
    name = encode_path(path, s.prefix)
    kv.remove_tags(name, keys)
    console.print(f"[dim]({s.vault_name})[/dim] Removed tags from: {path}")
    
    # Show remaining tags
    current = kv.get_secret_tags(name)
    if current:
        for key, value in sorted(current.items()):
            console.print(f"  {key}={value}")
    else:
        console.print("  (no tags remaining)")


# ─────────────────────────────────────────────────────────────────────────────
# Firewall / Diagnostics Commands
# ─────────────────────────────────────────────────────────────────────────────


@app.command()
def firewall(
    vault_name: Optional[str] = typer.Argument(None, help="Key Vault name (optional if --all)"),
    check_all: bool = typer.Option(False, "--all", "-a", help="Check all vaults from config"),
    check_ip: Optional[str] = typer.Option(None, "--ip", help="Check specific IP instead of current"),
    subscription: Optional[str] = typer.Option(None, "--subscription", "-s", help="Azure subscription ID or name"),
):
    """
    Check if your IP is allowed in Key Vault firewall.
    
    Examples:
        kvpass firewall                           # Check current vault
        kvpass firewall myvault                   # Check specific vault by name
        kvpass firewall myvault -s "My Sub"       # With subscription
        kvpass firewall --all                     # Check all vaults from config
        kvpass --vault prod firewall              # Check vault 'prod' from config
        kvpass firewall --ip 1.2.3.4              # Check specific IP
    """
    from .firewall import get_public_ip, check_vault, load_vaults_from_config, extract_vault_name_from_url, VaultInfo
    
    try:
        public_ip = check_ip or get_public_ip()
        console.print(f"[dim]Your public IP: {public_ip}[/dim]")
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    
    # List of VaultInfo to check
    vaults_to_check: list[VaultInfo] = []
    
    if check_all:
        config_vaults = load_vaults_from_config()
        if not config_vaults:
            console.print("[red]No vaults found in config[/red]")
            raise typer.Exit(1)
        vaults_to_check = list(config_vaults.values())
    elif vault_name:
        vaults_to_check = [VaultInfo(
            name=extract_vault_name_from_url(vault_name),
            subscription=subscription,
        )]
    else:
        # Try to use current vault from --vault option or default
        try:
            s = load_settings()
            vaults_to_check = [VaultInfo(
                name=extract_vault_name_from_url(s.vault_url),
                subscription=subscription or s.subscription,
            )]
        except SystemExit:
            console.print("[red]No vault specified. Use vault name or --all[/red]")
            raise typer.Exit(1)
    
    all_allowed = True
    for vault_info in vaults_to_check:
        try:
            # CLI --subscription overrides config subscription
            sub = subscription or vault_info.subscription
            if sub:
                console.print(f"[dim]Using subscription: {sub}[/dim]")
            allowed = check_vault(vault_info.name, public_ip, subscription=sub)
            if not allowed:
                all_allowed = False
        except RuntimeError as e:
            console.print(f"\n[red]Error checking {vault_info.name}:[/red] {e}")
            all_allowed = False
    
    if not all_allowed:
        raise typer.Exit(1)
