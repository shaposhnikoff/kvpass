from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient, SecretProperties


@dataclass(frozen=True)
class SecretInfo:
    """Secret name with optional tags."""
    name: str
    tags: dict[str, str]


@dataclass(frozen=True)
class KV:
    client: SecretClient

    @staticmethod
    def from_vault_url(vault_url: str) -> "KV":
        cred = DefaultAzureCredential()
        client = SecretClient(vault_url=vault_url, credential=cred)
        return KV(client=client)

    def list_secret_names(self) -> Iterable[str]:
        for props in self.client.list_properties_of_secrets():
            yield props.name

    def list_secrets_with_tags(self) -> Iterable[SecretInfo]:
        """List secrets with their tags."""
        for props in self.client.list_properties_of_secrets():
            yield SecretInfo(
                name=props.name,
                tags=dict(props.tags) if props.tags else {},
            )

    def get_secret_value(self, name: str, version: Optional[str] = None) -> str:
        sec = self.client.get_secret(name, version=version)
        return sec.value

    def get_secret_tags(self, name: str) -> dict[str, str]:
        """Get tags for a specific secret."""
        sec = self.client.get_secret(name)
        return dict(sec.properties.tags) if sec.properties.tags else {}

    def set_secret_value(
        self,
        name: str,
        value: str,
        tags: Optional[dict[str, str]] = None,
    ) -> None:
        """Set secret value, optionally with tags."""
        if tags:
            self.client.set_secret(name, value, tags=tags)
        else:
            self.client.set_secret(name, value)

    def update_tags(self, name: str, tags: dict[str, str]) -> None:
        """
        Update tags on a secret without changing its value.
        Merges with existing tags.
        """
        current_tags = self.get_secret_tags(name)
        current_tags.update(tags)
        self.client.update_secret_properties(name, tags=current_tags)

    def set_tags(self, name: str, tags: dict[str, str]) -> None:
        """
        Replace all tags on a secret (does not merge).
        """
        self.client.update_secret_properties(name, tags=tags)

    def remove_tags(self, name: str, keys: list[str]) -> None:
        """Remove specific tag keys from a secret."""
        current_tags = self.get_secret_tags(name)
        for key in keys:
            current_tags.pop(key, None)
        self.client.update_secret_properties(name, tags=current_tags)

    def list_versions(self, name: str) -> list[str]:
        versions: list[str] = []
        for props in self.client.list_properties_of_secret_versions(name):
            if props.version:
                versions.append(props.version)
        return versions

    def delete_secret(self, name: str) -> None:
        poller = self.client.begin_delete_secret(name)
        poller.result()  # wait

    def purge_deleted_secret(self, name: str) -> None:
        # Requires purge permissions and soft-delete enabled
        self.client.purge_deleted_secret(name)

