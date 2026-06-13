from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import DataTable, Input, Static

from .clipboard import copy_with_ttl
from .config import Settings
from .editor import edit_in_editor
from .kv import KV, SecretInfo
from .mapping import decode_name

MatchSpans = dict[str, list[tuple[int, int]]]


@dataclass(frozen=True)
class SecretRow:
    """Display-safe secret metadata for the TUI."""

    raw_name: str
    path: str
    tags: dict[str, str]


@dataclass(frozen=True)
class SecretMatch:
    """A visible row with match spans keyed by displayed field."""

    row: SecretRow
    spans: MatchSpans


@dataclass(frozen=True)
class TuiResult:
    """Action requested after leaving the fullscreen app."""

    action: str
    raw_name: str
    path: str
    query: str


def format_tags_for_display(tags: dict[str, str]) -> str:
    """Format tags with stable ordering for display and filtering."""
    return ", ".join(f"{key}={value}" for key, value in sorted(tags.items()))


def _find_spans(value: str, query: str) -> list[tuple[int, int]]:
    if not query:
        return []

    spans: list[tuple[int, int]] = []
    haystack = value.lower()
    needle = query.lower()
    start = 0
    while True:
        index = haystack.find(needle, start)
        if index == -1:
            return spans
        end = index + len(query)
        spans.append((index, end))
        start = end


def filter_rows(rows: Iterable[SecretRow], query: str) -> list[SecretMatch]:
    """Filter rows by path, raw name, tag keys, or tag values."""
    normalized_query = query.strip()
    if not normalized_query:
        return [SecretMatch(row=row, spans={}) for row in rows]

    matches: list[SecretMatch] = []
    for row in rows:
        field_values = {
            "path": row.path,
            "raw_name": row.raw_name,
            "tags": format_tags_for_display(row.tags),
        }
        spans = {
            field: found
            for field, value in field_values.items()
            if (found := _find_spans(value, normalized_query))
        }
        if spans:
            matches.append(SecretMatch(row=row, spans=spans))
    return matches


def clamp_selection(index: int, visible_count: int) -> int:
    """Keep the selected row valid for the current result count."""
    if visible_count == 0:
        return -1
    if index < 0 or index >= visible_count:
        return 0
    return index


def build_secret_rows(secrets: Iterable[SecretInfo], prefix: str) -> list[SecretRow]:
    """Convert Key Vault metadata to display rows."""
    rows = [
        SecretRow(raw_name=secret.name, path=decode_name(secret.name, prefix), tags=secret.tags)
        for secret in secrets
        if secret.name.startswith(prefix)
    ]
    return sorted(rows, key=lambda row: row.path.lower())


def _styled_cell(value: str, spans: list[tuple[int, int]], selected: bool) -> Text:
    base_style = "bold white on #263347" if selected else ""
    text = Text(value, style=base_style)
    for start, end in spans:
        text.stylize("bold black on yellow", start, end)
    return text


