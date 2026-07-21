#!/usr/bin/env python3
"""Repair duplicate tables in Codex's persisted TOML configuration."""

from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path


TABLE_HEADER = re.compile(r"^\s*\[([^\[\]]+)]\s*(?:#.*)?$")


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
    if not duplicate_starts:
        return text, False

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

    repaired = "".join(
        line for index, line in enumerate(lines) if index not in remove
    )
    # Refuse to persist a repair that is still not valid TOML.
    tomllib.loads(repaired)
    return repaired, True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config_path")
    args = parser.parse_args()

    path = Path(args.config_path)
    if not path.exists():
        return

    original = path.read_text()
    repaired, changed = repair(original)
    if changed:
        path.write_text(repaired)
        path.chmod(0o600)
        print("Removed duplicate tables from Codex MCP configuration.", flush=True)


if __name__ == "__main__":
    main()
