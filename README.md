# my-voice — স্ক্রিপ্ট থেকে নিজের কণ্ঠে ভয়েসওভার (ফ্রি)

A Claude skill that turns your Bangla video script into an MP3 in **your own voice**, for free. It uses
the open-source [AI4Bharat IndicF5](https://huggingface.co/spaces/ai4bharat/IndicF5) model on a
free Hugging Face Space. You don't need a paid plan, an API key, or a GPU.

## ইনস্টল (Install)

```powershell
npx skills add mdmahbubuzzaman4-create/my-voice-skill
```

or install it manually for Claude Code:

```powershell
git clone https://github.com/mdmahbubuzzaman4-create/my-voice-skill "$env:TEMP\my-voice"; Copy-Item -Recurse "$env:TEMP\my-voice\skills\my-voice" "$env:USERPROFILE\.claude\skills\my-voice"
```

Then install the one Python package it needs and restart Claude:

```powershell
python -m pip install gradio_client
```

ffmpeg is also required (`winget install Gyan.FFmpeg`).

## প্রথমবার (Once)

Record 8–12 seconds of yourself reading this passage:

> আসসালামু আলাইকুম। আমি আমার চ্যানেলে প্রতি সপ্তাহে নতুন ভিডিও নিয়ে আসি। আজকের বিষয়টা খুবই গুরুত্বপূর্ণ, তাই শেষ পর্যন্ত দেখবেন।

Then tell Claude: **"আমার ভয়েস সেটআপ করো, রেকর্ডিং: D:\VideoWork\my-voice.m4a"**

## ব্যবহার (Use)

> এই স্ক্রিপ্টটা আমার ভয়েসে কনভার্ট করো: D:\VideoWork\scripts\video1.txt

You get `video1.mp3` next to the script.
