"""
Telegram Security Lab Bot
=========================
Генерує безпечні тестові .exe файли для навчальних цілей.
Компіляція: Go cross-compilation (GOOS=windows) → справжні Windows PE-файли.
"""

import asyncio
import os
import random
import secrets
import shutil
import string
import subprocess
import tempfile
import uuid

import httpx
import py7zr
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------------------------------------------------------------------------
# Стан ConversationHandler
# ---------------------------------------------------------------------------
CHOOSE_PROFILE, GET_PARAMS = range(2)

# ---------------------------------------------------------------------------
# Профілі поведінки
# ---------------------------------------------------------------------------
PROFILES = {
    "net":      "🌐 Тест мережевої активності (HTTP-запити)",
    "keylog":   "⌨️ Тест запису подій клавіатури",
    "filecopy": "📁 Тест копіювання файлів із позначкою",
    "download": "⬇️ Тест завантаження зовнішнього файлу",
    "selfcopy": "🔄 Тест самокопіювання",
    "popup":    "🪟 Тест спливаючих вікон",
    "combo":    "🎲 Комбінований тест (випадковий мікс)",
}

# ---------------------------------------------------------------------------
# Стан
# ---------------------------------------------------------------------------
STATE: dict = {
    "webhook_url": "https://webhook.site/test",
    "generated_count": 0,
}

# ---------------------------------------------------------------------------
# Анімація прогресу
# ---------------------------------------------------------------------------
SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

PROGRESS_STAGES = [
    ("🔬", "Аналіз параметрів"),
    ("📝", "Генерую Go-код"),
    ("🔨", "Компіляція під Windows"),
    ("🔒", "Архівування з паролем"),
    ("☁️",  "Завантаження на сервер"),
]


def _build_bar(current: int, total: int, width: int = 10) -> str:
    filled = int((current / max(total - 1, 1)) * width)
    return f"[{'█' * filled}{'░' * (width - filled)}] {int((current / max(total - 1, 1)) * 100)}%"


async def _animate_progress(msg: Message, stop_event: asyncio.Event) -> None:
    stage_idx = 0
    spin_idx = 0
    total = len(PROGRESS_STAGES)

    while not stop_event.is_set():
        spin = SPINNER[spin_idx % len(SPINNER)]
        lines = []
        for i, (e, l) in enumerate(PROGRESS_STAGES):
            if i < stage_idx:
                lines.append(f"  ✅ {e} {l}")
            elif i == stage_idx:
                lines.append(f"  {spin} {e} {l}...")
            else:
                lines.append(f"  ▫️ {e} {l}")

        text = (
            f"⚙️ <b>Генерація тестового файлу</b>\n\n"
            f"{chr(10).join(lines)}\n\n"
            f"{_build_bar(stage_idx, total)}"
        )
        try:
            await msg.edit_text(text, parse_mode="HTML")
        except Exception:
            pass

        spin_idx += 1
        if spin_idx % 3 == 0 and stage_idx < total - 1:
            stage_idx += 1
        await asyncio.sleep(0.8)


# ---------------------------------------------------------------------------
# Go-шаблони для кожного профілю
# ---------------------------------------------------------------------------
# Кожен шаблон отримує унікальний UUID (const _labUID) → різний хеш файлу.
# Збірка: GOOS=windows GOARCH=amd64 CGO_ENABLED=0 → справжній Windows PE.

def _uid() -> str:
    return uuid.uuid4().hex


def _gostr(s: str) -> str:
    """Конвертує Python-рядок у Go string literal з подвійними лапками."""
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _go_net(webhook_url: str, interval: int = 5, count: int = 3) -> str:
    uid = _uid()
    salt = "".join(random.choices(string.ascii_letters, k=8))
    return f"""\
package main

// uid={uid} salt={salt}
// THIS FILE IS SAFE - FOR ISOLATED LAB USE ONLY

import (
\t"bytes"
\t"fmt"
\t"net/http"
\t"time"
)

const _labUID = "{uid}"

func main() {{
\turl := {_gostr(webhook_url)}
\tcount := {count}
\tinterval := {interval}

\tfor i := 0; i < count; i++ {{
\t\tpayload := fmt.Sprintf("lab_test_%s_%d", _labUID, i)
\t\thttp.Post(url, "application/octet-stream", bytes.NewBufferString(payload)) //nolint
\t\ttime.Sleep(time.Duration(interval) * time.Second)
\t}}
}}
"""


