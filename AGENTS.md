# Agent instructions for `/Users/danil/code/open-city`

## Mission

This repository is the AI operating system for the OpenCity studio. It coordinates
story intake, synthetic voice production, animation handoff, release and learning.
Treat changes as live production updates: preserve provenance and reproducibility.

## Navigation

- `studio-os/` — governance, agent roles, workflows and handoff contracts.
- `projects/open-city/` — project canon and reusable assets.
- `productions/episodes/<episode-id>/` — one complete production run.
- `platform/` — reusable automation code.
- `knowledge/` — raw sources, research, decisions and provenance.
- `var/` — local cache, output and temporary files; never commit it.

Read the nearest `README.md` before changing a governed area. One fact has one
canonical owner. Raw chats and generated files are evidence or run outputs, not
automatic canon.

## Agent work protocol

1. Identify the current episode and read its `episode.yaml` and README.
2. Check the relevant agent role in `studio-os/agents/`.
3. Consume the named upstream manifest or contract.
4. Make the smallest scoped change.
5. Run `make validate` and the relevant quality gate.
6. Update the downstream manifest, handoff note or ADR.
7. Report changed files, validation results and unresolved risks.

Do not silently resolve conflicts between canon, approved scripts and raw sources.
Report the conflict to the owner named by governance.

## Voice pipeline

The stable voice entry point is `platform/voice/generate.py`; its current implementation
is kept in `platform/voice/generate_v2.py`. The pilot inputs are:

- `productions/episodes/pilot-v1.2/script/timeline.json`;
- `productions/episodes/pilot-v1.2/audio/speaker-map.json`.

Run `make deps` once to create the local `.venv`, then run `make generate` only with a
local `XI_API_KEY` or `ELEVENLABS_API_KEY`. Generated
audio goes to `var/output/` and chunks to `var/cache/`; approved outputs are recorded
by `audio/voice-manifest.json` and are not committed as raw media.

## Security

Never commit API credentials, local `.env` files, cache, temporary exports or
unmanifested media. Treat generated audio and visual assets as confidential studio IP.
