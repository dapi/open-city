# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Development Commands

### Setup & Dependencies
```bash
make deps                  # Install Python dependencies (requests, pydub, numpy)
```

Run inside a virtualenv. Requires ffmpeg in PATH for pydub audio operations.

### Voice Generation
```bash
# Full render with extended script
make generate             # Requires XI_API_KEY env var

# List available ElevenLabs voices
make voices               # Shows voice names and IDs

# Manual generation with v1 (basic)
python3 generate_voice.py voice_script_v1.2_extended.json \
  --speaker-map speakers.json \
  --api-key $XI_API_KEY \
  --srt

# Manual generation with v2 (auto-resolves voice names)
python3 generate_voice_v2.py voice_script_v1.2_extended.json \
  --api-key $XI_API_KEY \
  --speaker-map speakers.json \
  --model eleven_multilingual_v2 \
  --voice-settings stability=0.45,similarity_boost=0.9,style=0.25,use_speaker_boost=true \
  --srt
```

Add `--rate-limit 0.6` when approaching API quotas.

### Code Quality
```bash
black generate_voice.py generate_voice_v2.py  # Format code (line length 88)
ruff generate_voice.py generate_voice_v2.py   # Lint code
```

### Testing
```bash
# Unit tests (target pure helpers)
pytest tests/test_time_parsing.py

# Integration test with fixture
python3 generate_voice.py tests/data/sample.json \
  --speaker-map speakers.json \
  --rate-limit 0 \
  && ls output/
```

## Architecture Overview

### Core Components

**generate_voice.py** (v1)
- Original TTS synthesis engine
- Requires explicit ElevenLabs voice IDs in `speakers.json`
- Single-file architecture with all logic inline
- Key functions: `parse_time_range()`, `tts_request()`, `generate_sfx()`, `write_srt()`

**generate_voice_v2.py** (v2)
- Enhanced with voice name auto-resolution via ElevenLabs API
- Accepts either voice IDs or names in `speakers.json` (case-insensitive)
- Adds `--list-voices` for discovery and `resolve_voice()` with fuzzy matching
- Same outputs as v1, improved DX

### Data Flow

1. **Input**: JSON script (`voice_script_v1.2_extended.json`) defines timeline with:
   - `time`: "m:ss-m:ss" range
   - `speaker`: Character name (mapped via `speakers.json`)
   - `text`: Dialogue line
   - `sfx`: Optional sound effect cues (array)

2. **Processing**:
   - Parse timeline → resolve speakers to voice IDs → TTS per line
   - Cache audio chunks in `cache/` (keyed by speaker + text hash)
   - Mix onto master timeline at specified `start_ms`
   - Generate simple SFX cues inline (glitch-beep, white-noise-flash)
   - Build per-speaker stems in parallel

3. **Output** (`output/`):
   - `voice_master.wav`: Full mixed dialogue
   - `stems/<speaker>.wav`: Individual tracks per character
   - `cues.csv`: Sound designer reference (idx, time, speaker, text, sfx)
   - `subs.srt`: Optional subtitles (if `--srt`)

### Configuration

**speakers.json** — Maps character names to ElevenLabs voices:
```json
{
  "Danila": "Rachel",    // v2: voice name OR ID
  "Flepik": "Adam",
  "Mayor":  "Antoni"
}
```

**API Authentication**: Set `XI_API_KEY` or `ELEVENLABS_API_KEY` env var. Never commit keys.

### Production Kits

`Pilot_v1.2_Vertical_ProductionKit/` structure:
- `audio/`: Voice scripts (JSON + markdown)
- `docs/`: Task specs, animation scripts
- `render/`: Render plans for 9:16 vertical format

Version new kits as `Pilot_<version>_<format>_ProductionKit/` with same subfolder layout.

## Conventions

- **Coding Style**: 4-space indent, `snake_case`, upper `CONSTANTS`, explicit imports
- **Commits**: Conventional (`feat:`, `fix:`, `chore:`)
- **Cache Management**: Never commit `cache/`; prune `output/` before PRs unless audio needed for review
- **Script Versioning**: Name as `voice_script_<scene>.json` when adding variants
