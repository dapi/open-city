# WARP.md

## Development commands

```bash
make deps       # Create .venv and install dependencies
make validate   # Validate repository structure and pilot inputs
make voices     # List ElevenLabs voices; requires XI_API_KEY
make generate   # Render pilot voice assets into var/output/
```

Requires Python, ffmpeg and an ElevenLabs API key for voice generation.

## Architecture

- `studio-os/` contains human and agent operating rules.
- `projects/open-city/` contains canon.
- `productions/episodes/pilot-v1.2/` contains the current episode run.
- `platform/voice/` contains reusable TTS automation.
- `knowledge/` contains source material and provenance.

`platform/voice/generate.py` accepts a timeline JSON and speaker map, caches TTS
chunks, and writes WAV/stem/cue/subtitle output to the selected output directory.
