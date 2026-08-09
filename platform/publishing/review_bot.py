#!/usr/bin/env python3
"""Telegram-бот редакторского ревью комиксов OpenCity с long polling."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ISSUES_DIR = ROOT / "productions/issues"
STATE_PATH = ROOT / "var/review-bot/state.json"
REVIEW_SCHEMA = "../../../studio-os/contracts/comic-review.schema.json"


class BotError(RuntimeError):
    """Ошибка Telegram Bot API или локальной конфигурации."""


def load_local_env(path: Path) -> None:
    """Загружает простые KEY=VALUE из локального .env без внешней зависимости."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def update_local_env(path: Path, values: dict[str, str]) -> None:
    """Обновляет выбранные значения .env, сохраняя остальные строки без изменений."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    pending = dict(values)
    updated: list[str] = []
    for raw_line in lines:
        stripped = raw_line.strip()
        candidate = stripped[7:].lstrip() if stripped.startswith("export ") else stripped
        key = candidate.split("=", 1)[0].strip() if "=" in candidate else ""
        if key in pending:
            prefix = "export " if stripped.startswith("export ") else ""
            updated.append(f"{prefix}{key}={pending.pop(key)}")
        else:
            updated.append(raw_line)
    if pending and updated and updated[-1]:
        updated.append("")
    updated.extend(f"{key}={value}" for key, value in pending.items())
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("\n".join(updated) + "\n", encoding="utf-8")
    if path.exists():
        temporary.chmod(path.stat().st_mode)
    temporary.replace(path)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def issue_directory(issue_id: str) -> Path:
    if not issue_id.startswith("issue-") or not issue_id[6:].isdigit():
        raise BotError(f"Некорректный номер выпуска: {issue_id}")
    directory = ISSUES_DIR / issue_id
    if not directory.is_dir():
        raise BotError(f"Выпуск не найден: {issue_id}")
    return directory


def load_issue(issue_id: str) -> tuple[Path, dict[str, Any], dict[str, Any], Path, str]:
    directory = issue_directory(issue_id)
    issue_path = directory / "issue.json"
    manifest_path = directory / "manifest.json"
    issue = json.loads(issue_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    master = directory / issue["canonical_files"]["art_master"]
    if not master.exists():
        raise BotError(f"Визуальный мастер не найден: {master}")
    digest = sha256(master)
    declared = manifest.get("outputs", [{}])[0].get("sha256")
    if declared != digest:
        raise BotError("Хэш мастера не совпадает с manifest.json; сначала выполните make validate")
    return directory, issue, manifest, master, digest


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def review_record(
    issue_id: str,
    decision: str,
    digest: str,
    comment: str | None,
    decided_at: str | None = None,
) -> dict[str, Any]:
    if decision not in {"approved", "changes_requested"}:
        raise BotError(f"Неизвестное решение: {decision}")
    return {
        "$schema": REVIEW_SCHEMA,
        "issue": issue_id,
        "decision": decision,
        "master_sha256": digest,
        "reviewer_role": "showrunner",
        "decided_at": decided_at or datetime.now(UTC).isoformat(),
        "source": "telegram_editorial_chat",
        "comment": comment,
    }


def apply_decision(
    issue_id: str,
    decision: str,
    comment: str | None = None,
    *,
    base_directory: Path | None = None,
    decided_at: str | None = None,
) -> dict[str, Any]:
    directory = base_directory or issue_directory(issue_id)
    issue_path = directory / "issue.json"
    manifest_path = directory / "manifest.json"
    issue = json.loads(issue_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    master = directory / issue["canonical_files"]["art_master"]
    digest = sha256(master)
    record = review_record(issue_id, decision, digest, comment, decided_at)
    new_status = "approved" if decision == "approved" else "ready_for_review"
    issue["status"] = new_status
    manifest["status"] = new_status
    atomic_json(directory / "review.json", record)
    atomic_json(issue_path, issue)
    atomic_json(manifest_path, manifest)
    return record


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"offset": 0, "pending_comments": {}}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    atomic_json(STATE_PATH, state)


def multipart(fields: dict[str, str], file_field: str, file_path: Path) -> tuple[bytes, str]:
    boundary = f"----OpenCity{secrets.token_hex(12)}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
            value.encode("utf-8"),
            b"\r\n",
        ])
    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    chunks.extend([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'.encode(),
        f"Content-Type: {mime}\r\n\r\n".encode(),
        file_path.read_bytes(),
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ])
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


class TelegramBot:
    def __init__(self, token: str) -> None:
        if not token:
            raise BotError("Не задан TELEGRAM_REVIEW_BOT_TOKEN")
        self.base_url = f"https://api.telegram.org/bot{token}"

    def call(self, method: str, payload: dict[str, Any] | None = None) -> Any:
        data = urllib.parse.urlencode(payload or {}).encode("utf-8")
        request = urllib.request.Request(f"{self.base_url}/{method}", data=data)
        try:
            with urllib.request.urlopen(request, timeout=70) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as exc:
            raise BotError(f"Telegram API недоступен: {exc}") from exc
        if not result.get("ok"):
            raise BotError(f"Telegram API {method}: {result.get('description', 'неизвестная ошибка')}")
        return result["result"]

    def send_photo(self, chat_id: str, photo: Path, caption: str, keyboard: dict[str, Any]) -> dict[str, Any]:
        body, content_type = multipart(
            {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML", "reply_markup": json.dumps(keyboard, ensure_ascii=False)},
            "photo",
            photo,
        )
        request = urllib.request.Request(
            f"{self.base_url}/sendPhoto",
            data=body,
            headers={"Content-Type": content_type},
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as exc:
            raise BotError(f"Не удалось отправить мастер: {exc}") from exc
        if not result.get("ok"):
            raise BotError(f"sendPhoto: {result.get('description', 'неизвестная ошибка')}")
        return result["result"]


def allowed_reviewers() -> set[int]:
    raw = os.environ.get("TELEGRAM_REVIEWER_USER_IDS", "")
    try:
        values = {int(value.strip()) for value in raw.split(",") if value.strip()}
    except ValueError as exc:
        raise BotError("TELEGRAM_REVIEWER_USER_IDS должен содержать числовые ID через запятую") from exc
    if not values:
        raise BotError("Не задан TELEGRAM_REVIEWER_USER_IDS")
    return values


def callback_data(action: str, issue_id: str, digest: str) -> str:
    return f"oc:{action}:{issue_id[6:]}:{digest[:12]}"


def parse_callback(value: str) -> tuple[str, str, str]:
    parts = value.split(":")
    if len(parts) != 4 or parts[0] != "oc" or parts[1] not in {"approve", "changes"}:
        raise BotError("Неизвестная кнопка ревью")
    return parts[1], f"issue-{parts[2]}", parts[3]


def submit(bot: TelegramBot, issue_id: str, chat_id: str) -> dict[str, Any]:
    _, issue, _, master, digest = load_issue(issue_id)
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Одобрить", "callback_data": callback_data("approve", issue_id, digest)},
            {"text": "✏️ Нужны правки", "callback_data": callback_data("changes", issue_id, digest)},
        ]]
    }
    caption = (
        f"<b>Редакторское ревью · выпуск {issue_id[6:]}</b>\n"
        f"<b>{issue['title']}</b>\n\n"
        f"{issue['premise']}\n\n"
        f"Панелей: {issue['format']['panels']} · мастер: 2:3\n"
        f"SHA-256: <code>{digest[:12]}</code>\n\n"
        "Одобрение относится только к этому изображению. Публикация запускается отдельно."
    )
    return bot.send_photo(chat_id, master, caption, keyboard)


def authorize(update_user: dict[str, Any], reviewers: set[int]) -> bool:
    return int(update_user.get("id", 0)) in reviewers


def handle_callback(bot: TelegramBot, query: dict[str, Any], reviewers: set[int], chat_id: str, state: dict[str, Any]) -> None:
    if not authorize(query.get("from", {}), reviewers):
        bot.call("answerCallbackQuery", {"callback_query_id": query["id"], "text": "У вас нет права утверждать выпуск", "show_alert": "true"})
        return
    message = query.get("message") or {}
    message_chat = str((message.get("chat") or {}).get("id", ""))
    if message_chat != str(chat_id):
        bot.call("answerCallbackQuery", {"callback_query_id": query["id"], "text": "Это не редакторский чат", "show_alert": "true"})
        return
    action, issue_id, short_digest = parse_callback(query.get("data", ""))
    _, issue, _, _, digest = load_issue(issue_id)
    if not digest.startswith(short_digest):
        bot.call("answerCallbackQuery", {"callback_query_id": query["id"], "text": "Мастер уже изменён. Отправьте его на новое ревью.", "show_alert": "true"})
        return
    if action == "approve":
        apply_decision(issue_id, "approved")
        bot.call("answerCallbackQuery", {"callback_query_id": query["id"], "text": "Выпуск одобрен"})
        bot.call("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": message["message_id"], "reply_markup": json.dumps({"inline_keyboard": []})})
        bot.call("sendMessage", {"chat_id": chat_id, "reply_to_message_id": message["message_id"], "text": f"✅ Выпуск {issue_id[6:]} «{issue['title']}» одобрен. Публикация не запущена."})
        return
    prompt = bot.call(
        "sendMessage",
        {
            "chat_id": chat_id,
            "reply_to_message_id": message["message_id"],
            "text": f"✏️ Ответьте на это сообщение и перечислите правки для выпуска {issue_id[6:]}. Решение запишется после вашего ответа.",
            "reply_markup": json.dumps({"force_reply": True, "selective": True}),
        },
    )
    state["pending_comments"][str(prompt["message_id"])] = {
        "issue": issue_id,
        "digest": digest,
        "review_message_id": message["message_id"],
        "reviewer_id": query["from"]["id"],
    }
    save_state(state)
    bot.call("answerCallbackQuery", {"callback_query_id": query["id"], "text": "Жду список правок ответом"})


def handle_message(bot: TelegramBot, message: dict[str, Any], reviewers: set[int], chat_id: str, state: dict[str, Any]) -> None:
    if str((message.get("chat") or {}).get("id", "")) != str(chat_id):
        return
    if not authorize(message.get("from", {}), reviewers):
        return
    reply_id = str(((message.get("reply_to_message") or {}).get("message_id", "")))
    pending = state["pending_comments"].get(reply_id)
    comment = (message.get("text") or message.get("caption") or "").strip()
    if not pending or not comment or int(pending["reviewer_id"]) != int(message["from"]["id"]):
        return
    _, issue, _, _, digest = load_issue(pending["issue"])
    if digest != pending["digest"]:
        bot.call("sendMessage", {"chat_id": chat_id, "reply_to_message_id": message["message_id"], "text": "Мастер изменился до записи комментария. Отправьте новую версию на ревью."})
    else:
        apply_decision(pending["issue"], "changes_requested", comment)
        bot.call("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": pending["review_message_id"], "reply_markup": json.dumps({"inline_keyboard": []})})
        bot.call("sendMessage", {"chat_id": chat_id, "reply_to_message_id": message["message_id"], "text": f"📝 Правки для выпуска {pending['issue'][6:]} «{issue['title']}» записаны. Публикация заблокирована до нового ревью."})
    del state["pending_comments"][reply_id]
    save_state(state)


def run(bot: TelegramBot, chat_id: str, reviewers: set[int]) -> None:
    state = load_state()
    print("REVIEW BOT RUNNING: long polling", flush=True)
    while True:
        try:
            updates = bot.call(
                "getUpdates",
                {
                    "offset": state.get("offset", 0),
                    "timeout": 30,
                    "allowed_updates": json.dumps(["callback_query", "message"]),
                },
            )
            for update in updates:
                state["offset"] = update["update_id"] + 1
                if "callback_query" in update:
                    handle_callback(bot, update["callback_query"], reviewers, chat_id, state)
                elif "message" in update:
                    handle_message(bot, update["message"], reviewers, chat_id, state)
                save_state(state)
        except KeyboardInterrupt:
            print("\nREVIEW BOT STOPPED", flush=True)
            return
        except BotError as exc:
            print(f"Временная ошибка: {exc}", file=sys.stderr, flush=True)
            time.sleep(3)


def discover(bot: TelegramBot) -> None:
    updates = bot.call("getUpdates", {"timeout": 0, "allowed_updates": json.dumps(["message"])})
    found = []
    for update in updates:
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        sender = message.get("from") or {}
        if not chat or not sender:
            continue
        found.append(
            {
                "chat_title": chat.get("title") or chat.get("username") or chat.get("first_name"),
                "chat_id": chat.get("id"),
                "user_name": " ".join(filter(None, [sender.get("first_name"), sender.get("last_name")])),
                "username": sender.get("username"),
                "user_id": sender.get("id"),
                "text": message.get("text"),
            }
        )
    print(json.dumps(found, ensure_ascii=False, indent=2))
    if not found:
        print("Сообщения не найдены. Добавьте бота в чат, отправьте /review_setup и повторите discover.", file=sys.stderr)


def latest_private_sender(updates: list[dict[str, Any]]) -> tuple[str, str, str]:
    """Возвращает chat ID, user ID и безопасное отображаемое имя последнего личного сообщения."""
    for update in reversed(updates):
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        sender = message.get("from") or {}
        if chat.get("type") != "private" or sender.get("is_bot"):
            continue
        chat_id = chat.get("id")
        user_id = sender.get("id")
        if chat_id is None or user_id is None or int(chat_id) != int(user_id):
            continue
        name = f"@{sender['username']}" if sender.get("username") else " ".join(
            filter(None, [sender.get("first_name"), sender.get("last_name")])
        )
        return str(chat_id), str(user_id), name or "пользователь Telegram"
    raise BotError("Личное сообщение боту не найдено. Отправьте ему /start и повторите команду.")


def configure_private(bot: TelegramBot, env_path: Path) -> str:
    updates = bot.call("getUpdates", {"timeout": 0, "allowed_updates": json.dumps(["message"])})
    chat_id, user_id, display_name = latest_private_sender(updates)
    update_local_env(
        env_path,
        {
            "TELEGRAM_REVIEW_CHAT_ID": chat_id,
            "TELEGRAM_REVIEWER_USER_IDS": user_id,
        },
    )
    os.environ["TELEGRAM_REVIEW_CHAT_ID"] = chat_id
    os.environ["TELEGRAM_REVIEWER_USER_IDS"] = user_id
    return display_name


def main() -> int:
    load_local_env(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    submit_parser = subparsers.add_parser("submit", help="Отправить выпуск на ревью")
    submit_parser.add_argument("issue")
    subparsers.add_parser("run", help="Запустить long polling")
    subparsers.add_parser("discover", help="Показать ID чата и пользователя из последнего сообщения")
    subparsers.add_parser("configure-private", help="Настроить личный диалог по последнему сообщению")
    args = parser.parse_args()
    token = os.environ.get("TELEGRAM_REVIEW_BOT_TOKEN", "")
    bot = TelegramBot(token)
    if args.command == "discover":
        discover(bot)
        return 0
    if args.command == "configure-private":
        display_name = configure_private(bot, ROOT / ".env")
        print(f"Личный режим настроен для {display_name}; идентификаторы сохранены только в локальном .env.")
        return 0
    chat_id = os.environ.get("TELEGRAM_REVIEW_CHAT_ID", "")
    if not chat_id:
        raise BotError("Не задан TELEGRAM_REVIEW_CHAT_ID")
    if args.command == "submit":
        result = submit(bot, args.issue, chat_id)
        print(json.dumps({"ok": True, "message_id": result["message_id"], "issue": args.issue}, ensure_ascii=False))
        return 0
    run(bot, chat_id, allowed_reviewers())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BotError as exc:
        print(f"REVIEW BOT ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
