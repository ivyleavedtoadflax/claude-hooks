# PATH wrappers for Socket Firewall

A second defence-in-depth layer alongside [`sfw-enforce.py`](../sfw-enforce.py).

## Why

The Claude Code hook gates Bash commands Claude runs through its declared tool interface. It is structurally blind to:

- Install scripts (`bash setup.sh`, `curl https://… | bash`).
- Package-manager calls Claude Code itself makes internally (e.g. MCP server updates that invoke `uvx` directly, never via the Bash tool).
- Cron jobs, makefiles, IDE-integrated terminals, any other process tree.

A PATH wrapper sits at the OS level: anything that resolves `npm`/`pip`/`uv`/etc. via `$PATH` hits the wrapper first, which re-execs the real binary through `sfw`. It catches the cases the hook can't see.

## How it works

`_dispatch` is a small bash script. We install it once and symlink it to each tool name we want wrapped (`npm`, `npx`, `pnpm`, `yarn`, `uv`, `uvx`, `pip`, `pipx`, `cargo`). The symlink directory is prepended to `$PATH` ahead of every other directory that contains a real `npm`, `uv`, etc.

When invoked, `_dispatch`:

1. Uses `${0##*/}` to learn its invocation name (e.g. `npm`).
2. Walks `$PATH` and finds the *next* executable with that name, skipping any entry that resolves to itself.
3. Re-execs the real binary under `sfw "$real" "$@"`.

So when you type `npm install foo` — or a Makefile rule says `npm install` — the OS resolves `npm` to `~/.sfw-wrappers/npm`, the wrapper finds the real `npm` (e.g. `/usr/bin/npm`), and runs it through Socket Firewall transparently.

## Install

```bash
# 1. Drop the dispatch script.
mkdir -p ~/.sfw-wrappers
install -m 755 wrappers/_dispatch ~/.sfw-wrappers/_dispatch

# 2. Symlink it under every tool name to wrap.
cd ~/.sfw-wrappers
for t in npm npx pnpm yarn uv uvx pip pipx cargo; do
    ln -sf _dispatch "$t"
done

# 3. Prepend ~/.sfw-wrappers to PATH. Append to your shell rc AFTER any
#    existing PATH manipulation so the wrapper dir ends up at PATH[0].
echo 'export PATH="$HOME/.sfw-wrappers:$PATH"' >> ~/.zshrc   # or ~/.bashrc

# 4. Reload the shell. From a new terminal:
which npm        # should be ~/.sfw-wrappers/npm
npm --version    # should print 'Protected by Socket Firewall' then the version
```

## Verify it routes correctly

```bash
which -a npm           # wrapper listed first, real npm second
~/.sfw-wrappers/_dispatch </dev/null 2>&1 | head -1
                       # expect: 'sfw-wrap: no real ... found' (self-test ok)
npm --version          # should show sfw banner
```

## Fail-open behaviour

The dispatch script falls through to the real binary with a warning if `sfw` is missing on the system, so a broken sfw install doesn't break every install command on the box. Flip that to a hard fail by replacing the `command -v sfw` branch with `exit 1` in `_dispatch`.

## Removal

```bash
sed -i '/sfw-wrappers/d' ~/.zshrc
rm -rf ~/.sfw-wrappers
```

## What's still uncovered

Even with the wrappers in place:

- **Full-path invocations** (`/usr/bin/npm install foo`) skip PATH lookup entirely.
- **Vendored copies** (`./node_modules/.bin/npm`) run from a project-local path.
- **Binaries that fetch packages themselves** (Go-style installers, compiled tools that call registry HTTP APIs) don't shell out to a wrapped tool.

For those, the only real defence is running unknown installers inside a sandbox.
