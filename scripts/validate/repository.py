#!/usr/bin/env python3
"""Small dependency-free repository smoke validator."""

import hashlib
import json
import re
import struct
import tomllib
from pathlib import Path

try:
    import jsonschema
except ModuleNotFoundError as exc:
    raise SystemExit("Validation dependency missing: run `make deps` first (jsonschema).") from exc


ROOT = Path(__file__).resolve().parents[2]
REQUIRED = [
    "README.md",
    "studio-os/README.md",
    "studio-os/contracts/approved-script.schema.json",
    "studio-os/contracts/comic-issue.schema.json",
    "studio-os/contracts/comic-review.schema.json",
    "studio-os/contracts/character-catalog.schema.json",
    "projects/open-city/canon/project-bible.md",
    "projects/open-city/canon/characters/README.md",
    "projects/open-city/canon/characters/characters.json",
    "projects/open-city/channels/README.md",
    "projects/open-city/channels/telegram-map.yaml",
    "projects/open-city/channels/telegram-setup-checklist.md",
    "projects/open-city/channels/studio-chat/editorial-policy.md",
    "projects/open-city/channels/studio-chat/participant-accounts.yaml",
    "projects/open-city/channels/studio-chat/scripts/sync-001-format-change.md",
    "projects/open-city/channels/studio-chat/scripts/sync-002-no-argument.md",
    "projects/open-city/channels/studio-chat/scripts/sync-003-quiet-mode.md",
    "projects/open-city/channels/studio-chat/scripts/sync-004-joy-index.md",
    "projects/open-city/channels/opencity-studio/publishing-policy.md",
    "projects/open-city/channels/editorial-review/README.md",
    "projects/open-city/brand/visual-system.md",
    "projects/open-city/site/README.md",
    "projects/open-city/site/site.json",
    "projects/open-city/site/styles.css",
    "productions/issues/issue-001/issue.json",
    "productions/issues/issue-001/script.md",
    "productions/issues/issue-001/art/issue-001-master.png",
    "productions/issues/issue-001/manifest.json",
    "productions/issues/issue-002/issue.json",
    "productions/issues/issue-002/script.md",
    "productions/issues/issue-002/art/issue-002-master.png",
    "productions/issues/issue-002/manifest.json",
    "productions/issues/issue-003/issue.json",
    "productions/issues/issue-003/script.md",
    "productions/issues/issue-003/art/issue-003-master.png",
    "productions/issues/issue-003/manifest.json",
    "productions/issues/issue-004/issue.json",
    "productions/issues/issue-004/script.md",
    "productions/issues/issue-004/art/issue-004-master.png",
    "productions/issues/issue-004/manifest.json",
    "knowledge/research/open-city-chat-archive-findings.md",
    "knowledge/research/editorial-review-issues-001-004.md",
    ".codex/config.toml",
    ".codex/agents/flepik.toml",
    ".codex/agents/danya.toml",
    ".codex/agents/neyra.toml",
    ".codex/agents/marina.toml",
    ".codex/agents/showrunner-guard.toml",
    "productions/episodes/pilot-v1.2/episode.yaml",
    "productions/episodes/pilot-v1.2/script/timeline.json",
    "productions/episodes/pilot-v1.2/audio/speaker-map.json",
    "productions/episodes/pilot-v1.2/audio/voice-manifest.json",
    "productions/episodes/pilot-v1.2/animation/render-manifest.json",
    "productions/episodes/pilot-v1.2/release/release-manifest.json",
    "productions/episodes/pilot-v1.2/manifests/episode-manifest.yaml",
    "platform/voice/generate.py",
    "platform/publishing/build_site.py",
    "platform/publishing/review_bot.py",
]

SCHEMAS = {
    "studio-os/contracts/approved-script.schema.json": ["$schema", "title", "type"],
    "studio-os/contracts/comic-issue.schema.json": ["$schema", "title", "type"],
    "studio-os/contracts/comic-review.schema.json": ["$schema", "title", "type"],
    "studio-os/contracts/character-catalog.schema.json": ["$schema", "title", "type"],
    "studio-os/contracts/episode-spec.schema.json": ["$schema", "title", "type"],
    "studio-os/contracts/voice-manifest.schema.json": ["$schema", "title", "type"],
    "studio-os/contracts/render-manifest.schema.json": ["$schema", "title", "type"],
    "studio-os/contracts/release-manifest.schema.json": ["$schema", "title", "type"],
}

