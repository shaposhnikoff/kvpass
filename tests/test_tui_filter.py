from __future__ import annotations

from kvpass.tui import SecretRow, clamp_selection, filter_rows, format_tags_for_display


def rows() -> list[SecretRow]:
    return [
        SecretRow(
            raw_name="kvp-prod--db--password",
            path="prod/db/password",
            tags={"env": "prod", "team": "database"},
        ),
        SecretRow(
            raw_name="kvp-dev--api--token",
            path="dev/api/token",
            tags={"env": "dev", "team": "platform"},
        ),
        SecretRow(
            raw_name="kvp-shared--registry--password",
            path="shared/registry/password",
            tags={"owner": "sre"},
        ),
    ]


def test_filter_rows_matches_decoded_path_case_insensitively() -> None:
    matches = filter_rows(rows(), "DB")

    assert [match.row.path for match in matches] == ["prod/db/password"]
    assert matches[0].spans["path"] == [(5, 7)]


def test_filter_rows_matches_raw_name() -> None:
    matches = filter_rows(rows(), "registry")

    assert [match.row.raw_name for match in matches] == ["kvp-shared--registry--password"]
    assert matches[0].spans["raw_name"] == [(12, 20)]


def test_filter_rows_matches_tag_keys_and_values() -> None:
    key_matches = filter_rows(rows(), "owner")
    value_matches = filter_rows(rows(), "platform")

    assert [match.row.path for match in key_matches] == ["shared/registry/password"]
    assert key_matches[0].spans["tags"] == [(0, 5)]
    assert [match.row.path for match in value_matches] == ["dev/api/token"]
    assert value_matches[0].spans["tags"] == [(14, 22)]


def test_filter_rows_empty_query_returns_all_rows_without_spans() -> None:
    matches = filter_rows(rows(), "")

    assert [match.row.path for match in matches] == [
        "prod/db/password",
        "dev/api/token",
        "shared/registry/password",
    ]
    assert all(match.spans == {} for match in matches)


def test_clamp_selection_keeps_selection_valid() -> None:
    assert clamp_selection(1, 3) == 1
    assert clamp_selection(4, 3) == 0
    assert clamp_selection(-1, 3) == 0
    assert clamp_selection(0, 0) == -1


def test_format_tags_for_display_is_stable() -> None:
    assert format_tags_for_display({"team": "platform", "env": "prod"}) == "env=prod, team=platform"
    assert format_tags_for_display({}) == ""