def _go_keylog(log_path: str = "keylog_test.txt", duration: int = 10) -> str:
    uid = _uid()
    salt = "".join(random.choices(string.ascii_letters, k=8))
    return f"""\
package main

// uid={uid} salt={salt}
// THIS FILE IS SAFE - FOR ISOLATED LAB USE ONLY

import (
\t"fmt"
\t"os"
\t"time"
)

const _labUID = "{uid}"

var _keys = []string{{"LAB_KEY_A", "LAB_KEY_B", "LAB_KEY_CTRL", "LAB_KEY_ENTER"}}

func main() {{
\tf, _ := os.Create({_gostr(log_path)})
\tdefer f.Close()

\tfor i := 0; i < {duration}; i++ {{
\t\tkey := _keys[i%len(_keys)]
\t\tfmt.Fprintf(f, "[%s] %s uid=%s\\n", time.Now().Format("15:04:05"), key, _labUID)
\t\tf.Sync()
\t\ttime.Sleep(500 * time.Millisecond)
\t}}
}}
"""


def _go_filecopy(src_dir: str = ".", dst_dir: str = "lab_copies", n: int = 3) -> str:
    uid = _uid()
    salt = "".join(random.choices(string.ascii_letters, k=8))
    return f"""\
package main

// uid={uid} salt={salt}
// THIS FILE IS SAFE - FOR ISOLATED LAB USE ONLY

import (
\t"fmt"
\t"io"
\t"os"
\t"path/filepath"
\t"time"
)

const _labUID = "{uid}"

func copyFile(src, dst string) {{
\tin, err := os.Open(src)
\tif err != nil {{
\t\treturn
\t}}
\tdefer in.Close()
\tout, err := os.Create(dst)
\tif err != nil {{
\t\treturn
\t}}
\tdefer out.Close()
\tio.Copy(out, in) //nolint
}}

func main() {{
\tdstDir := {_gostr(dst_dir)}
\tos.MkdirAll(dstDir, 0755) //nolint

\tfor i := 0; i < {n}; i++ {{
\t\tsrc := fmt.Sprintf("lab_dummy_%s_%d.txt", _labUID[:6], i)
\t\tf, _ := os.Create(src)
\t\tfmt.Fprintf(f, "lab_content_%s_%d\\n", _labUID, i)
\t\tf.Close()

\t\tdst := filepath.Join(dstDir, "LAB_COPY_"+src)
\t\tcopyFile(src, dst)
\t\ttime.Sleep(200 * time.Millisecond)
\t}}
}}
"""


def _go_download(url: str, save_path: str = "lab_downloaded.bin") -> str:
    uid = _uid()
    salt = "".join(random.choices(string.ascii_letters, k=8))
    return f"""\
package main

// uid={uid} salt={salt}
// THIS FILE IS SAFE - FOR ISOLATED LAB USE ONLY

import (
\t"io"
\t"net/http"
\t"os"
)

const _labUID = "{uid}"

func main() {{
\turl := {_gostr(url)}
\tsavePath := {_gostr(save_path)}

\tresp, err := http.Get(url)
\tif err != nil {{
\t\tf, _ := os.Create(savePath)
\t\tf.WriteString("lab_download_failed uid=" + _labUID + ": " + err.Error())
\t\tf.Close()
\t\treturn
\t}}
\tdefer resp.Body.Close()

\tf, _ := os.Create(savePath)
\tdefer f.Close()
\tio.Copy(f, resp.Body) //nolint
}}
"""


def _go_selfcopy(dst_path: str = "lab_selfcopy.exe") -> str:
    uid = _uid()
    salt = "".join(random.choices(string.ascii_letters, k=8))
    return f"""\
package main

// uid={uid} salt={salt}
// THIS FILE IS SAFE - FOR ISOLATED LAB USE ONLY

import (
\t"io"
\t"os"
\t"time"
)

const _labUID = "{uid}"

func main() {{
\tdst := {_gostr(dst_path)}
\tself, err := os.Executable()
\tif err != nil {{
\t\treturn
\t}}

\tin, err := os.Open(self)
\tif err != nil {{
\t\treturn
\t}}
\tdefer in.Close()

\tout, err := os.Create(dst)
\tif err != nil {{
\t\treturn
\t}}
\tdefer out.Close()

\tio.Copy(out, in) //nolint
\t_ = _labUID
\ttime.Sleep(time.Second)
}}
"""


