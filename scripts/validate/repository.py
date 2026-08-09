#!/usr/bin/env python3
"""Small dependency-free repository smoke validator."""

import json
import re
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
    "projects/open-city/canon/project-bible.md",
    "productions/episodes/pilot-v1.2/episode.yaml",
    "productions/episodes/pilot-v1.2/script/timeline.json",
    "productions/episodes/pilot-v1.2/audio/speaker-map.json",
    "productions/episodes/pilot-v1.2/audio/voice-manifest.json",
    "productions/episodes/pilot-v1.2/animation/render-manifest.json",
    "productions/episodes/pilot-v1.2/release/release-manifest.json",
    "productions/episodes/pilot-v1.2/manifests/episode-manifest.yaml",
    "platform/voice/generate.py",
]

SCHEMAS = {
    "studio-os/contracts/approved-script.schema.json": ["$schema", "title", "type"],
    "studio-os/contracts/episode-spec.schema.json": ["$schema", "title", "type"],
    "studio-os/contracts/voice-manifest.schema.json": ["$schema", "title", "type"],
    "studio-os/contracts/render-manifest.schema.json": ["$schema", "title", "type"],
    "studio-os/contracts/release-manifest.schema.json": ["$schema", "title", "type"],
}

SCHEMA_INSTANCES = {
    "studio-os/contracts/approved-script.schema.json": "productions/episodes/pilot-v1.2/script/timeline.json",
    "studio-os/contracts/voice-manifest.schema.json": "productions/episodes/pilot-v1.2/audio/voice-manifest.json",
    "studio-os/contracts/render-manifest.schema.json": "productions/episodes/pilot-v1.2/animation/render-manifest.json",
    "studio-os/contracts/release-manifest.schema.json": "productions/episodes/pilot-v1.2/release/release-manifest.json",
}

FRONTMATTER_FILES = [
    "studio-os/governance/studio-passport.md",
    "projects/open-city/canon/project-bible.md",
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

    for schema_relative, instance_relative in SCHEMA_INSTANCES.items():
        try:
            schema = json.loads((ROOT / schema_relative).read_text(encoding="utf-8"))
            instance = json.loads((ROOT / instance_relative).read_text(encoding="utf-8"))
            jsonschema.Draft202012Validator(schema).validate(instance)
        except (OSError, json.JSONDecodeError, jsonschema.exceptions.ValidationError) as exc:
            errors.append(
                f"schema validation failed: {instance_relative} against {schema_relative}: {exc}"
            )

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
    for required_line in ("id: pilot-v1.2", "project: open-city", "status: in_progress"):
        if required_line not in yaml_text:
            errors.append(f"episode.yaml missing {required_line}")

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
