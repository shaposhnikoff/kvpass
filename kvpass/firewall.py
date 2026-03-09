#!/usr/bin/env python3
"""
kv-firewall-checker — Check if your IP is allowed in Azure Key Vault firewall.

Usage:
    kv-firewall-checker <vault-name>
    kv-firewall-checker --all              # Check all vaults from kvpass config
    kv-firewall-checker --vault vault1     # Use vault from kvpass config
"""
from __future__ import annotations

import ipaddress
import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional
from urllib.request import urlopen
from urllib.error import URLError

try:
    from rich.console import Console
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


@dataclass
class FirewallRule:
    """Represents an IP rule or virtual network rule."""
    type: str  # "ip" or "vnet"
    value: str
    
    def matches_ip(self, ip: str) -> bool:
        """Check if this rule allows the given IP address."""
        if self.type != "ip":
            return False
        try:
            # Handle CIDR notation
            if "/" in self.value:
                network = ipaddress.ip_network(self.value, strict=False)
                return ipaddress.ip_address(ip) in network
            else:
                return ip == self.value
        except ValueError:
            return False


@dataclass
class VaultFirewallConfig:
    """Key Vault firewall configuration."""
    vault_name: str
    default_action: str  # "Allow" or "Deny"
    bypass: str  # e.g., "AzureServices"
    ip_rules: list[FirewallRule]
    vnet_rules: list[FirewallRule]
    public_network_access: str  # "Enabled", "Disabled", or "SecuredByPerimeter"
    
    def is_ip_allowed(self, ip: str) -> tuple[bool, str]:
        """
        Check if IP is allowed. Returns (allowed, reason).
        """
        # If public network access is disabled
        if self.public_network_access == "Disabled":
            return False, "Public network access is disabled"
        
        # If default action is Allow and no IP rules, all IPs allowed
        if self.default_action == "Allow":
            return True, "Default action is Allow (no firewall)"
        
        # Default is Deny, check if IP matches any rule
        for rule in self.ip_rules:
            if rule.matches_ip(ip):
                return True, f"Matched IP rule: {rule.value}"
        
        # Check if bypass includes AzureServices
        if "AzureServices" in self.bypass:
            return False, f"IP not in whitelist. Bypass={self.bypass}"
        
        return False, "IP not in whitelist"


def get_public_ip() -> str:
    """Get current public IP address."""
    services = [
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://icanhazip.com",
        "https://checkip.amazonaws.com",
    ]
    
    for service in services:
        try:
            with urlopen(service, timeout=5) as response:
                ip = response.read().decode().strip()
                # Validate it's an IP
                ipaddress.ip_address(ip)
                return ip
        except (URLError, ValueError, TimeoutError):
            continue
    
    raise RuntimeError("Could not determine public IP address")