def _go_popup(message: str = "Lab Security Test") -> str:
    uid = _uid()
    salt = "".join(random.choices(string.ascii_letters, k=8))
    # Escape для Go рядка
    safe_msg = message.replace('"', '\\"')
    return f"""\
package main

// uid={uid} salt={salt}
// THIS FILE IS SAFE - FOR ISOLATED LAB USE ONLY

import (
\t"fmt"
\t"syscall"
\t"time"
\t"unsafe"
)

const _labUID = "{uid}"

var (
\tmodUser32  = syscall.NewLazyDLL("user32.dll")
\tmsgBoxProc = modUser32.NewProc("MessageBoxW")
)

func messageBox(caption, title string) {{
\tcap, _ := syscall.UTF16PtrFromString(caption)
\ttit, _ := syscall.UTF16PtrFromString(title)
\tmsgBoxProc.Call(0, uintptr(unsafe.Pointer(cap)), uintptr(unsafe.Pointer(tit)), 0x40)
}}

func main() {{
\tmsg := "{safe_msg}"
\tfor i := 0; i < 3; i++ {{
\t\tcaption := fmt.Sprintf("%s #%s-%d", msg, _labUID[:6], i)
\t\tmessageBox(caption, "Security Lab Test")
\t\ttime.Sleep(time.Second)
\t}}
}}
"""


def _go_combo(webhook_url: str) -> str:
    uid = _uid()
    salt = "".join(random.choices(string.ascii_letters, k=8))
    return f"""\
package main

// uid={uid} salt={salt}
// THIS FILE IS SAFE - FOR ISOLATED LAB USE ONLY - COMBO

import (
\t"bytes"
\t"fmt"
\t"io"
\t"net/http"
\t"os"
\t"path/filepath"
\t"time"
)

const _labUID = "{uid}"

func copyFile(src, dst string) {{
\tin, _ := os.Open(src)
\tdefer in.Close()
\tout, _ := os.Create(dst)
\tdefer out.Close()
\tio.Copy(out, in) //nolint
}}

func doNetwork() {{
\tfor i := 0; i < 2; i++ {{
\t\tpayload := fmt.Sprintf("lab_combo_%s_%d", _labUID, i)
\t\thttp.Post({_gostr(webhook_url)}, "application/octet-stream", bytes.NewBufferString(payload)) //nolint
\t\ttime.Sleep(2 * time.Second)
\t}}
}}

func doCopy() {{
\tos.MkdirAll("lab_copies", 0755) //nolint
\tfor i := 0; i < 2; i++ {{
\t\tsrc := fmt.Sprintf("lab_dummy_%s_%d.txt", _labUID[:6], i)
\t\tf, _ := os.Create(src)
\t\tfmt.Fprintf(f, "lab_content_%s\\n", _labUID)
\t\tf.Close()
\t\tcopyFile(src, filepath.Join("lab_copies", "LAB_COPY_"+src))
\t\ttime.Sleep(200 * time.Millisecond)
\t}}
}}

func doSelfCopy() {{
\tself, _ := os.Executable()
\tin, _ := os.Open(self)
\tdefer in.Close()
\tout, _ := os.Create("lab_combo_copy.exe")
\tdefer out.Close()
\tio.Copy(out, in) //nolint
}}

func main() {{
\tgo doNetwork()
\ttime.Sleep(500 * time.Millisecond)
\tdoCopy()
\tdoSelfCopy()
\ttime.Sleep(3 * time.Second)
}}
"""


# ---------------------------------------------------------------------------
# Побудова Go-коду за профілем
# ---------------------------------------------------------------------------

