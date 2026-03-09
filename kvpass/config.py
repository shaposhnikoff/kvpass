from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import tomllib

CONFIG_PATH = Path.home() / ".config" / "kvpass" / "config.toml"

# Global state for selected vault (set via CLI callback)
_selected_vault: Optional[str] = None


@dataclass(frozen=True)
class VaultConfig:
    """Configuration for a single vault."""
    name: str
    url: str
    prefix: str = ""
    clipboard_ttl_seconds: int = 25
    default_copy: bool = True
    is_default: bool = False
    subscription: Optional[str] = None  # Azure subscription ID or name


@dataclass(frozen=True)
class Settings:
    vault_url: str
    vault_name: str
    prefix: str = ""
    clipboard_ttl_seconds: int = 25
    default_copy: bool = True
    subscription: Optional[str] = None


def set_selected_vault(vault_name: Optional[str]) -> None:
    """Set the vault to use for this session."""
    global _selected_vault
    _selected_vault = vault_name


def get_selected_vault() -> Optional[str]:
    """Get the currently selected vault name."""
    return _selected_vault


def load_all_vaults() -> dict[str, VaultConfig]:
    """Load all vault configurations from config file."""
    if not CONFIG_PATH.exists():
        raise SystemExit(
            f"Config not found: {CONFIG_PATH}\n"
            "Create it with vault sections, e.g.\n"
            "[myvault]\n"
            "default = true\n"
            'url = "https://YOURVAULTNAME.vault.azure.net/"\n'
            'prefix = "kvp-"\n'
        )

    data = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    
    vaults: dict[str, VaultConfig] = {}
    for section_name, section_data in data.items():
        if not isinstance(section_data, dict):
            continue
        # A vault section must have a 'url' key
        url = section_data.get("url")
        if not url:
            continue
        
        vaults[section_name] = VaultConfig(
            name=section_name,
            url=url,
            prefix=section_data.get("prefix", ""),
            clipboard_ttl_seconds=int(section_data.get("clipboard_ttl_seconds", 25)),
            default_copy=bool(section_data.get("default_copy", True)),
            is_default=bool(section_data.get("default", False)),
            subscription=section_data.get("subscription"),
        )
    
    if not vaults:
        raise SystemExit(
            f"No vault configurations found in {CONFIG_PATH}\n"
            "Add at least one vault section with 'url' key."
        )
    
    return vaults


def get_default_vault(vaults: dict[str, VaultConfig]) -> Optional[str]:
    """Find the vault marked as default."""
    for name, cfg in vaults.items():
        if cfg.is_default:
            return name
    return None


def load_settings(vault_name: Optional[str] = None) -> Settings:
    """
    Load settings for a specific vault.
    
    Priority:
    1. Explicit vault_name parameter
    2. Global _selected_vault (set via CLI --vault option)
    3. Vault marked as default=true in config
    4. If only one vault exists, use it
    5. Otherwise raise error asking user to specify
    """
    vaults = load_all_vaults()
    
    # Determine which vault to use
    target_vault = vault_name or _selected_vault
    
    if target_vault:
        if target_vault not in vaults:
            available = ", ".join(sorted(vaults.keys()))
            raise SystemExit(
                f"Vault '{target_vault}' not found in config.\n"
                f"Available vaults: {available}"
            )
        cfg = vaults[target_vault]
    else:
        # Try to find default
        default_name = get_default_vault(vaults)
        if default_name:
            cfg = vaults[default_name]
        elif len(vaults) == 1:
            # Only one vault, use it
            cfg = next(iter(vaults.values()))
        else:
            # Multiple vaults, no default, no selection
            available = ", ".join(sorted(vaults.keys()))
            raise SystemExit(
                f"Multiple vaults configured but none selected.\n"
                f"Use --vault <name> or set 'default = true' in config.\n"
                f"Available vaults: {available}"
            )
    
    return Settings(
        vault_url=cfg.url,
        vault_name=cfg.name,
        prefix=cfg.prefix,
        clipboard_ttl_seconds=cfg.clipboard_ttl_seconds,
        default_copy=cfg.default_copy,
        subscription=cfg.subscription,
    )
