#!/usr/bin/env python3
"""Repair duplicate tables in Codex's persisted TOML configuration."""

from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path


TABLE_HEADER = re.compile(r"^\s*\[([^\[\]]+)]\s*(?:#.*)?$")
ASSIGNMENT = re.compile(r"^\s*([^=]+?)\s*=")
INLINE_TABLE = re.compile(r"^(\s*[^=]+?=\s*)\{(.*)}(\s*(?:#.*)?)$")
SAFE_BASELINE = """cli_auth_credentials_store = "file"
mcp_oauth_credentials_store = "file"
approval_policy = "never"
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = true
writable_roots = ["/data"]
"""


def _split_inline_items(value: str) -> list[str]:
    items: list[str] = []
    start = 0
    quote = ""
    escaped = False
    depth = 0
    for index, char in enumerate(value):
        if quote:
            if quote == '"' and char == "\\" and not escaped:
                escaped = True
                continue
            if char == quote and not escaped:
                quote = ""
            escaped = False
            continue
        if char in ('"', "'"):
            quote = char
        elif char in "[{(":
            depth += 1
        elif char in "]})":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            items.append(value[start:index].strip())
            start = index + 1
    items.append(value[start:].strip())
    return [item for item in items if item]


def _inline_item_key(item: str) -> str:
    try:
        parsed = tomllib.loads(f"value = {{ {item} }}")["value"]
        if len(parsed) == 1:
            return next(iter(parsed))
    except tomllib.TOMLDecodeError:
        pass
    return item.split("=", 1)[0].strip()


def _dedupe_inline_tables(lines: list[str]) -> tuple[list[str], bool]:
    output: list[str] = []
    changed = False
    for line in lines:
        ending = "\n" if line.endswith("\n") else ""
        body = line[:-1] if ending else line
        match = INLINE_TABLE.match(body)
        if not match:
            output.append(line)
            continue
        items = _split_inline_items(match.group(2))
        last: dict[str, int] = {}
        for index, item in enumerate(items):
            last[_inline_item_key(item)] = index
        kept = [
            item for index, item in enumerate(items)
            if last[_inline_item_key(item)] == index
        ]
        if len(kept) != len(items):
            changed = True
            body = f"{match.group(1)}{{ {', '.join(kept)} }}{match.group(3)}"
        output.append(body + ending)
    return output, changed


def _dedupe_assignments(lines: list[str]) -> tuple[list[str], bool]:
    section = ""
    occurrences: dict[tuple[str, str], list[int]] = {}
    for index, line in enumerate(lines):
        table = TABLE_HEADER.match(line)
        if table:
            section = table.group(1).strip()
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        assignment = ASSIGNMENT.match(line)
        if assignment:
            key = assignment.group(1).strip()
            occurrences.setdefault((section, key), []).append(index)

    remove = {
        index
        for indexes in occurrences.values()
        for index in indexes[:-1]
    }
    if not remove:
        return lines, False
    return [line for index, line in enumerate(lines) if index not in remove], True


def repair(text: str) -> tuple[str, bool]:
    lines = text.splitlines(keepends=True)
    occurrences: dict[str, list[int]] = {}
    headers: list[tuple[int, str]] = []

    for index, line in enumerate(lines):
        match = TABLE_HEADER.match(line)
        if not match:
            continue
        name = match.group(1).strip()
        headers.append((index, name))
        occurrences.setdefault(name, []).append(index)

    duplicate_starts = {
        index
        for indexes in occurrences.values()
        for index in indexes[:-1]
    }
    remove: set[int] = set()
    for position, (start, _name) in enumerate(headers):
        if start not in duplicate_starts:
            continue
        end = headers[position + 1][0] if position + 1 < len(headers) else len(lines)
        for index in range(start, end):
            stripped = lines[index].strip()
            # Keep comments (especially Feedling's managed-block markers) and
            # blank separators, but remove the stale table and its values.
            if stripped and not stripped.startswith("#"):
                remove.add(index)

    lines = [line for index, line in enumerate(lines) if index not in remove]
    lines, assignment_changed = _dedupe_assignments(lines)
    lines, inline_changed = _dedupe_inline_tables(lines)
    changed = bool(remove) or assignment_changed or inline_changed
    if not changed:
        # Still validate an untouched file so startup reports the real problem.
        tomllib.loads(text)
        return text, False
    repaired = "".join(lines)
    # Refuse to persist a repair that is still not valid TOML.
    tomllib.loads(repaired)
    return repaired, True


def drop_table(text: str, table_name: str) -> tuple[str, bool]:
    lines = text.splitlines(keepends=True)
    output: list[str] = []
    dropping = False
    changed = False
    for line in lines:
        table = TABLE_HEADER.match(line)
        if table:
            dropping = table.group(1).strip() == table_name
            if dropping:
                changed = True
                continue
        if dropping:
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                output.append(line)
            continue
        output.append(line)
    result = "".join(output)
    tomllib.loads(result)
    return result, changed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config_path")
    parser.add_argument("--drop-table")
    args = parser.parse_args()

    path = Path(args.config_path)
    if not path.exists():
        return

    original = path.read_text()
    try:
        repaired, changed = repair(original)
    except tomllib.TOMLDecodeError:
        backup = path.with_name("config.toml.invalid.bak")
        backup.write_text(original)
        backup.chmod(0o600)
        repaired = SAFE_BASELINE
        changed = True
        print(
            "Reset invalid Codex configuration to a safe baseline; "
            "OAuth credentials were preserved.",
            flush=True,
        )

    if args.drop_table:
        repaired, dropped = drop_table(repaired, args.drop_table)
        changed = changed or dropped
    if changed:
        path.write_text(repaired)
        path.chmod(0o600)
        print("Codex configuration repair completed.", flush=True)


if __name__ == "__main__":
    main()