class SecretSelectorApp(App[TuiResult | None]):
    """Fullscreen selector for kvpass secrets."""

    CSS = """
    Screen {
        background: #11131c;
        color: #d7dce8;
    }

    #header {
        height: 1;
        padding: 0 1;
        background: #11131c;
        color: #c8d3f5;
        text-style: bold;
    }

    #search-row {
        height: 1;
        background: #11131c;
    }

    #prompt {
        width: 2;
        padding-left: 1;
        color: #82aaff;
    }

    #filter {
        height: 1;
        border: none;
        background: #11131c;
        color: #d7dce8;
    }

    #secrets {
        height: 1fr;
        background: #11131c;
    }

    #status {
        height: 1;
        padding: 0 1;
        color: #ffc777;
        background: #11131c;
    }

    #shortcuts {
        height: 1;
        padding: 0 1;
        color: #7f849c;
        background: #11131c;
    }
    """

    BINDINGS = [
        Binding("up", "cursor_up", "up", show=False, priority=True),
        Binding("down", "cursor_down", "down", show=False, priority=True),
        Binding("enter", "copy_selected", "copy", show=False, priority=True),
        Binding("ctrl+y", "copy_selected", "yank/copy", show=False, priority=True),
        Binding("ctrl+e", "edit_selected", "edit", show=False, priority=True),
        Binding("ctrl+a", "add_placeholder", "add", show=False, priority=True),
        Binding("ctrl+d", "delete_placeholder", "delete", show=False, priority=True),
        Binding("ctrl+o", "import_placeholder", "import", show=False, priority=True),
        Binding("f1", "help", "help", show=False, priority=True),
        Binding("escape", "quit", "quit", show=False, priority=True),
        Binding("ctrl+c", "quit", "quit", show=False, priority=True),
    ]

    def __init__(
        self,
        *,
        rows: list[SecretRow],
        kv: KV,
        vault_name: str,
        clipboard_ttl_seconds: int,
        initial_query: str = "",
        initial_raw_name: str | None = None,
        initial_status: str = "",
        copy_secret: Callable[[str, int], None] = copy_with_ttl,
    ) -> None:
        super().__init__()
        self.rows = rows
        self.kv = kv
        self.vault_name = vault_name
        self.clipboard_ttl_seconds = clipboard_ttl_seconds
        self.query_text = initial_query
        self.initial_raw_name = initial_raw_name
        self.status_text = initial_status or f"vault: {vault_name}"
        self.copy_secret = copy_secret
        self.visible_matches: list[SecretMatch] = []
        self.selected_index = 0

    def compose(self) -> ComposeResult:
        yield Static(id="header")
        with Horizontal(id="search-row"):
            yield Static(">", id="prompt")
            yield Input(value=self.query_text, id="filter")
        yield DataTable(id="secrets")
        yield Static(id="status")
        yield Static(
            "Enter copy  Ctrl+A add  Ctrl+E edit  Ctrl+D delete  "
            "Ctrl+Y yank/copy  Ctrl+O import  F1 help",
            id="shortcuts",
        )

    def on_mount(self) -> None:
        table = self.query_one("#secrets", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = False
        table.add_columns("", "path", "raw_name", "tags")

        self._apply_filter()
        self.query_one("#filter", Input).focus()
        self._set_status(self.status_text)

    @on(Input.Changed, "#filter")
    def filter_changed(self, event: Input.Changed) -> None:
        self.query_text = event.value
        selected_raw_name = self.selected.row.raw_name if self.selected else None
        self._apply_filter(preferred_raw_name=selected_raw_name)

    @property
    def selected(self) -> SecretMatch | None:
        if self.selected_index == -1:
            return None
        if self.selected_index >= len(self.visible_matches):
            return None
        return self.visible_matches[self.selected_index]

    def _apply_filter(self, preferred_raw_name: str | None = None) -> None:
        self.visible_matches = filter_rows(self.rows, self.query_text)
        self.selected_index = clamp_selection(self.selected_index, len(self.visible_matches))

        target_raw_name = preferred_raw_name or self.initial_raw_name
        if target_raw_name:
            for index, match in enumerate(self.visible_matches):
                if match.row.raw_name == target_raw_name:
                    self.selected_index = index
                    break
        self.initial_raw_name = None

        self._update_header()
        self._refresh_table()

    def _update_header(self) -> None:
        self.query_one("#header", Static).update(f"kvpass {len(self.visible_matches)}/{len(self.rows)}")

    def _refresh_table(self) -> None:
        table = self.query_one("#secrets", DataTable)
        table.clear()
        for index, match in enumerate(self.visible_matches):
            selected = index == self.selected_index
            row = match.row
            table.add_row(
                Text(">" if selected else " ", style="bold #82aaff" if selected else ""),
                _styled_cell(row.path, match.spans.get("path", []), selected),
                _styled_cell(row.raw_name, match.spans.get("raw_name", []), selected),
                _styled_cell(format_tags_for_display(row.tags), match.spans.get("tags", []), selected),
                key=row.raw_name,
            )

        if self.selected_index >= 0:
            table.move_cursor(row=self.selected_index, column=0, animate=False)

    def _set_status(self, message: str, *, temporary: bool = False) -> None:
        self.status_text = message
        self.query_one("#status", Static).update(message)
        if temporary:
            self.set_timer(3.0, self._restore_vault_status)

    def _restore_vault_status(self) -> None:
        if self.status_text.startswith(("copied:", "not implemented:", "help:")):
            self._set_status(f"vault: {self.vault_name}")

    def action_cursor_up(self) -> None:
        if not self.visible_matches:
            return
        self.selected_index = max(0, self.selected_index - 1)
        self._refresh_table()

    def action_cursor_down(self) -> None:
        if not self.visible_matches:
            return
        self.selected_index = min(len(self.visible_matches) - 1, self.selected_index + 1)
        self._refresh_table()

    def action_copy_selected(self) -> None:
        selected = self.selected
        if selected is None:
            self._set_status("no secret selected", temporary=True)
            return

        try:
            value = self.kv.get_secret_value(selected.row.raw_name)
            self.copy_secret(value, self.clipboard_ttl_seconds)
        except Exception as exc:
            self._set_status(f"copy failed: {type(exc).__name__}: {exc}", temporary=True)
            return

        self._set_status(f"copied: {selected.row.path} (TTL {self.clipboard_ttl_seconds}s)", temporary=True)

    def action_edit_selected(self) -> None:
        selected = self.selected
        if selected is None:
            self._set_status("no secret selected", temporary=True)
            return
        self.exit(TuiResult("edit", selected.row.raw_name, selected.row.path, self.query_text))

    def action_add_placeholder(self) -> None:
        self._set_status("not implemented: use kvpass set PATH", temporary=True)

    def action_delete_placeholder(self) -> None:
        self._set_status("not implemented: use kvpass rm PATH", temporary=True)

    def action_import_placeholder(self) -> None:
        self._set_status("not implemented: import is not available in kvpass TUI yet", temporary=True)

    def action_help(self) -> None:
        self._set_status(
            "help: type to filter, use Up/Down to select, Enter or Ctrl+Y to copy, Esc to quit",
            temporary=True,
        )

    def action_quit(self) -> None:
        self.exit(None)


def load_tui_rows(kv: KV, prefix: str) -> list[SecretRow]:
    """Load display rows from Azure Key Vault metadata."""
    return build_secret_rows(kv.list_secrets_with_tags(), prefix)


def run_secret_selector(settings: Settings, kv: KV) -> None:
    """Run the kvpass fullscreen selector."""
    initial_query = ""
    initial_raw_name: str | None = None
    initial_status = ""

    while True:
        app = SecretSelectorApp(
            rows=load_tui_rows(kv, settings.prefix),
            kv=kv,
            vault_name=settings.vault_name,
            clipboard_ttl_seconds=settings.clipboard_ttl_seconds,
            initial_query=initial_query,
            initial_raw_name=initial_raw_name,
            initial_status=initial_status,
        )
        result = app.run()
        if result is None:
            return

        initial_query = result.query
        initial_raw_name = result.raw_name

        if result.action != "edit":
            return

        try:
            current = kv.get_secret_value(result.raw_name)
            updated = edit_in_editor(current)
            if updated == current:
                initial_status = f"no changes: {result.path}"
            else:
                kv.set_secret_value(result.raw_name, updated)
                initial_status = f"updated: {result.path}"
        except SystemExit as exc:
            initial_status = str(exc)
        except Exception as exc:
            initial_status = f"edit failed: {type(exc).__name__}: {exc}"
