"""Generate voice lines with ElevenLabs (with character timestamps for subtitle sync).

Usage: python3 tts.py [--force] [--only l05,l10]
Outputs build/voice/<id>.mp3 and build/voice/<id>.json (alignment).
If the API is unreachable, writes placeholder silence + estimated alignment (marked "placeholder").
"""
import base64, json, os, subprocess, sys, urllib.request, urllib.error

from lines import LINES, SPEAKERS

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "build", "voice")
API = "https://api.elevenlabs.io/v1"

SETTINGS = {
    "narrator": dict(model="eleven_multilingual_v2", stability=0.42, similarity_boost=0.82, style=0.38, speed=0.90),
    "oldman":   dict(model="eleven_multilingual_v2", stability=0.30, similarity_boost=0.80, style=0.55, speed=0.86),
    "victor":   dict(model="eleven_multilingual_v2", stability=0.22, similarity_boost=0.78, style=0.80, speed=1.06),
    "mom":      dict(model="eleven_multilingual_v2", stability=0.55, similarity_boost=0.85, style=0.30, speed=0.84),
    "thing":    dict(model="eleven_multilingual_v2", stability=0.28, similarity_boost=0.70, style=0.65, speed=0.82),
}


def request(path, payload):
    req = urllib.request.Request(API + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "xi-api-key": os.environ.get("ELEVEN_API_KEY", "proxy-injected")})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", path]).decode().strip())


def placeholder(line, mp3, js):
    text = line["text"]
    per = {"victor": 0.060, "mom": 0.11, "thing": 0.10, "oldman": 0.085}.get(line["spk"], 0.075)
    t, starts, ends = 0.15, [], []
    for ch in text:
        d = per * (6 if ch in ".!?…" else 3 if ch in ",—:" else 1)
        starts.append(t); ends.append(t + d); t += d
    total = t + 0.2
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono",
                    "-t", f"{total:.3f}", "-c:a", "libmp3lame", "-b:a", "128k", mp3], check=True)
    json.dump({"characters": list(text), "character_start_times_seconds": starts,
               "character_end_times_seconds": ends, "placeholder": True}, open(js, "w"), ensure_ascii=False)


def generate(line, prev_text, next_text, force=False):
    mp3 = os.path.join(OUT, line["id"] + ".mp3")
    js = os.path.join(OUT, line["id"] + ".json")
    if not force and os.path.exists(js) and not json.load(open(js)).get("placeholder"):
        return "cached"
    s = SETTINGS[line["spk"]]
    payload = {
        "text": line["text"],
        "model_id": s["model"],
        "voice_settings": {k: s[k] for k in ("stability", "similarity_boost", "style", "speed")} | {"use_speaker_boost": True},
    }
    if line["spk"] == "narrator":
        payload["previous_text"] = prev_text
        payload["next_text"] = next_text
    voice = SPEAKERS[line["spk"]]["voice"]
    try:
        data = request(f"/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_192", payload)
    except urllib.error.HTTPError as e:
        print(line["id"], "API error", e.code, e.read()[:200].decode(errors="ignore"))
        placeholder(line, mp3, js)
        return "placeholder"
    open(mp3, "wb").write(base64.b64decode(data["audio_base64"]))
    json.dump(data["alignment"], open(js, "w"), ensure_ascii=False)
    return "ok"


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    force = "--force" in sys.argv
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    narr = [l for l in LINES]
    for i, line in enumerate(LINES):
        if only and line["id"] not in only:
            continue
        prev_t = " ".join(l["text"] for l in LINES[max(0, i - 2):i] if l["spk"] == "narrator")
        next_t = LINES[i + 1]["text"] if i + 1 < len(LINES) else ""
        status = generate(line, prev_t, next_t, force=force or bool(only))
        print(line["id"], status, f'{duration(os.path.join(OUT, line["id"] + ".mp3")):.2f}s', line["text"])