SCHEMA_INSTANCES = [
    (
        "studio-os/contracts/character-catalog.schema.json",
        "projects/open-city/canon/characters/characters.json",
    ),
] + [
    ("studio-os/contracts/comic-issue.schema.json", f"productions/issues/issue-{number:03d}/issue.json")
    for number in range(1, 5)
] + [
    ("studio-os/contracts/approved-script.schema.json", "productions/episodes/pilot-v1.2/script/timeline.json"),
    ("studio-os/contracts/voice-manifest.schema.json", "productions/episodes/pilot-v1.2/audio/voice-manifest.json"),
    ("studio-os/contracts/render-manifest.schema.json", "productions/episodes/pilot-v1.2/animation/render-manifest.json"),
    ("studio-os/contracts/release-manifest.schema.json", "productions/episodes/pilot-v1.2/release/release-manifest.json"),
]

FRONTMATTER_FILES = [
    "studio-os/governance/studio-passport.md",
    "projects/open-city/canon/project-bible.md",
    "projects/open-city/canon/characters/README.md",
    "projects/open-city/channels/README.md",
    "projects/open-city/channels/telegram-setup-checklist.md",
    "projects/open-city/channels/studio-chat/README.md",
    "projects/open-city/channels/studio-chat/editorial-policy.md",
    "projects/open-city/channels/studio-chat/scripts/sync-001-format-change.md",
    "projects/open-city/channels/studio-chat/scripts/sync-002-no-argument.md",
    "projects/open-city/channels/studio-chat/scripts/sync-003-quiet-mode.md",
    "projects/open-city/channels/studio-chat/scripts/sync-004-joy-index.md",
    "projects/open-city/channels/opencity-studio/README.md",
    "projects/open-city/channels/opencity-studio/publishing-policy.md",
    "projects/open-city/channels/editorial-review/README.md",
    "projects/open-city/brand/visual-system.md",
    "projects/open-city/site/README.md",
    "productions/issues/issue-001/README.md",
    "productions/issues/issue-001/brief.md",
    "productions/issues/issue-001/script.md",
    "productions/issues/issue-001/storyboard.md",
    "productions/issues/issue-001/art/generation-prompt.md",
    "productions/issues/issue-002/README.md",
    "productions/issues/issue-002/brief.md",
    "productions/issues/issue-002/script.md",
    "productions/issues/issue-002/storyboard.md",
    "productions/issues/issue-002/art/generation-prompt.md",
    "productions/issues/issue-003/README.md",
    "productions/issues/issue-003/brief.md",
    "productions/issues/issue-003/script.md",
    "productions/issues/issue-003/storyboard.md",
    "productions/issues/issue-003/art/generation-prompt.md",
    "productions/issues/issue-004/README.md",
    "productions/issues/issue-004/brief.md",
    "productions/issues/issue-004/script.md",
    "productions/issues/issue-004/storyboard.md",
    "productions/issues/issue-004/art/generation-prompt.md",
    "knowledge/research/open-city-chat-archive-findings.md",
    "knowledge/research/editorial-review-issues-001-004.md",
    "studio-os/workflows/editorial-council.md",
    "studio-os/workflows/comic-editorial-review.md",
    "productions/episodes/pilot-v1.2/README.md",
    "studio-os/agents/showrunner/README.md",
    "studio-os/agents/story-generator/README.md",
    "studio-os/agents/script-editor/README.md",
    "studio-os/agents/visual-designer/README.md",
    "studio-os/agents/voice-director/README.md",
    "studio-os/agents/animator/README.md",
    "studio-os/agents/visual-designer/README.md",
    "studio-os/agents/promo-agent/README.md",
    "productions/episodes/pilot-v1.2/script/voice-script.md",
    "productions/episodes/pilot-v1.2/audio/task.md",
    "productions/episodes/pilot-v1.2/animation/task.md",
    "productions/episodes/pilot-v1.2/animation/animation-script.md",
    "productions/episodes/pilot-v1.2/render/render-plan.md",
]

MANIFESTS = [
    "productions/episodes/pilot-v1.2/audio/voice-manifest.json",
    "productions/episodes/pilot-v1.2/animation/render-manifest.json",
    "productions/episodes/pilot-v1.2/release/release-manifest.json",
]


