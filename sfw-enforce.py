#!/usr/bin/env python3
"""PreToolUse hook: enforce the sfw wrapper on package-manager install commands.

Reads tool-call JSON from stdin (Claude Code passes
{"tool_name": "Bash", "tool_input": {"command": "..."}}).
Exits 0 to allow, 2 to block with stderr.
Policy source: ~/.claude/socket.md
"""
import json
import re
import sys

ALLOW_PREFIXES = re.compile(r'\b(sfw|socket\s+(npm|npx))\s')

INSTALL_PATTERNS = [
    r'\bnpm\s+(install|i|add|ci)\b',
    r'\bnpx\s+\S',
    r'\bpnpm\s+(add|install|i|dlx)\b',
    r'\byarn\s+(add|install)\b',
    r'(^|[;&|]\s*)yarn\s*($|[;&|])',
    r'\buv\s+(add|sync|run|pip\s+install|tool\s+install)\b',
    r'\bpip\s+install\b',
    r'\bpipx\s+install\b',
    r'\bcargo\s+(install|add)\b',
]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("tool_name") != "Bash":
        return 0

    cmd = payload.get("tool_input", {}).get("command", "")
    if not cmd:
        return 0

    if ALLOW_PREFIXES.search(cmd):
        return 0

    for pat in INSTALL_PATTERNS:
        if re.search(pat, cmd):
            print(
                f"Install command detected without 'sfw' wrapper:\n  {cmd}\n\n"
                "Policy at ~/.claude/socket.md requires Socket Firewall on package installs.\n"
                "Retry prefixed with `sfw` (e.g., `sfw npm install ...`, `sfw uv add ...`).",
                file=sys.stderr,
            )
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
