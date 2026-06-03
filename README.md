# Security Lab Telegram Bot

A Telegram bot that generates safe test `.exe` files for security lab research. Each file simulates suspicious-but-harmless behaviour (IoC indicators) for AV/EDR testing in isolated environments.

## Run & Operate

- **Telegram Bot** workflow runs `python3 bot.py` — this is the main service.
- Required env secret: `TELEGRAM_BOT_TOKEN` (set in Replit Secrets)
- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages

## Stack

- Python 3.11 + python-telegram-bot v22+
- PyInstaller (compiles .py scripts → .exe)
- pnpm workspaces, Node.js 24, TypeScript 5.9 (API server)
- API: Express 5

## Where things live

- `bot.py` — main Telegram bot, all logic in one file
- `pyproject.toml` — Python dependencies (python-telegram-bot, pyinstaller)
- `artifacts/api-server/` — Express API server (health check etc.)

## Architecture decisions

- All bot state (webhook URL, generation counter) is in-process memory — restarts reset it.
- Each `.exe` is compiled in a `tempfile.mkdtemp()` directory that is deleted after sending.
- Script uniqueness is achieved via UUID-seeded variable names + random comment injections, ensuring each generated file has a different hash.
- The `telegram==0.0.1` stub package conflicts with `python-telegram-bot` — it must NOT be added to `pyproject.toml` dependencies (uv will reinstall it automatically if listed).

## Product

7 behaviour profiles accessible via `/generate`:
1. **Network activity** — HTTP POST requests to a configurable webhook
2. **Keylogger simulation** — writes fake key events to a local file (no real interception)
3. **File copy** — copies files into a `lab_copies/` directory with LAB_ prefix
4. **File download** — downloads a URL to disk (dropper simulation)
5. **Self-copy** — copies the executable to another path (spreader simulation)
6. **Popup windows** — shows 3 MessageBox dialogs via ctypes
7. **Combo** — random mix of the above

## User preferences

- Language: Ukrainian (бот повністю на українській мові)
- Target runtime: Windows (exe files, ctypes.windll, etc.)

## Gotchas

- **Do NOT add `telegram>=0.0.1` to `pyproject.toml`** — it conflicts with python-telegram-bot by overwriting `telegram/__init__.py`. If it appears, run `uv sync` to remove it.
- PyInstaller must be installed (`pyinstaller` in pyproject.toml) for `/generate` to work.
- PyInstaller on Replit builds Linux ELF binaries, not Windows `.exe` — for real Windows executables the bot must run on a Windows host or use Wine + PyInstaller.
- After any `uv add` or `installLanguagePackages` call, verify `telegram/__init__.py` still exists.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
