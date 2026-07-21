#!/usr/bin/env python3
"""Remove an unmanaged OB table when Feedling already manages the same table."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


MANAGED_BEGIN = "# --- feedling user_mcp (managed) — do not edit ---"
MANAGED_END = "# --- end feedling user_mcp ---"
OB_HEADER = "[mcp_servers.ob]"
TABLE_HEADER = re.compile(r"^\s*\[")


def repair(text: str) -> tuple[str, bool]:
    begin = text.find(MANAGED_BEGIN)
    end = text.find(MANAGED_END)
    if begin < 0 or end < begin:
        return text, False

    managed = text[begin : end + len(MANAGED_END)]
    if OB_HEADER not in managed:
        return text, False

    lines = text.splitlines(keepends=True)
    output: list[str] = []
    in_managed = False
    skipping_unmanaged_ob = False
    changed = False

    for line in lines:
        stripped = line.strip()
        if stripped == MANAGED_BEGIN:
            in_managed = True

        if skipping_unmanaged_ob and TABLE_HEADER.match(line):
            skipping_unmanaged_ob = False

        if not in_managed and stripped == OB_HEADER:
            skipping_unmanaged_ob = True
            changed = True

        if not skipping_unmanaged_ob:
            output.append(line)

        if stripped == MANAGED_END:
            in_managed = False

    repaired = "".join(output)
    return repaired, changed


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
        print("Removed duplicate unmanaged Ombre Brain MCP table.", flush=True)


if __name__ == "__main__":
    main()