def build_go_code(profile: str, params: dict) -> str:
    webhook = params.get("webhook", STATE["webhook_url"])
    builders = {
        "net":      lambda: _go_net(
            webhook_url=webhook,
            interval=int(params.get("interval", 5)),
            count=int(params.get("count", 3)),
        ),
        "keylog":   lambda: _go_keylog(
            log_path=params.get("log_path", "keylog_test.txt"),
            duration=int(params.get("duration", 10)),
        ),
        "filecopy": lambda: _go_filecopy(
            src_dir=params.get("src_dir", "."),
            dst_dir=params.get("dst_dir", "lab_copies"),
            n=int(params.get("n", 3)),
        ),
        "download": lambda: _go_download(
            url=params.get("url", webhook),
            save_path=params.get("save_path", "lab_downloaded.bin"),
        ),
        "selfcopy": lambda: _go_selfcopy(
            dst_path=params.get("dst_path", "lab_selfcopy.exe"),
        ),
        "popup":    lambda: _go_popup(
            message=params.get("message", "Lab Security Test"),
        ),
        "combo":    lambda: _go_combo(webhook_url=webhook),
    }
    if profile not in builders:
        raise ValueError(f"Unknown profile: {profile}")
    return builders[profile]()


# ---------------------------------------------------------------------------
# Компіляція: Go → справжній Windows PE (блокуюча, запускається в executor)
# ---------------------------------------------------------------------------

def compile_go_exe_sync(go_code: str, work_dir: str, binary_name: str) -> str:
    """
    Компілює Go-код у Windows PE-файл.
    GOOS=windows GOARCH=amd64 CGO_ENABLED=0 → справжній .exe без залежностей.
    """
    go_cmd = shutil.which("go")
    if not go_cmd:
        raise RuntimeError(
            "Go не знайдено. Переконайтесь, що Go встановлено у середовищі."
        )

    src_dir = os.path.join(work_dir, "gosrc")
    os.makedirs(src_dir, exist_ok=True)

    # Записуємо main.go
    main_go = os.path.join(src_dir, "main.go")
    with open(main_go, "w", encoding="utf-8") as f:
        f.write(go_code)

    # go mod init
    mod_result = subprocess.run(
        [go_cmd, "mod", "init", f"lab_{binary_name}"],
        cwd=src_dir, capture_output=True, text=True,
    )
    if mod_result.returncode != 0:
        raise RuntimeError(f"go mod init: {mod_result.stderr}")

    # Шлях вихідного .exe
    exe_path = os.path.join(work_dir, binary_name + ".exe")

    # Cross-compile → Windows PE
    env = {
        **os.environ,
        "GOOS":        "windows",
        "GOARCH":      "amd64",
        "CGO_ENABLED": "0",
    }
    build_result = subprocess.run(
        [go_cmd, "build",
         "-ldflags", "-H windowsgui -s -w",   # без консолі, стриппнуті символи
         "-o", exe_path,
         "."],
        cwd=src_dir, capture_output=True, text=True, env=env,
    )
    if build_result.returncode != 0:
        raise RuntimeError(
            f"go build error:\n{build_result.stderr[-2000:]}"
        )

    if not os.path.exists(exe_path):
        raise RuntimeError("Файл .exe не знайдено після компіляції.")

    return exe_path


# ---------------------------------------------------------------------------
# Пароль та 7z-архів
# ---------------------------------------------------------------------------

def generate_password(length: int = 16) -> str:
    return "".join(secrets.choice(string.ascii_letters + string.digits)
                   for _ in range(length))


def create_7z_archive(exe_path: str, archive_path: str, password: str) -> None:
    with py7zr.SevenZipFile(archive_path, mode="w", password=password) as archive:
        archive.write(exe_path, arcname=os.path.basename(exe_path))


# ---------------------------------------------------------------------------
# Завантаження на Gofile.io
# ---------------------------------------------------------------------------

