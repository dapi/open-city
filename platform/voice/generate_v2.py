#!/usr/bin/env python3
"""
 generate_v2.py — ElevenLabs TTS builder with auto-resolve of voice NAMES to IDs.

What's new vs v1:
- Accepts in a speaker map either VOICE IDs *or* Voice NAMES (case-insensitive).
- --list-voices prints your voices (name + id) to help fill speakers.json.
- Clear error if a speaker can't be resolved; suggests closest matches.
- Same outputs as v1: output/voice_master.wav, stems per speaker, optional subs.srt, cues.csv.

JSON format stays the same:
[{"time":"0:00-0:05","speaker":"Danila","text":"...","sfx":["glitch-beep"]}, ...]

Usage examples:
  python generate_v2.py timeline.json --api-key $XI_API_KEY --speaker-map speaker-map.json --srt
  python generate_v2.py --list-voices --api-key $XI_API_KEY
"""

import argparse, json, os, re, time, math, csv, difflib
from pathlib import Path

try:
    import numpy as np
    HAVE_NUMPY = True
except Exception:
    HAVE_NUMPY = False

VOICES_ENDPOINT = "https://api.elevenlabs.io/v1/voices"
TTS_ENDPOINT    = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

def parse_time_range(t: str):
    m = re.match(r"^\s*(\d+):(\d{2})\s*-\s*(\d+):(\d{2})\s*$", t.replace("–","-").replace("—","-"))
    if not m:
        raise ValueError(f"Bad time format: {t}")
    s1 = int(m.group(1))*60 + int(m.group(2))
    s2 = int(m.group(3))*60 + int(m.group(4))
    if s2 < s1:
        raise ValueError(f"End before start: {t}")
    return s1*1000, s2*1000

def fetch_voices(api_key: str):
    r = requests.get(VOICES_ENDPOINT, headers={"xi-api-key": api_key}, timeout=60)
    r.raise_for_status()
    data = r.json()
    voices = data.get("voices", [])
    return [{"id": v["voice_id"], "name": v.get("name",""), "labels": v.get("labels",{})} for v in voices]

