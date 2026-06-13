from __future__ import annotations

import asyncio

from textual.coordinate import Coordinate
from textual.widgets import DataTable, Static

from kvpass.tui import SecretRow, SecretSelectorApp


class FakeKV:
    def get_secret_value(self, name: str, version: str | None = None) -> str:
        return f"value:{name}"


def test_secret_selector_filters_and_copies_selected_secret() -> None:
    copied: list[tuple[str, int]] = []

    async def run_app() -> None:
        app = SecretSelectorApp(
            rows=[
                SecretRow("kvp-prod--db--password", "prod/db/password", {"env": "prod"}),
                SecretRow("kvp-dev--api--token", "dev/api/token", {"env": "dev"}),
            ],
            kv=FakeKV(),
            vault_name="test",
            clipboard_ttl_seconds=25,
            copy_secret=lambda value, ttl: copied.append((value, ttl)),
        )

        async with app.run_test() as pilot:
            assert str(pilot.app.query_one("#header", Static).render()) == "kvpass 2/2"
            await pilot.press("d", "b")
            assert str(pilot.app.query_one("#header", Static).render()) == "kvpass 1/2"
            await pilot.press("enter")

    asyncio.run(run_app())

    assert copied == [("value:kvp-prod--db--password", 25)]


def test_secret_selector_uses_name_list_and_metadata_details_panel() -> None:
    async def run_app() -> None:
        app = SecretSelectorApp(
            rows=[
                SecretRow("kvp-prod--db--password", "prod/db/password", {"env": "prod", "team": "database"}),
                SecretRow("kvp-dev--api--token", "dev/api/token", {"env": "dev"}),
            ],
            kv=FakeKV(),
            vault_name="production",
            clipboard_ttl_seconds=30,
            copy_secret=lambda value, ttl: None,
        )

        async with app.run_test() as pilot:
            table = pilot.app.query_one("#secrets", DataTable)
            details = pilot.app.query_one("#details", Static)

            assert len(table.ordered_columns) == 2
            assert str(table.get_cell_at(Coordinate(0, 1))) == "prod/db/password"
            assert "kvp-prod--db--password" not in str(table.get_cell_at(Coordinate(0, 1)))
            assert "env=prod" not in str(table.get_cell_at(Coordinate(0, 1)))

            rendered_details = str(details.render())
            assert "Path: prod/db/password" in rendered_details
            assert "Raw name: kvp-prod--db--password" in rendered_details
            assert "Vault: production" in rendered_details
            assert "Tags: env=prod, team=database" in rendered_details
            assert "Clipboard TTL: 30s" in rendered_details

            await pilot.press("d", "e", "v")
            rendered_details = str(details.render())
            assert "Path: dev/api/token" in rendered_details
            assert "Raw name: kvp-dev--api--token" in rendered_details
            assert "Tags: env=dev" in rendered_details

    asyncio.run(run_app())


def test_secret_selector_visually_separates_list_and_details() -> None:
    css = SecretSelectorApp.CSS

    assert "#secrets" in css
    assert "background: #f8f8f2;" in css
    assert "color: #11131c;" in css
    assert "#details" in css
    assert "background: #5f6368;" in css
    assert "padding: 1 1 0 1;" in css
    assert "#divider" in css
