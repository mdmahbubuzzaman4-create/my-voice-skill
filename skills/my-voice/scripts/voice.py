#!/usr/bin/env python
"""my-voice: turn a written Bangla script into audio in your own voice - free.

Engine: AI4Bharat IndicF5 (open-source Bangla/Indic voice cloning) running on the free
Hugging Face Space `ai4bharat/IndicF5`. No paid plan, no GPU needed on your PC.

Needs: `pip install gradio_client`, and ffmpeg on PATH.

Commands:
  setup  --ref MY_RECORDING --ref-text "exact words spoken in it"   (once)
  speak  --in SCRIPT.txt [--out OUT.mp3] [--pause 0.3]
  status
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SPACE = os.environ.get("MY_VOICE_SPACE", "ai4bharat/IndicF5")
CONFIG_DIR = Path.home() / ".config" / "my-voice"
CONFIG_FILE = CONFIG_DIR / "config.json"
REF_WAV = CONFIG_DIR / "ref.wav"
CHUNK = 220          # F5 sounds best on short pieces (1-3 sentences)
MAX_REF_SEC = 12     # reference clip should be ~6-12 s

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except Exception:
        pass


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def load_config():
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8")) if CONFIG_FILE.exists() else {}


def need_ffmpeg():
    if not shutil.which("ffmpeg"):
        die("ffmpeg not found. Install it:  winget install Gyan.FFmpeg")


def client():
    try:
        from gradio_client import Client
    except ImportError:
        die("Missing package. Run:  python -m pip install gradio_client")
    token = os.environ.get("HF_TOKEN") or load_config().get("hf_token")
    try:
        return Client(SPACE, hf_token=token, verbose=False) if token else Client(SPACE, verbose=False)
    except Exception as e:
        die(f"Could not connect to the Hugging Face Space {SPACE}: {e}")


def cmd_setup(args):
    need_ffmpeg()
    src = Path(args.ref)
    if not src.is_file():
        die(f"Recording not found: {src}")
    text = Path(args.ref_text_file).read_text(encoding="utf-8-sig") if args.ref_text_file else args.ref_text
    if not text or not text.strip():
        die("Give the exact words spoken in the recording with --ref-text or --ref-text-file.")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # mono 24 kHz, trimmed, leading/trailing silence removed, loudness normalised
    flt = ("silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
           "silenceremove=start_periods=1:start_threshold=-45dB,areverse,loudnorm")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(args.start), "-i", str(src),
                    "-t", str(args.duration or MAX_REF_SEC), "-af", flt, "-ac", "1", "-ar", "24000", str(REF_WAV)],
                   check=True)
    cfg = load_config()
    cfg["ref_text"] = " ".join(text.split())
    if args.hf_token:
        cfg["hf_token"] = args.hf_token.strip()
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                "csv=p=0", str(REF_WAV)], capture_output=True, text=True).stdout or 0)
    print(f"Voice saved ({dur:.1f} s reference) in {CONFIG_DIR}")
    if dur > MAX_REF_SEC + 1:
        print(f"Note: reference is long. Best results come from 6-{MAX_REF_SEC} s whose words exactly "
              "match --ref-text. Cut the recording to one or two sentences if output sounds off.")


def cmd_status(args):
    cfg = load_config()
    print(f"Engine: {SPACE} (free)")
    print(f"Voice reference: {'OK' if REF_WAV.exists() else 'MISSING - run setup'}")
    print(f"Reference text: {cfg.get('ref_text', '-')}")
    print(f"HF token: {'set' if (os.environ.get('HF_TOKEN') or cfg.get('hf_token')) else 'not set (optional)'}")


def split_script(text, limit=CHUNK):
    """Paragraphs -> sentences (। ! ? .) -> pieces of <= limit chars, never mid-word."""
    text = re.sub(r"[ \t]+", " ", text.replace("\r\n", "\n")).strip()
    out = []  # list of (chunk, ends_paragraph)
    for para in [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]:
        para = " ".join(para.split())
        sents = [s for s in re.split(r"(?<=[।!?.…])\s+", para) if s]
        cur = ""
        pieces = []
        for s in sents:
            while len(s) > limit:  # very long sentence: cut at comma, else space
                cut = max(s.rfind(",", 0, limit), s.rfind(" ", 0, limit))
                cut = cut + 1 if cut > 0 else limit
                if cur:
                    pieces.append(cur)
                    cur = ""
                pieces.append(s[:cut].strip())
                s = s[cut:].strip()
            if cur and len(cur) + 1 + len(s) > limit:
                pieces.append(cur)
                cur = s
            else:
                cur = f"{cur} {s}".strip()
        if cur:
            pieces.append(cur)
        out += [(p, i == len(pieces) - 1) for i, p in enumerate(pieces)]
    return out


def cmd_speak(args):
    need_ffmpeg()
    cfg = load_config()
    if not REF_WAV.exists() or not cfg.get("ref_text"):
        die("No voice set up yet. Run:  python voice.py setup --ref my_recording.mp3 --ref-text \"...\"")
    src = Path(args.infile)
    if not src.is_file():
        die(f"Script not found: {src}")
    text = src.read_text(encoding="utf-8-sig")
    text = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))
    if not text.strip():
        die("The script is empty.")
    chunks = split_script(text)
    out = Path(args.out) if args.out else src.with_suffix(".mp3")
    out.parent.mkdir(parents=True, exist_ok=True)

    from gradio_client import handle_file
    c = client()
    print(f"Engine {SPACE} | {len(text)} characters in {len(chunks)} part(s)")
    tmp = Path(tempfile.mkdtemp(prefix="my-voice-"))
    try:
        listing = []
        sil_s = tmp / "pause_s.wav"
        sil_p = tmp / "pause_p.wav"
        for f, d in ((sil_s, args.pause), (sil_p, args.pause * 2.5)):
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                            "anullsrc=r=24000:cl=mono", "-t", f"{d:.2f}", str(f)], check=True)
        for i, (chunk, end_para) in enumerate(chunks):
            for attempt in range(1, 4):
                try:
                    t0 = time.time()
                    res = c.predict(text=chunk, ref_audio=handle_file(str(REF_WAV)),
                                    ref_text=cfg["ref_text"], api_name="/synthesize_speech")
                    break
                except Exception as e:
                    msg = str(e)
                    if attempt == 3:
                        hint = (" The free GPU quota may be used up - wait a while, or add a free "
                                "Hugging Face token: setup ... --hf-token hf_xxx") if "quota" in msg.lower() else ""
                        die(f"Part {i + 1} failed: {msg}.{hint}")
                    print(f"  part {i + 1}: retry {attempt} ({msg[:80]})")
                    time.sleep(10 * attempt)
            part = tmp / f"part_{i:03d}.wav"
            # normalise every part to the same format so they join cleanly
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(res), "-ac", "1",
                            "-ar", "24000", str(part)], check=True)
            listing.append(part)
            if i < len(chunks) - 1:
                listing.append(sil_p if end_para else sil_s)
            print(f"  part {i + 1}/{len(chunks)} done ({time.time() - t0:.0f} s)")
        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in listing), encoding="utf-8")
        codec = ["-c:a", "libmp3lame", "-b:a", "192k"] if out.suffix.lower() == ".mp3" else []
        if not 0.5 <= args.speed <= 2.0:
            die("--speed must be between 0.5 and 2.0")
        # atempo speeds up speech without changing pitch (voice stays the same)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i",
                        str(lst), "-af", f"atempo={args.speed}", *codec, str(out)], check=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"Saved: {out.resolve()}")


def main():
    p = argparse.ArgumentParser(description="Bangla script -> audio in your own voice (free, IndicF5)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("setup", help="save your voice reference (once)")
    s.add_argument("--ref", required=True, help="recording of you (mp3/wav/m4a/mp4)")
    s.add_argument("--ref-text", help="exact words spoken in the recording")
    s.add_argument("--ref-text-file", help="file containing those words")
    s.add_argument("--start", type=float, default=0, help="start the clip at this second")
    s.add_argument("--duration", type=float, help=f"clip length in seconds (default {MAX_REF_SEC})")
    s.add_argument("--hf-token", help="optional free Hugging Face token for more GPU quota")
    s.set_defaults(fn=cmd_setup)

    sub.add_parser("status", help="show setup").set_defaults(fn=cmd_status)

    s = sub.add_parser("speak", help="script -> audio")
    s.add_argument("--in", dest="infile", required=True)
    s.add_argument("--out")
    s.add_argument("--pause", type=float, default=0.25, help="seconds between sentences")
    s.add_argument("--speed", type=float, default=1.2,
                   help="speaking speed, 1.0 = original, 1.2 = 20%% faster (default), max 2.0")
    s.set_defaults(fn=cmd_speak)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