def load_speaker_map(path: Path):
    if not path.exists():
        sample = {
            "Danila": "Rachel",    # name or id
            "Flepik": "Adam",
            "Mayor":  "Antoni",
            "Babka":  "Bella",
            "Ani":    "Elli",
            "Passerby":"Charlie",
            "System": "George"
        }
        raise SystemExit(f"Speaker map not found: {path}\nCreate a JSON with voice NAMES or IDs, e.g.:\n{json.dumps(sample, ensure_ascii=False, indent=2)}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def resolve_voice(value: str, voices: list):
    """value may be an ID or a NAME; try ID first, then NAME (case-insensitive contains)."""
    val = (value or "").strip()
    if not val:
        return None, "empty"
    # Heuristic: IDs are long-ish, alnum; allow direct match
    if len(val) >= 20 and re.fullmatch(r"[A-Za-z0-9]+", val):
        # check exists
        for v in voices:
            if v["id"] == val:
                return v["id"], None
        return None, f"id_not_found:{val}"
    # treat as name
    # exact case-insensitive
    for v in voices:
        if v["name"].lower() == val.lower():
            return v["id"], None
    # substring match
    candidates = [v for v in voices if val.lower() in v["name"].lower()]
    if len(candidates) == 1:
        return candidates[0]["id"], None
    if candidates:
        # multiple, pick best by closeness
        names = [c["name"] for c in candidates]
        best = difflib.get_close_matches(val, names, n=1)
        if best:
            for c in candidates:
                if c["name"] == best[0]:
                    return c["id"], None
    return None, f"name_not_found:{val}"

def tts(text, voice_id, api_key, model, voice_settings, retry=3):
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    payload = {"text": text, "model_id": model, "voice_settings": voice_settings}
    url = TTS_ENDPOINT.format(voice_id=voice_id)
    last = None
    for i in range(retry):
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        if r.status_code == 200:
            return r.content
        last = (r.status_code, r.text)
        time.sleep(1 + i)
    raise RuntimeError(f"TTS failed {last[0]}: {last[1]}")

def generate_sfx(name: str):
    name = (name or "").lower()
    if "glitch" in name or "beep" in name:
        return Sine(1000).to_audio_segment(duration=120).apply_gain(-6)
    if "white-noise" in name and HAVE_NUMPY:
        import numpy as np
        samples = np.random.uniform(-1, 1, int(44100 * 0.30)).astype(np.float32)
        return AudioSegment(samples.tobytes(), frame_rate=44100, sample_width=4, channels=1).apply_gain(-8)
    return Sine(800).to_audio_segment(duration=80).apply_gain(-10)

def write_srt(items, path: Path):
    def fmt(ms):
        s, ms = divmod(int(ms), 1000)
        m, s = divmod(s, 60)
        return f"{m:02d}:{s:02d}:{ms:03d}".replace(":", ",", 1)
    with open(path, "w", encoding="utf-8") as f:
        for i, it in enumerate(items, 1):
            t1, t2 = parse_time_range(it["time"])
            f.write(f"{i}\n{fmt(t1)} --> {fmt(t2)}\n{it.get('speaker','')}: {it.get('text','')}\n\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path", nargs="?", help="Path to voice_script.json")
    ap.add_argument("--api-key", help="ElevenLabs API key (or env XI_API_KEY)")
    ap.add_argument("--speaker-map", default="speakers.json", help="JSON with speaker->(voice name or id)")
    ap.add_argument("--model", default="eleven_multilingual_v2")
    ap.add_argument("--voice-settings", default="stability=0.5,similarity_boost=0.85,style=0.2,use_speaker_boost=true")
    ap.add_argument("--rate-limit", type=float, default=0.4)
    ap.add_argument("--list-voices", action="store_true", help="List your voices and exit")
    ap.add_argument("--srt", action="store_true")
    ap.add_argument("--output-dir", default="output", help="Directory for generated audio and cues")
    ap.add_argument("--cache-dir", default="cache", help="Directory for reusable TTS chunks")
    args = ap.parse_args()

    # Import runtime dependencies after argparse so `--help` works on a fresh
    # checkout and missing setup produces an actionable message.
    global requests, AudioSegment, Sine
    try:
        import requests as requests
        from pydub import AudioSegment
        from pydub.generators import Sine
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Voice dependencies are missing. Run `make deps` first "
            f"(missing: {exc.name})."
        ) from exc

    api_key = args.api_key or os.getenv("XI_API_KEY")
    if not api_key:
        raise SystemExit("Provide --api-key or set env XI_API_KEY")

    # List voices and exit
    voices = fetch_voices(api_key)
    if args.list_voices:
        print("Your ElevenLabs voices:")
        for v in voices:
            print(f"- {v['name']}: {v['id']}")
        return

    if not args.json_path:
        raise SystemExit("Provide path to JSON script. Example: productions/episodes/<episode>/script/timeline.json")

    # Parse voice settings
    vs = {}
    for kv in args.voice_settings.split(","):
        kv = kv.strip()
        if not kv: 
            continue
        k, v = kv.split("=", 1)
        if v.lower() in ("true","false"):
            vs[k] = (v.lower() == "true")
        else:
            try:
                vs[k] = float(v)
            except ValueError:
                vs[k] = v

    # Load data
    data = json.loads(Path(args.json_path).read_text(encoding="utf-8"))
    speaker_map = load_speaker_map(Path(args.speaker_map))

    # Resolve speakers to IDs
    resolved = {}
    errors = []
    for spk, val in speaker_map.items():
        vid, err = resolve_voice(str(val), voices)
        if vid:
            resolved[spk] = vid
        else:
            errors.append((spk, val, err))
    if errors:
        printable = "\n".join([f"  - {spk}: '{val}' -> {err}" for spk, val, err in errors])
        # Show hints
        names = ", ".join(sorted({v['name'] for v in voices}))
        raise SystemExit(f"Can't resolve some speakers to voice IDs:\n{printable}\n\nTip: run with --list-voices and use one of your voice NAMES:\n{names}")

    # Build master and stems
    out_dir = Path(args.output_dir); out_dir.mkdir(parents=True, exist_ok=True)
    stems_dir = out_dir / "stems"; stems_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(args.cache_dir); cache_dir.mkdir(parents=True, exist_ok=True)

    # duration calc
    max_end = 0
    timeline = []
    for i, it in enumerate(data, 1):
        start_ms, end_ms = parse_time_range(it["time"])
        max_end = max(max_end, end_ms)
        timeline.append({
            "idx": i,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "speaker": it.get("speaker",""),
            "text": it.get("text","").strip(),
            "sfx": it.get("sfx", [])
        })

    master = AudioSegment.silent(duration=max_end + 500)
    stems = {}
    # cues
    with open(out_dir / "cues.csv", "w", newline="", encoding="utf-8") as cf:
        w = csv.writer(cf); w.writerow(["idx","time","speaker","text","sfx"])
        for ln in timeline:
            spk = ln["speaker"]; text = ln["text"]
            start_ms = ln["start_ms"]; sfx_list = ln["sfx"]
            voice_id = resolved.get(spk)
            if not voice_id:
                print(f"[WARN] No voice for {spk}; skipping line #{ln['idx']}")
                continue

            # cache key
            key = re.sub(r"[^a-zA-Z0-9._-]+","_", f"{spk}_{ln['idx']}_{text[:40]}")
            cache_file = cache_dir / f"{key}.wav"
            if cache_file.exists():
                seg = AudioSegment.from_file(cache_file)
            else:
                print(f"[TTS] {spk} #{ln['idx']}: {text}")
                audio_bytes = tts(text, voice_id, api_key, args.model, vs)
                cache_file.write_bytes(audio_bytes)
                seg = AudioSegment.from_file(cache_file)
                time.sleep(args.rate_limit)

            seg = seg.fade_in(15).fade_out(30)
            stems.setdefault(spk, AudioSegment.silent(duration=max_end + 500))
            stems[spk] = stems[spk].overlay(seg, position=start_ms)
            master = master.overlay(seg, position=start_ms)

            for s in sfx_list:
                try:
                    master = master.overlay(generate_sfx(s), position=start_ms)
                except Exception as e:
                    print(f"[SFX WARN] {s}: {e}")

            w.writerow([ln["idx"], f"{start_ms/1000:.2f}", spk, text, "|".join(sfx_list)])

    # Exports
    master.export(out_dir / "voice_master.wav", format="wav")
    for spk, seg in stems.items():
        seg.export(stems_dir / f"{re.sub(r'[^a-zA-Z0-9._-]+','_', spk)}.wav", format="wav")

    if args.srt:
        from datetime import timedelta
        def fmt(ms):
            td = timedelta(milliseconds=int(ms))
            srt = str(td)
            # ensure hh:mm:ss,ms
            if len(srt.split(':')) == 2:
                srt = "0:" + srt
            return srt.replace(".", ",")
        with open(out_dir / "subs.srt", "w", encoding="utf-8") as f:
            for i, ln in enumerate(timeline, 1):
                f.write(f"{i}\n{fmt(ln['start_ms'])} --> {fmt(ln['end_ms'])}\n{ln['speaker']}: {ln['text']}\n\n")
    print(f"[OK] Done. Exports in {out_dir}")
    
if __name__ == "__main__":
    main()
