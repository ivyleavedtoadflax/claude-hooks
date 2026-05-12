# claude-hooks

Personal [Claude Code](https://docs.claude.com/en/docs/claude-code) hooks.

## sfw-enforce.py

A `PreToolUse` hook that rejects `Bash` tool calls running a package-manager install command without the [Socket Firewall](https://docs.socket.dev/docs/socket-firewall-free) (`sfw`) wrapper. Stops Claude (and any subagent, and any `!`-prefixed shell command) from running raw installs that bypass Socket's malware checks.

### What it catches

| Manager | Verbs blocked unless wrapped |
| --- | --- |
| npm | `install`, `i`, `add`, `ci` |
| npx | any invocation |
| pnpm | `add`, `install`, `i`, `dlx` |
| yarn | `add`, `install`, and bare `yarn` |
| uv | `add`, `sync`, `run`, `pip install`, `tool install` |
| pip | `install` |
| pipx | `install` |
| cargo | `install`, `add` |

### What passes through

- Anything prefixed with `sfw ` or `socket npm `/`socket npx `.
- All non-install Bash (`git`, `ls`, `grep`, scans, etc.).
- All non-Bash tool calls.

## Install

1. Install Socket Firewall Free:

    ```
    sudo npm i -g sfw
    ```

2. Drop the script into your hooks dir:

    ```
    install -m 755 sfw-enforce.py ~/.claude/hooks/sfw-enforce.py
    ```

3. Register it in `~/.claude/settings.json`:

    ```json
    {
      "hooks": {
        "PreToolUse": [
          {
            "matcher": "Bash",
            "hooks": [
              { "type": "command", "command": "~/.claude/hooks/sfw-enforce.py" }
            ]
          }
        ]
      }
    }
    ```

4. Open `/hooks` once inside Claude Code (or restart the session) so the config watcher picks up the new hook.

## Verify

```
echo '{"tool_name":"Bash","tool_input":{"command":"npm install foo"}}' \
  | ~/.claude/hooks/sfw-enforce.py; echo "exit: $?"
# exit: 2  (blocked)

echo '{"tool_name":"Bash","tool_input":{"command":"sfw npm install foo"}}' \
  | ~/.claude/hooks/sfw-enforce.py; echo "exit: $?"
# exit: 0  (allowed)
```
