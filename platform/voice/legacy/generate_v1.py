#!/usr/bin/env python3
"""
generate_voice.py — Build a full dialogue WAV from a JSON script (standard or extended).

Features
- Reads JSON array with items: { "time": "m:ss-m:ss", "speaker": "Name", "text": "Text", "sfx": ["..."] }
- Calls ElevenLabs TTS API for each item (per speaker) and caches results in ./cache/
- Aligns each spoken line to its "start" time and mixes them into one master track
- Optional simple SFX for cues: "glitch-beep" / "white-noise-flash" (requires numpy)
- Exports:
  * master WAV: ./output/voice_master.wav
  * stems per speaker: ./output/stems/<speaker>.wav
  * cues CSV for sound designer: ./output/cues.csv
  * optional SRT subtitles: ./output/subs.srt (if --srt)

Usage
  python generate_voice.py path/to/voice_script.json \
      --api-key YOUR_XI_API_KEY \
      --speaker-map speakers.json \
      --model eleven_monolingual_v1 \
      --voice-settings stability=0.5,similarity_boost=0.85,style=0.2,use_speaker_boost=true \
      --srt
Notes
  - Set API key by arg or env XI_API_KEY.
  - Provide a speakers.json mapping: { "Danila": "VOICE_ID1", "Flepik": "VOICE_ID2", ... }
  - Requires: pip install requests pydub numpy (numpy optional but recommended)
"""

import argparse, json, os, re, time, math, csv
from pathlib import Path
import requests

# Optional deps
try:
    from pydub import AudioSegment
    from pydub.generators import Sine
except Exception as e:
    raise SystemExit("pydub is required (pip install pydub). Also ensure ffmpeg is installed in your PATH.")

try:
    import numpy as np
    HAVE_NUMPY = True
except Exception:
    HAVE_NUMPY = False

ELEVEN_TTS_ENDPOINT = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

def parse_time_range(t: str):
    """Parse 'm:ss-m:ss' into (start_ms, end_ms)."""
    m = re.match(r"^\s*(\d+):(\d{2})\s*-\s*(\d+):(\d{2})\s*$", t.replace("–", "-").replace("—", "-"))
    if not m:
        raise ValueError(f"Bad time format: {t}")
    s1 = int(m.group(1))*60 + int(m.group(2))
    s2 = int(m.group(3))*60 + int(m.group(4))
    if s2 < s1:
        raise ValueError(f"End before start in time: {t}")
    return s1*1000, s2*1000

def load_speaker_map(path: Path):
    if not path.exists():
        raise SystemExit(f"Speaker map not found: {path}\nCreate a JSON like: {{\"Danila\": \"VOICE_ID\", \"Flepik\": \"VOICE_ID\", ...}}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def tts_request(text: str, voice_id: str, api_key: str, model: str, voice_settings: dict, retry=3) -> bytes:
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": model,
        "voice_settings": voice_settings
    }
    url = ELEVEN_TTS_ENDPOINT.format(voice_id=voice_id)
    for attempt in range(retry):
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        if r.status_code == 200:
            return r.content
        time.sleep(1 + attempt)
    raise RuntimeError(f"TTS failed ({r.status_code}): {r.text}")

def sanitize_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", name)

def db(val: float):
    return 20 * math.log10(val) if val > 0 else -120

def generate_sfx(name: str, duration_ms=150) -> AudioSegment:
    """Minimal SFX: glitch-beep (1kHz sine 120ms), white-noise-flash (noise 300ms)."""
    name = name.lower()
    if "glitch" in name or "beep" in name:
        return Sine(1000).to_audio_segment(duration=120).apply_gain(-6)
    if "white-noise" in name and HAVE_NUMPY:
        samples = np.random.uniform(-1, 1, int(44100 * 0.30)).astype(np.float32)  # 300ms
        seg = AudioSegment(
            (samples.tobytes()), 
            frame_rate=44100, sample_width=4, channels=1
        ).apply_gain(-8)
        return seg
    # default: short tick
    return Sine(800).to_audio_segment(duration=80).apply_gain(-10)