async def upload_file(file_path: str) -> str:
    fname = os.path.basename(file_path)
    errors: list[str] = []

    # --- 1. Gofile.io ---
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            srv_resp = await client.get("https://api.gofile.io/servers")
            srv_data = srv_resp.json()
            if srv_data.get("status") != "ok":
                raise RuntimeError(f"Gofile /servers: {srv_data}")
            server = srv_data["data"]["servers"][0]["name"]
            with open(file_path, "rb") as f:
                up_resp = await client.post(
                    f"https://{server}.gofile.io/contents/uploadfile",
                    files={"file": (fname, f, "application/octet-stream")},
                )
        up_data = up_resp.json()
        if up_data.get("status") == "ok":
            return up_data["data"]["downloadPage"]
        errors.append(f"Gofile upload: {up_data}")
    except Exception as e:
        errors.append(f"Gofile: {e}")

    # --- 2. litterbox.catbox.moe (резерв) ---
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            with open(file_path, "rb") as f:
                resp = await client.post(
                    "https://litterbox.catbox.moe/resources/internals/api.php",
                    data={"reqtype": "fileupload", "time": "72h"},
                    files={"fileToUpload": (fname, f, "application/octet-stream")},
                )
        if resp.status_code == 200:
            url = resp.text.strip()
            if url.startswith("http"):
                return url
        errors.append(f"catbox.moe: HTTP {resp.status_code}")
    except Exception as e:
        errors.append(f"catbox.moe: {e}")

    raise RuntimeError("Не вдалося завантажити файл:\n" + "\n".join(errors))