def frontmatter_references(path: Path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return []
    end = text.find("\n---", 4)
    if end == -1:
        return []
    block = text[4:end]
    references = []
    in_derived_from = False
    for line in block.splitlines():
        if line.startswith("derived_from:"):
            in_derived_from = True
            continue
        if in_derived_from and line.startswith("  - "):
            value = line[4:].strip().strip("\"'")
            if not value.startswith(("http://", "https://")):
                references.append(value)
        elif in_derived_from and line and not line.startswith(" "):
            in_derived_from = False
    return references


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as image:
        header = image.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError("not a PNG with IHDR header")
    return struct.unpack(">II", header[16:24])


def main() -> int:
    errors = []
    for relative in REQUIRED:
        if not (ROOT / relative).exists():
            errors.append(f"missing required file: {relative}")

    for relative, required_keys in SCHEMAS.items():
        try:
            schema = json.loads((ROOT / relative).read_text(encoding="utf-8"))
            jsonschema.Draft202012Validator.check_schema(schema)
            for key in required_keys:
                if key not in schema:
                    errors.append(f"schema {relative} missing {key}")
        except (OSError, json.JSONDecodeError, jsonschema.exceptions.SchemaError) as exc:
            errors.append(f"invalid schema {relative}: {exc}")

    for schema_relative, instance_relative in SCHEMA_INSTANCES:
        try:
            schema = json.loads((ROOT / schema_relative).read_text(encoding="utf-8"))
            instance = json.loads((ROOT / instance_relative).read_text(encoding="utf-8"))
            jsonschema.Draft202012Validator(schema).validate(instance)
        except (OSError, json.JSONDecodeError, jsonschema.exceptions.ValidationError) as exc:
            errors.append(
                f"schema validation failed: {instance_relative} against {schema_relative}: {exc}"
            )

    try:
        character_catalog = json.loads(
            (ROOT / "projects/open-city/canon/characters/characters.json").read_text(encoding="utf-8")
        )
        characters = character_catalog["characters"]
        character_ids = [character["id"] for character in characters]
        dossier_numbers = [character["dossier_number"] for character in characters]
        if len(character_ids) != len(set(character_ids)):
            errors.append("character catalog contains duplicate ids")
        if len(dossier_numbers) != len(set(dossier_numbers)):
            errors.append("character catalog contains duplicate dossier numbers")
        for character in characters:
            for issue_id in character["appearances"]:
                if not (ROOT / "productions/issues" / issue_id / "issue.json").exists():
                    errors.append(f"character {character['id']} references missing issue {issue_id}")
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        errors.append(f"invalid character catalog relationships: {exc}")

    for relative in FRONTMATTER_FILES:
        path = ROOT / relative
        try:
            text = path.read_text(encoding="utf-8")
            if not text.startswith("---\n") or "doc_kind:" not in text or "status:" not in text:
                errors.append(f"invalid frontmatter: {relative}")
        except OSError as exc:
            errors.append(f"cannot read frontmatter file {relative}: {exc}")

    for base in ("studio-os", "projects", "productions", "docs"):
        for path in (ROOT / base).rglob("*.md"):
            if "knowledge/sources/chatgpt/open-city/archive" in str(path):
                continue
            for reference in frontmatter_references(path):
                if not (path.parent / reference).resolve().exists():
                    errors.append(f"broken derived_from in {path.relative_to(ROOT)}: {reference}")

    for relative in MANIFESTS:
        try:
            manifest = json.loads((ROOT / relative).read_text(encoding="utf-8"))
            for key in ("episode", "status", "inputs", "outputs"):
                if key not in manifest:
                    errors.append(f"manifest {relative} missing {key}")
            for input_path in manifest.get("inputs", []):
                if not (ROOT / Path(relative).parent / input_path).resolve().exists():
                    errors.append(f"manifest {relative} references missing input {input_path}")
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid manifest {relative}: {exc}")

    episode_yaml = ROOT / "productions/episodes/pilot-v1.2/episode.yaml"
    yaml_text = episode_yaml.read_text(encoding="utf-8")
    for required_line in ("id: pilot-v1.2", "project: open-city", "status: cancelled"):
        if required_line not in yaml_text:
            errors.append(f"episode.yaml missing {required_line}")

    comic_manifest_paths = sorted((ROOT / "productions/issues").glob("issue-*/manifest.json"))
    for comic_manifest_path in comic_manifest_paths:
        try:
            comic_manifest = json.loads(comic_manifest_path.read_text(encoding="utf-8"))
            for key in ("issue", "status", "inputs", "outputs", "releases"):
                if key not in comic_manifest:
                    errors.append(f"comic manifest {comic_manifest_path.parent.name} missing {key}")
            for input_path in comic_manifest.get("inputs", []):
                if not (comic_manifest_path.parent / input_path).resolve().exists():
                    errors.append(
                        f"comic manifest {comic_manifest_path.parent.name} references missing input {input_path}"
                    )
            for output in comic_manifest.get("outputs", []):
                output_path = (comic_manifest_path.parent / output.get("path", "")).resolve()
                if not output_path.exists():
                    errors.append(
                        f"comic manifest {comic_manifest_path.parent.name} references missing output {output.get('path')}"
                    )
                    continue
                expected_hash = output.get("sha256")
                actual_hash = hashlib.sha256(output_path.read_bytes()).hexdigest()
                if expected_hash != actual_hash:
                    errors.append(
                        f"comic output checksum mismatch for {output.get('path')}: "
                        f"expected {expected_hash}, got {actual_hash}"
                    )
                try:
                    actual_width, actual_height = png_dimensions(output_path)
                    if (actual_width, actual_height) != (output.get("width"), output.get("height")):
                        errors.append(
                            f"comic output dimensions mismatch for {output.get('path')}: "
                            f"manifest {(output.get('width'), output.get('height'))}, "
                            f"actual {(actual_width, actual_height)}"
                        )
                    if actual_width * 3 != actual_height * 2:
                        errors.append(f"comic output must have 2:3 aspect ratio: {output.get('path')}")
                except (OSError, ValueError) as exc:
                    errors.append(f"invalid comic PNG {output.get('path')}: {exc}")

            issue_path = comic_manifest_path.parent / "issue.json"
            issue = json.loads(issue_path.read_text(encoding="utf-8"))
            if issue.get("status") != comic_manifest.get("status"):
                errors.append(f"status mismatch in {comic_manifest_path.parent.name}")
            if issue.get("status") in {"approved", "published"}:
                review_path = comic_manifest_path.parent / "review.json"
                if not review_path.exists():
                    errors.append(f"approved issue missing review.json: {comic_manifest_path.parent.name}")
                else:
                    review_schema = json.loads(
                        (ROOT / "studio-os/contracts/comic-review.schema.json").read_text(encoding="utf-8")
                    )
                    review = json.loads(review_path.read_text(encoding="utf-8"))
                    jsonschema.Draft202012Validator(review_schema).validate(review)
                    current_hash = comic_manifest.get("outputs", [{}])[0].get("sha256")
                    if review.get("decision") != "approved" or review.get("master_sha256") != current_hash:
                        errors.append(f"stale or rejected review for {comic_manifest_path.parent.name}")
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid comic manifest {comic_manifest_path}: {exc}")
        except jsonschema.exceptions.ValidationError as exc:
            errors.append(f"invalid comic review {comic_manifest_path.parent.name}: {exc}")

    for agent_path in sorted((ROOT / ".codex/agents").glob("*.toml")):
        try:
            employee = tomllib.loads(agent_path.read_text(encoding="utf-8"))
            for key in ("name", "description", "developer_instructions"):
                if not employee.get(key):
                    errors.append(f"employee config {agent_path.name} missing {key}")
            if employee.get("sandbox_mode") != "read-only":
                errors.append(f"employee config {agent_path.name} must be read-only")
            if "по-русски" not in employee.get("developer_instructions", ""):
                errors.append(f"employee config {agent_path.name} missing Russian-language rule")
        except (OSError, tomllib.TOMLDecodeError) as exc:
            errors.append(f"invalid employee config {agent_path.name}: {exc}")

    json_files = [
        "productions/episodes/pilot-v1.2/script/timeline.json",
        "productions/episodes/pilot-v1.2/audio/speaker-map.json",
        "productions/episodes/pilot-v1.2/audio/speaker-map-russian.json",
    ]
    for relative in json_files:
        try:
            json.loads((ROOT / relative).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON {relative}: {exc}")

    timeline = json.loads((ROOT / json_files[0]).read_text(encoding="utf-8"))
    speakers = json.loads((ROOT / json_files[1]).read_text(encoding="utf-8"))
    for index, line in enumerate(timeline, 1):
        for key in ("time", "speaker", "text"):
            if not line.get(key):
                errors.append(f"timeline line {index} missing {key}")
        if line.get("speaker") not in speakers:
            errors.append(f"timeline line {index} has unmapped speaker {line.get('speaker')}")
        if not re.match(r"^\d+:[0-5]\d-\d+:[0-5]\d$", line.get("time", "")):
            errors.append(f"timeline line {index} has invalid time {line.get('time')}")

    if errors:
        print("VALIDATION FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("VALIDATION OK")
    print(f"- required files: {len(REQUIRED)}")
    print(f"- timeline lines: {len(timeline)}")
    print(f"- speakers: {len(speakers)}")
    print(f"- comic issues: {len(comic_manifest_paths)}")
    print(f"- digital employees: {len(list((ROOT / '.codex/agents').glob('*.toml')))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
