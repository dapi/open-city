#!/usr/bin/env python3
import argparse, os, json, time, re
from pathlib import Path
import requests

VOICES_ENDPOINT = "https://api.elevenlabs.io/v1/voices"
TTS_ENDPOINT    = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

PREFERRED_ORDER = [
    # (character, preferred voice names in order)
    ("Danila",   ["Daniel","Will","Brian","Roger","Harry","Liam"]),
    ("Flepik",   ["Alice","Sarah","Laura","Matilda","Lily"]),
    ("Mayor",    ["George","Brian","Will","Roger"]),
    ("Babka",    ["Jessica","Laura","Sarah","Matilda"]),
    ("Ani",      ["Lily","Alice","Sarah","Matilda"]),
    ("Passerby", ["Charlie","Roger","Harry","Will","Brian"]),
    ("System",   ["Brian","George","Eric","Chris"]),
]

def parse_voice_settings(s: str):
    vs = {}
    for kv in (s or "").split(","):
        kv = kv.strip()
        if not kv:
            continue
        if "=" not in kv: 
            continue
        k, v = kv.split("=", 1)
        if v.lower() in ("true","false"):
            vs[k] = (v.lower() == "true")
        else:
            try:
                vs[k] = float(v)
            except ValueError:
                vs[k] = v
    return vs

def fetch_voices(api_key: str):
    r = requests.get(VOICES_ENDPOINT, headers={"xi-api-key": api_key}, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data.get("voices", [])

def can_speak_ru(api_key: str, voice_id: str, model: str, voice_settings: dict, rate_limit: float):
    """Heuristic: try a tiny Russian TTS; if 200 OK and audio bytes > 2KB -> OK"""
    payload = {"text": "Проверка русского языка…", "model_id": model, "voice_settings": voice_settings}
    r = requests.post(TTS_ENDPOINT.format(voice_id=voice_id),
                      headers={"xi-api-key": api_key, "Content-Type": "application/json"},
                      json=payload, timeout=60)
    time.sleep(rate_limit)
    if r.status_code == 200 and len(r.content) > 2048:
        return True
    return False

def pick_mapping(ru_voices_by_name):
    mapping = {}
    # First pass: try preferred names
    used = set()
    for character, prefs in PREFERRED_ORDER:
        chosen = None
        for name in prefs:
            if name in ru_voices_by_name and name not in used:
                chosen = name; break
        if not chosen:
            # fallback to any remaining RU voice
            for name in ru_voices_by_name:
                if name not in used:
                    chosen = name; break
        if chosen:
            mapping[character] = chosen
            used.add(chosen)
    return mapping

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", help="ElevenLabs API key (or env XI_API_KEY)")
    ap.add_argument("--model", default="eleven_multilingual_v2")
    ap.add_argument("--voice-settings", default="stability=0.45,similarity_boost=0.9,style=0.25,use_speaker_boost=true")
    ap.add_argument("--rate-limit", type=float, default=0.35, help="sleep seconds between API calls")
    ap.add_argument("--test-limit", type=int, default=999, help="limit number of voices to test for RU (for speed)")
    ap.add_argument("--list-ru", action="store_true", help="only list RU-capable voices and exit")
    ap.add_argument("--write-speakers", default=None, help="path to write speakers.json mapping")
    args = ap.parse_args()

    api_key = args.api_key or os.getenv("XI_API_KEY")
    if not api_key:
        raise SystemExit("Provide --api-key or set env XI_API_KEY")

    voices = fetch_voices(api_key)
    vs = parse_voice_settings(args.voice_settings)

    ru_ok = []
    tested = 0
    for v in voices:
        if tested >= args.test_limit:
            break
        name = v.get("name","").strip()
        vid  = v.get("voice_id","").strip()
        if not name or not vid:
            continue
        ok = can_speak_ru(api_key, vid, args.model, vs, args.rate_limit)
        if ok:
            ru_ok.append((name, vid))
        tested += 1

    if not ru_ok:
        print("No RU-capable voices detected with quick test. Try increasing --test-limit or check your plan/keys.")
        return

    ru_voices_by_name = {name: vid for name, vid in ru_ok}
    print("RU-capable voices:")
    for name, vid in ru_ok:
        print(f"- {name}: {vid}")

    if args.list-ru and not args.write-speakers:
        return

    mapping = pick_mapping(ru_voices_by_name)
    if not mapping:
        print("Couldn't build speakers mapping.")
        return

    print("\nProposed speakers.json mapping (character -> voice name):")
    print(json.dumps(mapping, ensure_ascii=False, indent=2))

    # If user wants to write file
    if args.write-speakers:
        path = Path(args.write-speakers)
        path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[OK] speakers.json written to {path}")

if __name__ == "__main__":
    main()