# ---------------------------------------------------------------------------
# Обробники команд
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🔬 <b>Security Lab Bot</b>\n\n"
        "Генерую безпечні тестові <code>.exe</code> файли для лабораторного стенду.\n"
        "Файли — справжні Windows PE, не потребують Python на цільовій машині.\n\n"
        "<b>⚠️ УВАГА:</b> Лише для ізольованого лабораторного середовища!\n\n"
        "<b>Команди:</b>\n"
        "/generate — створити тестовий .exe\n"
        "/setwebhook &lt;URL&gt; — задати вебхук\n"
        "/status — поточний стан"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        f"📊 <b>Статус бота</b>\n\n"
        f"🌐 Вебхук: <code>{STATE['webhook_url']}</code>\n"
        f"📦 Згенеровано файлів: <b>{STATE['generated_count']}</b>"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_set_webhook(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not ctx.args:
        await update.message.reply_text(
            "Використання: /setwebhook <URL>\nПриклад: /setwebhook https://webhook.site/abc123"
        )
        return
    url = ctx.args[0]
    if not url.startswith("http"):
        await update.message.reply_text("❌ URL повинен починатися з http:// або https://")
        return
    STATE["webhook_url"] = url
    await update.message.reply_text(f"✅ Вебхук збережено: <code>{url}</code>", parse_mode="HTML")


# ---------------------------------------------------------------------------
# ConversationHandler — /generate
# ---------------------------------------------------------------------------

async def cmd_generate(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton(label, callback_data=key)]
        for key, label in PROFILES.items()
    ]
    await update.message.reply_text(
        "🛠 <b>Оберіть профіль поведінки тестового файлу:</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return CHOOSE_PROFILE


async def profile_chosen(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    profile = query.data
    ctx.user_data["profile"] = profile
    label = PROFILES.get(profile, profile)

    hints = {
        "net": (
            "Введіть параметри або <code>default</code>:\n"
            "• <code>webhook=URL</code>\n"
            "• <code>interval=сек</code> (default: 5)\n"
            "• <code>count=N</code> (default: 3)\n\n"
            "<i>Приклад: webhook=https://my.site interval=3 count=5</i>"
        ),
        "keylog": (
            "Введіть параметри або <code>default</code>:\n"
            "• <code>log_path=шлях</code> (default: keylog_test.txt)\n"
            "• <code>duration=N</code> записів (default: 10)\n\n"
            "<i>Приклад: log_path=C:\\\\lab\\\\log.txt duration=20</i>"
        ),
        "filecopy": (
            "Введіть параметри або <code>default</code>:\n"
            "• <code>src_dir=шлях</code> (default: .)\n"
            "• <code>dst_dir=шлях</code> (default: lab_copies)\n"
            "• <code>n=N</code> файлів (default: 3)\n\n"
            "<i>Приклад: dst_dir=C:\\\\lab\\\\copies n=5</i>"
        ),
        "download": (
            "Введіть параметри або <code>default</code>:\n"
            "• <code>url=URL</code> — джерело\n"
            "• <code>save_path=шлях</code> (default: lab_downloaded.bin)\n\n"
            "<i>Приклад: url=https://example.com/file.bin</i>"
        ),
        "selfcopy": (
            "Введіть параметри або <code>default</code>:\n"
            "• <code>dst_path=шлях</code> (default: lab_selfcopy.exe)\n\n"
            "<i>Приклад: dst_path=C:\\\\lab\\\\copy.exe</i>"
        ),
        "popup": (
            "Введіть параметри або <code>default</code>:\n"
            "• <code>message=текст</code> (default: Lab Security Test)\n\n"
            "<i>Приклад: message=Тест безпеки лабораторії</i>"
        ),
        "combo": (
            "Комбінований тест — введіть <code>default</code> або:\n"
            "• <code>webhook=URL</code>\n\n"
            "<i>Приклад: default</i>"
        ),
    }

    prompt = hints.get(profile, "Введіть параметри або <code>default</code>:")
    await query.edit_message_text(
        f"✅ Обрано: <b>{label}</b>\n\n{prompt}",
        parse_mode="HTML",
    )
    return GET_PARAMS


async def receive_params(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    profile = ctx.user_data.get("profile", "net")
    params: dict = {}

    if text.lower() != "default":
        for token in text.split():
            if "=" in token:
                k, _, v = token.partition("=")
                params[k.strip()] = v.strip()

    prog_msg = await update.message.reply_text(
        "⚙️ <b>Запуск генерації...</b>", parse_mode="HTML"
    )

    stop_event = asyncio.Event()
    loop = asyncio.get_event_loop()
    work_dir = tempfile.mkdtemp(prefix="seclab_")

    anim_task = asyncio.create_task(_animate_progress(prog_msg, stop_event))

    try:
        # 1. Генеруємо Go-код
        go_code = build_go_code(profile, params)
        binary_name = f"lab_{profile}_{uuid.uuid4().hex[:6]}"

        # 2. Компілюємо → Windows PE
        exe_path = await loop.run_in_executor(
            None, compile_go_exe_sync, go_code, work_dir, binary_name
        )

        # 3. Генеруємо пароль + 7z архів
        password = generate_password()
        archive_path = os.path.join(work_dir, binary_name + ".7z")
        await loop.run_in_executor(
            None, create_7z_archive, exe_path, archive_path, password
        )

        # 4. Завантажуємо на Gofile
        download_url = await upload_file(archive_path)

        # Зупиняємо анімацію
        stop_event.set()
        await anim_task

        # Фінальний прогрес
        done_lines = "\n".join(f"  ✅ {e} {l}" for e, l in PROGRESS_STAGES)
        await prog_msg.edit_text(
            f"⚙️ <b>Генерація тестового файлу</b>\n\n"
            f"{done_lines}\n\n[{'█' * 10}] 100%",
            parse_mode="HTML",
        )

        STATE["generated_count"] += 1
        profile_label = PROFILES[profile]

        await ctx.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"✅ <b>Готово! Файл #{STATE['generated_count']}</b>\n"
                f"Профіль: <b>{profile_label}</b>\n\n"
                f"📥 <b>Посилання (Gofile):</b>\n"
                f"{download_url}\n\n"
                f"🔑 <b>Пароль до архіву:</b>\n"
                f"<code>{password}</code>\n\n"
                f"<i>ℹ️ Архів 7z (AES-256). "
                f"Справжній Windows .exe — не потребує Python.</i>\n\n"
                f"⚠️ <i>Запускайте лише в ізольованому середовищі!</i>"
            ),
            parse_mode="HTML",
        )

    except RuntimeError as e:
        stop_event.set()
        await anim_task
        await prog_msg.edit_text(
            f"❌ <b>Помилка генерації</b>\n\n<code>{str(e)[:800]}</code>",
            parse_mode="HTML",
        )
    except Exception as e:
        stop_event.set()
        await anim_task
        await prog_msg.edit_text(
            f"❌ <b>Несподівана помилка</b>\n\n<code>{e}</code>",
            parse_mode="HTML",
        )
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    return ConversationHandler.END


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Генерацію скасовано.")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Точка входу
# ---------------------------------------------------------------------------

def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise EnvironmentError("TELEGRAM_BOT_TOKEN не задано у Secrets.")

    app = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("generate", cmd_generate)],
        states={
            CHOOSE_PROFILE: [CallbackQueryHandler(profile_chosen)],
            GET_PARAMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_params)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("setwebhook", cmd_set_webhook))
    app.add_handler(conv_handler)

    print("🤖 Bot started (Go/Windows compiler). Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
