# Repository Guidelines

## Operating Scope
- This repository hosts the AI-driven operating system for the studio: it choreographs script intake, synthetic voice production, and hand-off to animation.
- Treat every change as a live-ops update—each asset here feeds the pilot production pipeline and must remain reproducible for future episodes.

## Project Structure & Shared Assets
- `generate_voice.py`, `speakers.json`, and `voice_script_v1.2_extended.json` define the core dialogue engine; keep additional scene scripts named `voice_script_<episode>.json`.
- Runtime caches live in `cache/`; final deliverables export to `output/` (`voice_master.wav`, `stems/`, `cues.csv`, optional `subs.srt`). Clear these folders before syncing with downstream teams.
- `Pilot_v1.2_Vertical_ProductionKit/` is the canonical package for collaborators. Subdirectories: `audio/` (approved stems), `docs/` (task briefs for agents), `render/` (final picture references). Duplicate the layout when spinning new kits.

## Daily Workflow
- Morning sync: review updated briefs in `Pilot_v1.2_Vertical_ProductionKit/docs/` and align task ownership across agents.
- Voice pass: update the JSON script, confirm speaker mappings, then run a dry render (`python3 generate_voice.py ... --rate-limit 0.4`). Log SFX or timing issues in the cues CSV.
- Animation prep: deposit greenlit audio stems into `Pilot_v1.2_Vertical_ProductionKit/audio/` and notify the Animator Agent with scene timestamps.
- EOD: archive approved exports to `output/stems/` and reset caches to keep the workspace light.

## Agent Roles & Handoffs
- **Voice Director (human + XI agent):** curates scripts, tweaks voice settings, validates pronunciation. Leaves notes in `output/cues.csv`.
- **Animator Agent:** consumes cues and audio, outputs motion drafts referenced in `render/`.
- **Operations Lead:** maintains this repo, coordinates API quotas, and publishes combined production kits.

## Tooling & Automations
- `make deps` prepares environment dependencies; run once per machine.
- `make generate` executes the full synthesis pass with subtitles; ensure `ELEVENLABS_API_KEY` (or `XI_API_KEY`) is present.
- For spot fixes, bake alternate takes by cloning the script file (e.g., `voice_script_v1.2_alt.json`) and comparing WAVs under `output/stems/`.

## Review & Quality Gate
- Before shipping, confirm cue timings against the script, listen for clipping, and screenshot waveform anomalies for the Animator Agent.
- Use pull requests—or a shared changelog if working outside Git—to document what changed, why, and which agents are impacted.

## Security & Access
- Store ElevenLabs credentials in local env vars or a `.env` excluded from sync. Rotate keys monthly and purge residual audio after each hand-off.
- Treat all generated audio as confidential IP: share via approved studio channels, not direct repository commits.