def get_vault_firewall_config(
    vault_name: str,
    subscription: Optional[str] = None,
) -> VaultFirewallConfig:
    """
    Get firewall configuration for a Key Vault using Azure CLI.
    
    Args:
        vault_name: Name of the Key Vault
        subscription: Optional Azure subscription ID or name
    """
    cmd_show = [
        "az", "keyvault", "show",
        "--name", vault_name,
        "-o", "json"
    ]
    
    if subscription:
        cmd_show.extend(["--subscription", subscription])
    
    try:
        result = subprocess.run(
            cmd_show,
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.lower()
        if "not found" in stderr or "could not be found" in stderr:
            sub_hint = f" in subscription '{subscription}'" if subscription else ""
            raise RuntimeError(
                f"Key Vault '{vault_name}' not found{sub_hint}.\n"
                f"Check the vault name and subscription.\n"
                f"Tip: Add 'subscription = \"your-subscription-id\"' to config."
            )
        if "authorization" in stderr or "forbidden" in stderr or "does not have" in stderr:
            raise RuntimeError(
                f"No permission to read Key Vault '{vault_name}' configuration.\n"
                f"You need 'Reader' role on the Key Vault resource (Azure RBAC).\n"
                f"This is different from Key Vault access policies.\n\n"
                f"To grant access:\n"
                f"  az role assignment create --role Reader \\\n"
                f"    --assignee <your-email-or-object-id> \\\n"
                f"    --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.KeyVault/vaults/{vault_name}"
            )
        raise RuntimeError(f"Azure CLI error: {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError("Azure CLI (az) not found. Install: https://aka.ms/azure-cli")
    
    data = json.loads(result.stdout)
    props = data.get("properties", {})
    acls = props.get("networkAcls") or {}
    
    ip_rules = []
    for rule in acls.get("ipRules", []):
        ip_rules.append(FirewallRule(type="ip", value=rule.get("value", "")))
    
    vnet_rules = []
    for rule in acls.get("virtualNetworkRules", []):
        vnet_rules.append(FirewallRule(type="vnet", value=rule.get("id", "")))
    
    return VaultFirewallConfig(
        vault_name=vault_name,
        default_action=acls.get("defaultAction", "Allow"),
        bypass=acls.get("bypass", "None"),
        ip_rules=ip_rules,
        vnet_rules=vnet_rules,
        public_network_access=props.get("publicNetworkAccess", "Enabled"),
    )


def extract_vault_name_from_url(url: str) -> str:
    """Extract vault name from URL like https://myvault.vault.azure.net/"""
    url = url.rstrip("/")
    if "vault.azure.net" in url:
        # https://myvault.vault.azure.net -> myvault
        parts = url.replace("https://", "").replace("http://", "").split(".")
        return parts[0]
    return url


def print_result_rich(
    vault_name: str,
    public_ip: str,
    config: VaultFirewallConfig,
    allowed: bool,
    reason: str
):
    """Print result using Rich library."""
    console = Console()
    
    # Header
    status = "[green]✓ ALLOWED[/green]" if allowed else "[red]✗ BLOCKED[/red]"
    console.print(f"\n[bold]Key Vault:[/bold] {vault_name}")
    console.print(f"[bold]Your IP:[/bold] {public_ip}")
    console.print(f"[bold]Status:[/bold] {status}")
    console.print(f"[bold]Reason:[/bold] {reason}\n")
    
    # Config details
    table = Table(title="Firewall Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    
    table.add_row("Public Network Access", config.public_network_access)
    table.add_row("Default Action", config.default_action)
    table.add_row("Bypass", config.bypass)
    table.add_row("IP Rules Count", str(len(config.ip_rules)))
    table.add_row("VNet Rules Count", str(len(config.vnet_rules)))
    
    console.print(table)
    
    # Show IP rules if any
    if config.ip_rules:
        console.print("\n[bold]Allowed IP Ranges:[/bold]")
        for rule in config.ip_rules:
            if rule.matches_ip(public_ip):
                console.print(f"  [green]{rule.value} ← YOUR IP[/green]")
            else:
                console.print(f"  {rule.value}")
    
    # Suggestions if blocked
    if not allowed:
        console.print("\n[yellow][bold]To fix this:[/bold][/yellow]")
        console.print(f"  1. Add your IP to the firewall whitelist:")
        console.print(f"     [dim]az keyvault network-rule add --name {vault_name} --ip-address {public_ip}[/dim]")
        console.print(f"  2. Or temporarily allow all networks:")
        console.print(f"     [dim]az keyvault update --name {vault_name} --default-action Allow[/dim]")
        console.print(f"  3. Or use Azure VPN/Private Endpoint")


def print_result_plain(
    vault_name: str,
    public_ip: str,
    config: VaultFirewallConfig,
    allowed: bool,
    reason: str
):
    """Print result without Rich library."""
    status = "✓ ALLOWED" if allowed else "✗ BLOCKED"
    
    print(f"\nKey Vault: {vault_name}")
    print(f"Your IP: {public_ip}")
    print(f"Status: {status}")
    print(f"Reason: {reason}")
    print()
    print("Firewall Configuration:")
    print(f"  Public Network Access: {config.public_network_access}")
    print(f"  Default Action: {config.default_action}")
    print(f"  Bypass: {config.bypass}")
    print(f"  IP Rules: {len(config.ip_rules)}")
    print(f"  VNet Rules: {len(config.vnet_rules)}")
    
    if config.ip_rules:
        print("\nAllowed IP Ranges:")
        for rule in config.ip_rules:
            match = " ← YOUR IP" if rule.matches_ip(public_ip) else ""
            print(f"  {rule.value}{match}")
    
    if not allowed:
        print("\nTo fix this:")
        print(f"  1. Add your IP: az keyvault network-rule add --name {vault_name} --ip-address {public_ip}")
        print(f"  2. Or allow all: az keyvault update --name {vault_name} --default-action Allow")


@dataclass
class VaultInfo:
    """Vault info from config."""
    name: str  # Key Vault name (extracted from URL)
    subscription: Optional[str] = None


def check_vault(
    vault_name: str,
    public_ip: Optional[str] = None,
    subscription: Optional[str] = None,
) -> bool:
    """
    Check if current IP is allowed for a vault.
    Returns True if allowed, False if blocked.
    """
    if public_ip is None:
        public_ip = get_public_ip()
    
    config = get_vault_firewall_config(vault_name, subscription=subscription)
    allowed, reason = config.is_ip_allowed(public_ip)
    
    if RICH_AVAILABLE:
        print_result_rich(vault_name, public_ip, config, allowed, reason)
    else:
        print_result_plain(vault_name, public_ip, config, allowed, reason)
    
    return allowed


def load_vaults_from_config() -> dict[str, VaultInfo]:
    """Load vault info from kvpass config."""
    from pathlib import Path
    import tomllib
    
    config_path = Path.home() / ".config" / "kvpass" / "config.toml"
    if not config_path.exists():
        return {}
    
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    vaults = {}
    
    for section_name, section_data in data.items():
        if isinstance(section_data, dict) and "url" in section_data:
            vault_name = extract_vault_name_from_url(section_data["url"])
            vaults[section_name] = VaultInfo(
                name=vault_name,
                subscription=section_data.get("subscription"),
            )
    
    return vaults


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Check if your IP is allowed in Azure Key Vault firewall",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  kv-firewall-checker myvault                     # Check specific vault
  kv-firewall-checker myvault -s "My Subscription" # With subscription
  kv-firewall-checker --all                       # Check all vaults from kvpass config
  kv-firewall-checker --vault prod                # Check vault 'prod' from kvpass config
  kv-firewall-checker --ip 1.2.3.4 myvault        # Check specific IP
        """
    )
    parser.add_argument("vault_name", nargs="?", help="Key Vault name (without .vault.azure.net)")
    parser.add_argument("--all", "-a", action="store_true", help="Check all vaults from kvpass config")
    parser.add_argument("--vault", "-v", help="Use vault from kvpass config by section name")
    parser.add_argument("--subscription", "-s", help="Azure subscription ID or name")
    parser.add_argument("--ip", help="Check specific IP instead of current public IP")
    
    args = parser.parse_args()
    
    # Determine public IP
    try:
        public_ip = args.ip or get_public_ip()
        if RICH_AVAILABLE:
            Console().print(f"[dim]Detected public IP: {public_ip}[/dim]")
        else:
            print(f"Detected public IP: {public_ip}")
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # List of (vault_name, subscription) tuples to check
    vaults_to_check: list[VaultInfo] = []
    
    if args.all:
        # Check all vaults from config
        config_vaults = load_vaults_from_config()
        if not config_vaults:
            print("No vaults found in kvpass config", file=sys.stderr)
            sys.exit(1)
        vaults_to_check = list(config_vaults.values())
    elif args.vault:
        # Use vault from config
        config_vaults = load_vaults_from_config()
        if args.vault not in config_vaults:
            print(f"Vault '{args.vault}' not found in kvpass config", file=sys.stderr)
            print(f"Available: {', '.join(config_vaults.keys())}", file=sys.stderr)
            sys.exit(1)
        vaults_to_check = [config_vaults[args.vault]]
    elif args.vault_name:
        # Direct vault name with optional subscription from CLI
        vaults_to_check = [VaultInfo(
            name=extract_vault_name_from_url(args.vault_name),
            subscription=args.subscription,
        )]
    else:
        parser.print_help()
        sys.exit(1)
    
    # Check each vault
    all_allowed = True
    for vault_info in vaults_to_check:
        try:
            # CLI --subscription overrides config subscription
            subscription = args.subscription or vault_info.subscription
            if subscription and RICH_AVAILABLE:
                Console().print(f"[dim]Using subscription: {subscription}[/dim]")
            allowed = check_vault(vault_info.name, public_ip, subscription=subscription)
            if not allowed:
                all_allowed = False
        except RuntimeError as e:
            print(f"\nError checking {vault_info.name}: {e}", file=sys.stderr)
            all_allowed = False
    
    sys.exit(0 if all_allowed else 1)


if __name__ == "__main__":
    main()
