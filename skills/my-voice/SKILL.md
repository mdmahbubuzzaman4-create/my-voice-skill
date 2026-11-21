---
name: my-voice
description: Turn a written Bangla video script into a voiceover MP3 in the user's own cloned voice, free (AI4Bharat IndicF5 on a Hugging Face Space, no paid plan or GPU). Use for "convert my script to my voice", "make voiceover", "আমার ভয়েসে কনভার্ট করো", "ভয়েসওভার বানাও", "স্ক্রিপ্ট থেকে অডিও", or when the user pastes or points at a script and wants audio. Also handles the one-time voice setup.
---

# my-voice — Bangla script to your own voice (free)

Everything runs through `scripts/voice.py`. Call it as
`python "<this skill folder>/scripts/voice.py" <command>` (on Windows use `python`, not `python3`).
Requirements: `python -m pip install gradio_client`, and ffmpeg on PATH. Install anything missing
before going further.

## 1. Check setup

Run `python .../voice.py status`. If "Voice reference: MISSING", do the one-time setup:

1. Ask the user to record **8–12 seconds** of themselves reading this exact passage, in the same
   tone as their videos, in a quiet room, with no music (a phone voice memo is fine):

   > আসসালামু আলাইকুম। আমি আমার চ্যানেলে প্রতি সপ্তাহে নতুন ভিডিও নিয়ে আসি। আজকের বিষয়টা খুবই গুরুত্বপূর্ণ, তাই শেষ পর্যন্ত দেখবেন।

   If they use their own sentences instead, they must give the exact words they spoke.
2. Run:
   `python .../voice.py setup --ref "path/to/recording.m4a" --ref-text "<the exact words>"`
   Use `--start 3` to skip the first 3 seconds, and `--duration 10` to set the clip length.
   An existing video works too: point `--ref` at it with `--start`/`--duration` on a clean
   sentence, and write down exactly what is said there.

**The reference text must match the recording word for word.** A mismatch is the main cause of
bad output (garbled words or long nonsense audio).

## 2. Convert a script

1. Save the script as a UTF-8 `.txt` file (if pasted in chat, save it next to the user's project).
   Lines starting with `#` are notes and are not spoken. A blank line between paragraphs gives a
   longer pause.
2. Run `python .../voice.py speak --in script.txt --out script.mp3`. This takes about 10–25 s per
   1–2 sentences; run long scripts in the background.
3. Report the file path and its duration
   (`ffprobe -v error -show_entries format=duration -of csv=p=0 script.mp3`).

Options: `--pause 0.5` gives longer gaps between sentences (default 0.3 s).

## Problems

| Symptom | Fix |
|---|---|
| Garbled, wrong words, or audio much longer than expected | Reference text doesn't match the clip. Re-run setup with a shorter, cleaner clip and exact text |
| Doesn't sound like the user | Use a cleaner 8–12 s clip in their normal video tone |
| "quota" / "GPU" error | Free Space GPU limit reached. Wait and retry, or have the user create a free Hugging Face account → Settings → Access Tokens (read), then `setup ... --hf-token hf_xxx` |
| Space is down or sleeping | Retry in a few minutes. Advanced: set the `MY_VOICE_SPACE` env var to a duplicate of `ai4bharat/IndicF5` |

## Writing scripts for natural Bangla speech

- Write numbers as words when the reading matters (`২০২৬` → `দুই হাজার ছাব্বিশ`).
- Spell abbreviations out (`ড.` → `ডক্টর`). Write English terms in Bangla script the way they should be said (`কার্বন ক্রেডিট`).
- Short sentences ending in `।` sound most natural.

## Rules

- Never print or commit an HF token. Tokens stay in `~/.config/my-voice/config.json`.
- Clone only the user's own voice, or a voice they have permission to use.
