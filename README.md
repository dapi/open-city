# OpenCity Studio OS

AI-first production system for the OpenCity studio: story development, voice
production, animation handoff, release and learning.

## Start here

- [Studio OS](studio-os/README.md) — rules, agents, workflows and contracts.
- [OpenCity project](projects/open-city/README.md) — canon and reusable assets.
- [Pilot v1.2 production run](productions/episodes/pilot-v1.2/README.md) — current episode.
- [Platform](platform/README.md) — reusable automation code.
- [Knowledge and provenance](knowledge/README.md) — sources, research and decisions.

## Common commands

```bash
make deps       # create .venv and install dependencies
make validate
make voices
make generate
```

Secrets belong in `XI_API_KEY`/`ELEVENLABS_API_KEY` or a local `.env`; never commit
them. Generated media belongs outside Git and is recorded by manifests.
