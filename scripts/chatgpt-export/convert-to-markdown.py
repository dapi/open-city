#!/usr/bin/env python3
"""Build searchable Markdown projections from the immutable ChatGPT archive."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARCHIVE = REPO_ROOT / "knowledge/sources/chatgpt/open-city/archive"
DEFAULT_OUTPUT = REPO_ROOT / "knowledge/research/open-city-chat-archive/transcripts"

CHAT_FILENAMES = {
    "69077bb5-15c0-8327-a692-409c0d5bf1ea": "main.md",
    "69078091-5838-8333-8e33-e18b3a431b33": "producer-consultant.md",
    "69086e59-db2c-8325-b5c2-da4d3bf58181": "studio-roles.md",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def iso_time(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "unknown"
    return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")


def message_text(message: dict[str, Any]) -> str:
    content = message.get("content") or {}
    if content.get("content_type") == "thoughts":
        return "_[Служебные внутренние рассуждения модели не включены в поисковую копию.]_"

    chunks: list[str] = []
    for part in content.get("parts") or []:
        if isinstance(part, str):
            chunks.append(part)
        elif isinstance(part, dict) and part.get("content_type") == "text" and part.get("text"):
            chunks.append(str(part["text"]))
    text = "\n".join(chunks).strip()
    return text or "_[Текстового содержимого нет.]_"


def file_id_from_pointer(pointer: str) -> str | None:
    match = re.search(r"(?:file[_-])[A-Za-z0-9]+", pointer)
    return match.group(0) if match else None


def message_attachments(message: dict[str, Any]) -> list[dict[str, Any]]:
    attachments: list[dict[str, Any]] = []
    content = message.get("content") or {}
    for part in content.get("parts") or []:
        if not isinstance(part, dict) or not part.get("asset_pointer"):
            continue
        attachments.append(
            {
                "file_id": file_id_from_pointer(str(part["asset_pointer"])),
                "name": None,
                "mime": part.get("content_type"),
                "pointer": part["asset_pointer"],
            }
        )
    for attachment in (message.get("metadata") or {}).get("attachments") or []:
        attachments.append(
            {
                "file_id": attachment.get("id"),
                "name": attachment.get("name"),
                "mime": attachment.get("mimeType") or attachment.get("mime_type"),
                "pointer": None,
            }
        )

    unique: dict[tuple[Any, Any], dict[str, Any]] = {}
    for attachment in attachments:
        unique[(attachment.get("file_id"), attachment.get("name"))] = attachment
    return list(unique.values())


def current_path(raw: dict[str, Any]) -> list[str]:
    mapping = raw["mapping"]
    node_id = raw["current_node"]
    path: list[str] = []
    seen: set[str] = set()
    while node_id and node_id not in seen:
        seen.add(node_id)
        node = mapping[node_id]
        if node.get("message"):
            path.append(node_id)
        node_id = node.get("parent")
    path.reverse()
    return path


def node_sort_key(mapping: dict[str, Any], node_id: str) -> tuple[float, str]:
    message = mapping[node_id].get("message") or {}
    value = message.get("create_time")
    return (float(value) if isinstance(value, (int, float)) else float("inf"), node_id)


def branch_roots(raw: dict[str, Any], current: set[str]) -> list[str]:
    mapping = raw["mapping"]
    roots: list[str] = []
    for node_id, node in mapping.items():
        if node_id in current or not node.get("message"):
            continue
        parent = node.get("parent")
        parent_has_noncurrent_message = bool(
            parent
            and parent in mapping
            and parent not in current
            and mapping[parent].get("message")
        )
        if not parent_has_noncurrent_message:
            roots.append(node_id)
    return sorted(roots, key=lambda node_id: node_sort_key(mapping, node_id))


def walk_branch(raw: dict[str, Any], root: str, current: set[str]) -> list[tuple[str, int]]:
    mapping = raw["mapping"]
    result: list[tuple[str, int]] = []

    def visit(node_id: str, depth: int) -> None:
        node = mapping[node_id]
        if node_id in current:
            return
        if node.get("message"):
            result.append((node_id, depth))
        children = [child for child in node.get("children") or [] if child not in current]
        for child in sorted(children, key=lambda value: node_sort_key(mapping, value)):
            visit(child, depth + (1 if node.get("message") else 0))

    visit(root, 0)
    return result


def message_anchor(message_id: str) -> str:
    return f"msg-{message_id}"


def message_link(message_id: str | None, mapping: dict[str, Any]) -> str:
    if not message_id:
        return "—"
    if not mapping.get(message_id, {}).get("message"):
        return f"`{message_id}` (служебный узел)"
    return f"[`{message_id}`](#{message_anchor(message_id)})"


def render_attachments(
    message: dict[str, Any], artifact_map: dict[str, dict[str, Any]], conversation_id: str
) -> list[str]:
    rendered: list[str] = []
    for attachment in message_attachments(message):
        file_id = attachment.get("file_id")
        artifact = artifact_map.get(file_id) if file_id else None
        label = attachment.get("name") or (artifact or {}).get("file") or file_id or "attachment"
        if artifact and artifact.get("status") == "ok" and artifact.get("file"):
            target = (
                "../../../sources/chatgpt/open-city/archive/artifacts/"
                f"{conversation_id}/{artifact['file']}"
            )
            rendered.append(f"- [{label}]({target}) (`{file_id}`)")
        else:
            status = (artifact or {}).get("status") or "локальный файл не найден"
            rendered.append(f"- `{label}` (`{file_id or 'unknown'}`) — {status}")
    return rendered


def render_message(
    raw: dict[str, Any],
    node_id: str,
    ordinal: str,
    branch_state: str,
    artifact_map: dict[str, dict[str, Any]],
    depth: int = 0,
) -> str:
    node = raw["mapping"][node_id]
    message = node["message"]
    author = message.get("author") or {}
    role = author.get("role") or "unknown"
    name = author.get("name")
    role_label = f"{role}:{name}" if name else role
    content_type = (message.get("content") or {}).get("content_type") or "unknown"
    children = [child for child in node.get("children") or [] if raw["mapping"].get(child, {}).get("message")]

    lines = [
        f'<a id="{message_anchor(node_id)}"></a>',
        f"### {ordinal} · {role_label}",
        "",
        f"- `message_id`: `{node_id}`",
        f"- `state`: `{branch_state}`",
        f"- `created_at`: `{iso_time(message.get('create_time'))}`",
        f"- `content_type`: `{content_type}`",
        f"- `parent`: {message_link(node.get('parent'), raw['mapping'])}",
        f"- `children`: {', '.join(message_link(child, raw['mapping']) for child in children) if children else '—'}",
    ]
    if branch_state == "saved_branch":
        lines.append(f"- `branch_depth`: `{depth}`")
    recipient = (message.get("metadata") or {}).get("recipient")
    if recipient:
        lines.append(f"- `recipient`: `{recipient}`")
    lines.extend(["", message_text(message), ""])
    attachments = render_attachments(message, artifact_map, raw["conversation_id"])
    if attachments:
        lines.extend(["Вложения:", "", *attachments, ""])
    return "\n".join(lines)


def render_chat(raw: dict[str, Any], normalized: dict[str, Any], raw_filename: str) -> tuple[str, dict[str, int]]:
    conversation_id = raw["conversation_id"]
    mapping = raw["mapping"]
    current_ids = current_path(raw)
    current = set(current_ids)
    roots = branch_roots(raw, current)
    artifact_map = {
        artifact["file_id"]: artifact
        for artifact in normalized.get("artifacts") or []
        if artifact.get("file_id")
    }
    message_nodes = [node_id for node_id, node in mapping.items() if node.get("message")]
    branch_count = len(message_nodes) - len(current_ids)

    lines = [
        "---",
        "doc_kind: source",
        "doc_function: derived",
        "context: knowledge_provenance",
        f"purpose: {yaml_quote('Поисковое Markdown-представление чата ChatGPT «' + raw['title'] + '».')}",
        "status: active",
        "derived_from:",
        f"  - ../../../sources/chatgpt/open-city/archive/chats/{raw_filename}",
        "audience: humans_and_agents",
        "---",
        "",
        f"# {raw['title']}",
        "",
        "> Сгенерированная поисковая копия. Она не является каноном и не заменяет",
        "> неизменённый JSON-экспорт. Не редактировать вручную; пересобирать конвертером.",
        "",
        f"- Conversation ID: `{conversation_id}`",
        f"- Текущая ветка: {len(current_ids)} сообщений",
        f"- Сохранённые ответвления: {branch_count} сообщений в {len(roots)} корневых ветках",
        f"- Всего уникальных сообщений: {len(message_nodes)}",
        f"- Raw JSON: [`{raw_filename}`](../../../sources/chatgpt/open-city/archive/chats/{raw_filename})",
        "",
        "## Текущая ветка",
        "",
    ]
    for index, node_id in enumerate(current_ids):
        lines.append(render_message(raw, node_id, f"C{index:04d}", "current", artifact_map))

    lines.extend(["## Сохранённые ответвления", ""])
    if not roots:
        lines.extend(["Сохранённых ответвлений нет.", ""])
    for branch_index, root in enumerate(roots, 1):
        parent = mapping[root].get("parent")
        branch_nodes = walk_branch(raw, root, current)
        lines.extend(
            [
                f"## Ветка B{branch_index:03d}",
                "",
                f"Ответвляется после {message_link(parent, mapping)}. Уникальных сообщений: {len(branch_nodes)}.",
                "",
            ]
        )
        for message_index, (node_id, depth) in enumerate(branch_nodes):
            lines.append(
                render_message(
                    raw,
                    node_id,
                    f"B{branch_index:03d}.{message_index:04d}",
                    "saved_branch",
                    artifact_map,
                    depth,
                )
            )

    counts = {
        "current": len(current_ids),
        "branch": branch_count,
        "total": len(message_nodes),
        "branch_roots": len(roots),
    }
    return "\n".join(lines).rstrip() + "\n", counts


def render_index(records: list[dict[str, Any]]) -> str:
    total_current = sum(record["counts"]["current"] for record in records)
    total_branch = sum(record["counts"]["branch"] for record in records)
    total = sum(record["counts"]["total"] for record in records)
    lines = [
        "---",
        "doc_kind: source",
        "doc_function: index",
        "context: knowledge_provenance",
        "purpose: Индекс полнотекстовых Markdown-представлений скачанных чатов ChatGPT OpenCity.",
        "status: active",
        "derived_from:",
        "  - ../../../sources/chatgpt/open-city/archive/index.json",
        "audience: humans_and_agents",
        "---",
        "",
        "# Поисковые транскрипты архива ChatGPT OpenCity",
        "",
        "Это воспроизводимая Markdown-проекция неизменённого JSON-архива. Она удобна для",
        "полнотекстового поиска, но не является каноном проекта или заменой raw-источника.",
        "Каждый уникальный узел сообщения представлен один раз: сначала текущая ветка,",
        "затем сохранённые ответвления с указанием родителя.",
        "",
        "| Чат | Текущая ветка | Сохранённые ветки | Всего |",
        "|---|---:|---:|---:|",
    ]
    for record in records:
        counts = record["counts"]
        lines.append(
            f"| [{record['title']}]({record['filename']}) | {counts['current']} | "
            f"{counts['branch']} ({counts['branch_roots']} корн.) | {counts['total']} |"
        )
    lines.extend(
        [
            f"| **Итого** | **{total_current}** | **{total_branch}** | **{total}** |",
            "",
            "## Как искать",
            "",
            "```bash",
            "rg -n -i 'личка|ошибка человека|минус-контент' knowledge/research/open-city-chat-archive/transcripts",
            "rg -n '7d6799d9-d599-4388-9391-d1ac76a5fe9a' knowledge/research/open-city-chat-archive/transcripts",
            "```",
            "",
            "Служебные внутренние рассуждения модели намеренно не копируются; их узлы и",
            "метаданные остаются видимыми, а первичное содержимое хранится только в raw JSON.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build(archive: Path) -> dict[Path, str]:
    index = load_json(archive / "index.json")
    outputs: dict[Path, str] = {}
    records: list[dict[str, Any]] = []
    for chat in index["chats"]:
        conversation_id = chat["conversationId"]
        raw_path = archive / chat["files"]["raw"]
        normalized_path = archive / chat["files"]["messages"]
        raw = load_json(raw_path)
        normalized = load_json(normalized_path)
        filename = CHAT_FILENAMES.get(conversation_id, f"{conversation_id}.md")
        markdown, counts = render_chat(raw, normalized, raw_path.name)
        outputs[Path(filename)] = markdown
        records.append({"title": raw["title"], "filename": filename, "counts": counts})
    outputs[Path("README.md")] = render_index(records)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="Fail when generated files differ")
    args = parser.parse_args()

    outputs = build(args.archive.resolve())
    failures: list[str] = []
    if args.check:
        for relative_path, expected in outputs.items():
            path = args.output.resolve() / relative_path
            if not path.exists() or path.read_text(encoding="utf-8") != expected:
                failures.append(str(path))
        if failures:
            print("Outdated or missing Markdown projections:", file=sys.stderr)
            for failure in failures:
                print(f"- {failure}", file=sys.stderr)
            return 1
        print(f"OK: {len(outputs)} Markdown projections are reproducible")
        return 0

    args.output.mkdir(parents=True, exist_ok=True)
    for relative_path, content in outputs.items():
        path = args.output / relative_path
        path.write_text(content, encoding="utf-8")
        print(path.relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
