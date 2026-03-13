# Firewall Module

The `firewall` module checks whether your current public IP address is allowed by Azure Key Vault network rules. It uses the Azure CLI (`az`) to read a vault's firewall configuration and evaluates it locally.

## How It Works

1. **Detect your public IP** — queries one of several public IP services (`ipify.org`, `ifconfig.me`, etc.) with a 5-second timeout, trying each in turn until one succeeds.
2. **Fetch vault firewall config** — runs `az keyvault show` to retrieve the vault's `networkAcls` properties.
3. **Evaluate access** — checks your IP against the firewall rules using the logic described below.
4. **Print result** — shows status (ALLOWED / BLOCKED), matching rule if found, and remediation steps if blocked.

## Firewall Evaluation Logic

Access is determined in this order:

| Condition | Result |
|-----------|--------|
| `publicNetworkAccess = Disabled` | **BLOCKED** — no public access at all |
| `defaultAction = Allow` | **ALLOWED** — no firewall restrictions |
| IP matches any IP rule (exact or CIDR) | **ALLOWED** — matched rule shown |
| No rule matched | **BLOCKED** — remediation steps shown |

VNet rules are displayed but not evaluated for IP matching (they require Azure-internal context).

## Firewall Configuration Fields

The module reads these fields from `az keyvault show`:

| Field | Source in JSON | Description |
|-------|---------------|-------------|
| `publicNetworkAccess` | `properties.publicNetworkAccess` | `Enabled`, `Disabled`, or `SecuredByPerimeter` |
| `defaultAction` | `properties.networkAcls.defaultAction` | `Allow` or `Deny` |
| `bypass` | `properties.networkAcls.bypass` | Services that bypass rules (e.g. `AzureServices`) |
| `ipRules` | `properties.networkAcls.ipRules[].value` | IP addresses or CIDR ranges |
| `virtualNetworkRules` | `properties.networkAcls.virtualNetworkRules[].id` | VNet subnet resource IDs |

## Public IP Detection

The module tries these services in order, stopping at the first success:

1. `https://api.ipify.org`
2. `https://ifconfig.me/ip`
3. `https://icanhazip.com`
4. `https://checkip.amazonaws.com`

Each request has a 5-second timeout. If all fail, an error is raised and the command exits.

Override the detected IP with `--ip`:

```bash
kvpass firewall --ip 203.0.113.42
```

## Required Azure Permissions

The `firewall` command needs **Reader** role on the Key Vault _resource_ (Azure RBAC), not Key Vault access policies. This is separate from the permissions needed to read secrets.

```bash
az role assignment create \
  --role Reader \
  --assignee YOUR_EMAIL_OR_OBJECT_ID \
  --scope /subscriptions/SUB_ID/resourceGroups/RG_NAME/providers/Microsoft.KeyVault/vaults/VAULT_NAME
```

## Output

When your IP is **allowed**:

```
Your public IP: 203.0.113.10

Key Vault: my-vault
Your IP: 203.0.113.10
Status: ✓ ALLOWED
Reason: Matched IP rule: 203.0.113.0/24

┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Setting                ┃ Value         ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Public Network Access  │ Enabled       │
│ Default Action         │ Deny          │
│ Bypass                 │ AzureServices │
│ IP Rules Count         │ 3             │
│ VNet Rules Count       │ 1             │
└────────────────────────┴───────────────┘

Allowed IP Ranges:
  10.0.0.0/8
  192.168.1.100
  203.0.113.0/24  ← YOUR IP
```

When your IP is **blocked**:

```
Key Vault: my-vault
Your IP: 198.51.100.5
Status: ✗ BLOCKED
Reason: IP not in whitelist

To fix this:
  1. Add your IP to the firewall whitelist:
     az keyvault network-rule add --name my-vault --ip-address 198.51.100.5
  2. Or temporarily allow all networks:
     az keyvault update --name my-vault --default-action Allow
  3. Or use Azure VPN/Private Endpoint
```

## Troubleshooting

### Vault not found

```
Key Vault 'my-vault' not found in subscription 'My Sub'.
Check the vault name and subscription.
Tip: Add 'subscription = "your-subscription-id"' to config.
```

Set the correct subscription in your config or pass it explicitly:

```bash
kvpass firewall my-vault --subscription "correct-subscription-name"
```

### Permission denied

```
No permission to read Key Vault 'my-vault' configuration.
You need 'Reader' role on the Key Vault resource (Azure RBAC).
```

Assign the Reader role as shown in [Required Azure Permissions](#required-azure-permissions).

### Could not determine public IP

All public IP detection services failed (network issue or restrictive outbound firewall). Use `--ip` to bypass detection:

```bash
kvpass firewall --ip $(curl -s https://api.ipify.org)
```

### Azure CLI not found

```
Azure CLI (az) not found.
```

Install the Azure CLI: `https://aka.ms/azure-cli`
