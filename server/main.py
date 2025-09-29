from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import tempfile
import uuid
import os
import json
import subprocess
import shutil
from faster_whisper import WhisperModel

app = FastAPI(title="Hinglish Whisper STT")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev: allow any origin (frontend runs on random port)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_NAME = os.environ.get("WHISPER_MODEL", "small")
_model = WhisperModel(MODEL_NAME, compute_type=os.environ.get("WHISPER_COMPUTE", "int8"))


class Segment(BaseModel):
    id: str
    start: float
    end: float
    text: str


class TranscribeResponse(BaseModel):
    segments: list[Segment]


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(file: UploadFile = File(...)):
    # Persist to a temp file so whisper can read it
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename or "upload")[1] or ".mp4") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Auto language detection; faster-whisper yields generator of segments
        seg_iter, _info = _model.transcribe(tmp_path, task="transcribe", language=None)
        segments: list[Segment] = []
        for s in seg_iter:
            segments.append(
                Segment(
                    id=str(uuid.uuid4()),
                    start=float(getattr(s, "start", 0.0)),
                    end=float(getattr(s, "end", 0.0)),
                    text=str(getattr(s, "text", "")).strip(),
                )
            )
        return TranscribeResponse(segments=segments)
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


class RenderParams(BaseModel):
    style: str


@app.post("/render")
async def render_video(
    file: UploadFile = File(...),
    segments_json: str = Form(...),
    style: str = Form("bottom-centered"),
):
    # Prepare temp files
    with tempfile.TemporaryDirectory() as td:
        video_path = os.path.join(td, os.path.basename(file.filename or "input.mp4"))
        captions_path = os.path.join(td, "captions.json")
        out_path = os.path.join(td, "out.mp4")

        # Write inputs
        content = await file.read()
        with open(video_path, "wb") as vf:
            vf.write(content)
        try:
            data = json.loads(segments_json)
        except Exception:
            return {"error": "Invalid segments_json"}
        with open(captions_path, "w", encoding="utf-8") as cf:
            json.dump(data, cf, ensure_ascii=False)

        # Find render script
        # project_root = server dir parent
        server_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(server_dir, ".."))
        render_dir = os.path.join(project_root, "render")
        render_ts = os.path.join(render_dir, "render.ts")

        # Ensure node and npx are available
        npx = shutil.which("npx") or "npx"

        cmd = [
            npx,
            "ts-node",
            "render.ts",
            "--input",
            video_path,
            "--captions",
            captions_path,
            "--style",
            style,
            "--out",
            out_path,
        ]

        # Run render
        proc = subprocess.run(cmd, cwd=render_dir, capture_output=True, text=True)
        if proc.returncode != 0:
            return {"error": "Render failed", "stderr": proc.stderr}

        # Return file
        return FileResponse(out_path, media_type="video/mp4", filename="captioned.mp4")


