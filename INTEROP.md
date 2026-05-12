# Composing with other hooks

`sfw-enforce.py` is a pure gate: it inspects the Bash command, exits 0 to allow or 2 to block. It never modifies the command. That makes it safe to compose with other `PreToolUse` Bash hooks that *do* rewrite — the most common case being [rtk](https://github.com/rtk-ai/rtk).

## What was verified against rtk

| Concern | Verdict |
|---|---|
| Compound commands (`cd && ls`, `ls \| head`, `$(ls)`, `bash -c "…"`) | rtk splits on `&&`, `\|\|`, `;`, `\|`, `&` and rewrites each segment independently. No corruption. |
| Order between `sfw-enforce` and `rtk hook claude` | Either order is **safe**. If rtk runs first and rewrites `npm install foo` → `rtk npm install foo`, sfw-enforce's regex still matches `\bnpm\s+install\b` and blocks. If sfw runs first, it short-circuits on raw installs before rtk ever sees them. |
| `sfw`-prefixed commands surviving rtk | `sfw` isn't in rtk's rewrite rules, so `sfw npm install foo` passes through rtk unchanged. |
| `rtk init -g --auto-patch` clobbering existing hooks | It **appends** to the `PreToolUse` array, preserving existing entries. |
| Double-wrap of `rtk` prefix | rtk guards against rewriting commands that already begin with `rtk ` (for non-compounds). |

## Recommended order

Register `sfw-enforce.py` **before** any rewriter:

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "~/.claude/hooks/sfw-enforce.py" }] },
      { "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "rtk hook claude" }] }
    ]
  }
}
```

Either order works, but sfw-first short-circuits earlier on blocked installs — no point invoking the rewriter on a command we're about to reject.

## Trip-ups that survive composition

Things neither hook will catch:

1. **Indirect installs** — `bash setup.sh`, `curl https://… | bash`, `make install`, `docker run`. sfw only sees the literal command Claude Code passes; an install nested inside a script or container is invisible. Defence-in-depth (sandboxed installers, lockfile review) still matters.
2. **Literal-text false positives** — `echo "remember to npm install …"` is text-level matched and blocked. Annoying when discussing/documenting, never dangerous.
3. **`uv sync` / `uv run` friction** — these hit the registry, so they're blocked unless wrapped. Every routine `uv sync` needs the `sfw` prefix.
4. **Fail-open silent bypass** — both hooks return 0 on internal errors (missing `python3`, `jq`, or the `rtk` / `sfw` binary). Right call for availability; means a broken hook silently lets installs through. Periodically sanity-check with:

   ```
   sfw --version && rtk --version && python3 -c 'import json'
   ```

## Adding a third hook

If you stack another `PreToolUse` Bash hook on top, two checks:

- **Does it modify the command?** If yes, will the modified form still trip `sfw-enforce.py`'s install-pattern regex? (For rtk, yes — verified above.)
- **Does it short-circuit or fall through?** A hook that exits non-zero will block the tool call regardless of what comes after. Order matters for *who reports the block message*, not for safety.

If you can answer both, composition is fine. If the third hook re-orders the array on install, that's the only structural risk — pin the order by hand-editing `~/.claude/settings.json` after the third-party installer runs.
