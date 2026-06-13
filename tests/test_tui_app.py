from __future__ import annotations

import asyncio

from textual.widgets import Static

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
