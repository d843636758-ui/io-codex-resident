#!/usr/bin/env python3
"""Keep Codex commentary out of the user-visible IO Chat reply.

Codex 0.142 emits every commentary update and the final answer as separate
``agent_message`` events. Feedling's current parser joins all of them, which
turns internal progress narration into one very long chat message. Until the
upstream parser distinguishes commentary from the final channel, retain only
the last agent message while preserving the separate reasoning summary.

The replacement is deliberately exact and fails the image build if upstream
changes the target code. That is safer than silently deploying an unpatched
consumer after a release changes the parser.
"""

from __future__ import annotations

import argparse
from pathlib import Path


OLD = '    return "\\n\\n".join(replies), "\\n\\n".join(reasoning)\n'
NEW = (
    '    # Codex may emit commentary updates before the final answer. IO Chat\n'
    '    # has no separate commentary surface, so only the terminal assistant\n'
    '    # message is user-visible; reasoning remains a separate disclosure.\n'
    '    reply = replies[-1] if replies else ""\n'
    '    return reply, "\\n\\n".join(reasoning)\n'
)


def patch(path: Path) -> str:
    original = path.read_text()
    if NEW in original:
        return "already_patched"
    occurrences = original.count(OLD)
    if occurrences != 1:
        raise SystemExit(
            f"refusing to patch {path}: expected one parser return, found {occurrences}"
        )
    path.write_text(original.replace(OLD, NEW, 1))
    return "patched"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    print(f"Feedling Codex reply parser: {patch(args.path)}", flush=True)


if __name__ == "__main__":
    main()
