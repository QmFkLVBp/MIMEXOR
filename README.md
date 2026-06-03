# 🛡️ Security Lab Telegram Bot

<p align="center">
  Telegram bot for generating safe test binaries with suspicious-looking IoCs for AV/EDR lab validation.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white" alt="Python 3.11">
  <img src="https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram&logoColor=white" alt="Telegram Bot">
  <img src="https://img.shields.io/badge/PyInstaller-6.x-orange" alt="PyInstaller">
  <img src="https://img.shields.io/badge/Platform-Windows%20Target-success" alt="Windows Target">
</p>

---

## ✨ Highlights

- ⚙️ Generates `.exe` artifacts for isolated security testing.
- 🧪 Emulates suspicious behavior safely (no real harmful payloads).
- 🔁 Produces unique output each run using UUID/randomized script internals.
- 🇺🇦 Bot UI and messages are in Ukrainian.

## 📊 Repo Widgets

<p align="center">
  <img src="https://img.shields.io/github/repo-size/QmFkLVBp/MIMEXOR" alt="Repo Size">
  <img src="https://img.shields.io/github/last-commit/QmFkLVBp/MIMEXOR" alt="Last Commit">
  <img src="https://img.shields.io/github/languages/top/QmFkLVBp/MIMEXOR" alt="Top Language">
  <img src="https://img.shields.io/github/issues/QmFkLVBp/MIMEXOR" alt="Open Issues">
</p>

## 🧩 Supported Behavior Profiles (`/generate`)

1. **Network activity** — HTTP POST requests to a configurable webhook  
2. **Keylogger simulation** — writes fake key events to local file  
3. **File copy** — copies files to `lab_copies/` with `LAB_` prefix  
4. **File download** — downloads a URL to disk (dropper-style simulation)  
5. **Self-copy** — copies executable to another path  
6. **Popup windows** — shows MessageBox dialogs via `ctypes`  
7. **Combo** — randomized mix of multiple profiles

## 🗂️ Project Structure

| Path | Purpose |
|---|---|
| `bot.py` | Main Telegram bot logic |
| `pyproject.toml` | Python dependencies and project metadata |
| `artifacts/api-server/` | API server artifact location (health checks etc.) |

## 🛠️ Cool Tools & Stack

- **python-telegram-bot v22+** — bot interaction layer
- **PyInstaller** — script → executable packaging
- **Python 3.11** — runtime
- **pnpm workspaces + Node.js 24 + TypeScript 5.9** — supporting workspace/API tooling
- **Express 5** — API server

## 🚀 Run & Operate

- Main runtime: `python3 bot.py`
- Required secret: `TELEGRAM_BOT_TOKEN`
- API server: `pnpm --filter @workspace/api-server run dev`
- Type check workspace: `pnpm run typecheck`

## 🧠 Architecture Notes

- Bot state (webhook URL, generation counter) is in-memory only.
- Every build runs in an isolated temp directory via `tempfile.mkdtemp()`.
- Temporary build folders are removed after file delivery.
- Hash uniqueness is improved through UUID-based names and random comment injection.

## ⚠️ Important Gotchas

- **Never add `telegram>=0.0.1`** to dependencies (conflicts with `python-telegram-bot`).
- `pyinstaller` must be present for `/generate` to produce artifacts.
- Replit/Linux build hosts produce ELF binaries; true Windows `.exe` generation needs Windows host (or Wine-based pipeline).
- After package operations (`uv add`, install hooks), verify `telegram/__init__.py` remains intact.

## 📌 Pointers

- For workspace package structure and TS setup, refer to the `pnpm-workspace` skill notes.
