Remotion Captioner Starter (Hinglish + Whisper)

Overview

- Local web app to upload an MP4, auto-generate captions via Whisper (FastAPI), preview and style captions with Remotion, and export final MP4 via Remotion.
- Hinglish support (Devanagari + Latin) with Noto fonts.

Project Structure

- `app/`: Remotion + React TypeScript frontend
- `server/`: Python FastAPI Whisper STT server
- `render/`: Node script to render MP4 using @remotion/renderer

Prerequisites

- Node.js 18+
- Python 3.9+
- ffmpeg installed and on PATH

Setup

1) Install frontend deps

```bash
cd app
npm install
```

2) Install server deps (ideally in a venv)

```bash
cd ../server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

3) Run the STT server

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

4) Run the Remotion preview

```bash
cd ../app
npx remotion preview
```

Usage

- In the preview UI: Upload an MP4, click "Generate Captions" to call the Whisper server, choose a style, preview, then click "Render MP4" to export using Remotion CLI.

Rendering via Script

```bash
cd render
npm install
npx ts-node render.ts --input ../app/public/sample.mp4 --out out.mp4
```

Notes

- Fonts: Uses `@fontsource/noto-sans-devanagari` and `@fontsource/noto-sans` for Hinglish.
- STT: Default model is `small` for speed; change in `server/main.py`.
- Caption format: Simple segment-based subtitles with start/end seconds and text.