def write_srt(items, path: Path):
    with open(path, "w", encoding="utf-8") as f:
        for idx, it in enumerate(items, 1):
            t1_ms, t2_ms = parse_time_range(it["time"])
            def fmt(ms):
                s, ms = divmod(int(ms), 1000)
                m, s = divmod(s, 60)
                return f"{m:02d}:{s:02d}:{ms:03d}"
            f.write(f"{idx}\n{fmt(t1_ms).replace(':',',',1).replace(':',':',1)} --> {fmt(t2_ms).replace(':',',',1).replace(':',':',1)}\n")
            speaker = it.get("speaker","")
            text = it.get("text","")
            f.write(f"{speaker}: {text}\n\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path", help="Path to voice_script_vX.X.json")
    ap.add_argument("--api-key", help="ElevenLabs API key (or set env XI_API_KEY)")
    ap.add_argument("--speaker-map", default="speakers.json", help="JSON mapping of speaker to VOICE_ID")
    ap.add_argument("--model", default="eleven_monolingual_v1")
    ap.add_argument("--voice-settings", default="stability=0.5,similarity_boost=0.85,style=0.2,use_speaker_boost=true")
    ap.add_argument("--rate-limit", type=float, default=0.4, help="Seconds to sleep between TTS calls")
    ap.add_argument("--srt", action="store_true", help="Export SRT subtitles")
    args = ap.parse_args()

    api_key = args.api_key or os.getenv("XI_API_KEY")
    if not api_key:
        raise SystemExit("Provide --api-key or set env XI_API_KEY")

    # Parse voice settings
    vs = {}
    for kv in args.voice_settings.split(","):
        if not kv.strip(): 
            continue
        k, v = kv.split("=", 1)
        if v.lower() in ("true","false"):
            vs[k] = (v.lower() == "true")
        else:
            try:
                vs[k] = float(v)
            except ValueError:
                vs[k] = v

    json_path = Path(args.json_path)
    data = json.loads(json_path.read_text(encoding="utf-8"))

    speaker_map = load_speaker_map(Path(args.speaker_map))

    out_dir = Path("output")
    cache_dir = Path("cache")
    stems_dir = out_dir / "stems"
    out_dir.mkdir(exist_ok=True, parents=True)
    cache_dir.mkdir(exist_ok=True, parents=True)
    stems_dir.mkdir(exist_ok=True, parents=True)

    # Load lines, group by speaker and also remember times for master mix
    lines = []
    max_end = 0
    for i, it in enumerate(data):
        tstr = it.get("time","0:00-0:03")
        start_ms, end_ms = parse_time_range(tstr)
        max_end = max(max_end, end_ms)
        speaker = it.get("speaker","Unknown")
        text = it.get("text","").strip()
        sfx = it.get("sfx", [])
        lines.append({
            "idx": i+1,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "speaker": speaker,
            "text": text,
            "sfx": sfx
        })

    # Prepare empty master
    master = AudioSegment.silent(duration=max_end + 500)

    # Per-speaker stems
    stems = {}

    # Cues CSV
    cues_csv = out_dir / "cues.csv"
    with open(cues_csv, "w", newline="", encoding="utf-8") as cf:
        writer = csv.writer(cf)
        writer.writerow(["idx","time","speaker","text","sfx_joined"])

        for ln in lines:
            speaker = ln["speaker"]
            text = ln["text"]
            start_ms = ln["start_ms"]
            end_ms = ln["end_ms"]
            sfx_list = ln["sfx"] or []

            # Get voice id
            voice_id = speaker_map.get(speaker)
            if not voice_id:
                print(f"[WARN] No VOICE_ID for speaker '{speaker}'. Skipping line {ln['idx']}.")
                continue

            # Cache key
            key = sanitize_filename(f"{speaker}_{ln['idx']}_{text[:40]}")
            cache_file = cache_dir / f"{key}.wav"

            if cache_file.exists():
                seg = AudioSegment.from_file(cache_file)
            else:
                # TTS request
                print(f"[TTS] {speaker} #{ln['idx']}: {text}")
                audio_bytes = tts_request(text, voice_id, api_key, args.model, vs)
                cache_file.write_bytes(audio_bytes)
                seg = AudioSegment.from_file(cache_file)
                time.sleep(args.rate_limit)

            # Adjust length gently (fade in/out)
            seg = seg.fade_in(15).fade_out(30)
            # Build/append stem
            stems.setdefault(speaker, AudioSegment.silent(duration=max_end + 500))
            stems[speaker] = stems[speaker].overlay(seg, position=start_ms)

            # Place into master
            master = master.overlay(seg, position=start_ms)

            # SFX cues (simple generators)
            for sfx_name in sfx_list:
                try:
                    sfx_seg = generate_sfx(sfx_name)
                    master = master.overlay(sfx_seg, position=start_ms)
                except Exception as e:
                    print(f"[SFX WARN] {sfx_name}: {e}")

            writer.writerow([ln["idx"], f"{start_ms/1000:.2f}-{end_ms/1000:.2f}", speaker, text, "|".join(sfx_list)])

    # Export
    master_out = out_dir / "voice_master.wav"
    master.export(master_out, format="wav")
    print(f"[OK] Master exported: {master_out}")

    # Export stems
    for spk, seg in stems.items():
        stem_out = stems_dir / f"{sanitize_filename(spk)}.wav"
        seg.export(stem_out, format="wav")
        print(f"[OK] Stem exported: {stem_out}")

    # Optional SRT
    if args.srt:
        srt_path = out_dir / "subs.srt"
        write_srt(data, srt_path)
        print(f"[OK] SRT exported: {srt_path}")

    print("Done.")
    
if __name__ == "__main__":
    main()
