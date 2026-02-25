# ---------------------------------------------------------------------------
# dubbing/extract.py — Video segment extraction using ffmpeg.
#
# PURPOSE:
#   Given a full-length video, extract a specific time range (e.g. 0:15–0:30)
#   as both a video clip and a standalone audio file.  This is the first step
#   in the dubbing pipeline — everything downstream works on this segment.
#
# WHY ffmpeg (via subprocess, not a wrapper)?
#   1. Zero extra Python dependencies — ffmpeg ships with Colab by default.
#   2. Full control over codec flags (keyframe-accurate cuts, sample rate).
#   3. Easy to debug — copy-paste the exact command into a terminal.
#
# SCALABILITY NOTE (500 hrs overnight on distributed GPUs):
#   For full-length videos you would split into N-second chunks here, then
#   fan-out each chunk to a GPU worker (Ray / Celery / SageMaker Processing).
#   Each worker runs the full pipeline on its chunk independently.
#   A final "concat_demuxer" stitches all dubbed chunks back together.
#   This module is already chunk-oriented, so the extension is trivial.
# ---------------------------------------------------------------------------

import subprocess
import os
import logging

logger = logging.getLogger(__name__)


def extract_segment(
    input_video: str,
    output_dir: str,
    start_sec: float,
    end_sec: float,
) -> dict:
    """
    Cut a time-range from a video and produce a video clip + WAV audio.

    We re-encode (not stream-copy) because:
      • Stream copy can only cut at keyframes — not frame-accurate.
      • Lip-sync requires exact frame boundaries downstream.

    Args:
        input_video : Path to the source MP4 / MOV / etc.
        output_dir  : Where to write segment.mp4 and segment.wav.
        start_sec   : Start of the range in seconds  (e.g. 15.0).
        end_sec     : End of the range in seconds     (e.g. 30.0).

    Returns:
        dict  {"video": <path>, "audio": <path>, "duration": <float>}

    Raises:
        FileNotFoundError – source video missing.
        ValueError        – bad time range.
        RuntimeError      – ffmpeg non-zero exit.
    """

    # ── Validate ─────────────────────────────────────────────────────────
    if not os.path.isfile(input_video):
        raise FileNotFoundError(f"Input video not found: {input_video}")
    if start_sec >= end_sec:
        raise ValueError(f"start ({start_sec}) must be < end ({end_sec})")

    os.makedirs(output_dir, exist_ok=True)

    duration = end_sec - start_sec
    segment_video = os.path.join(output_dir, "segment.mp4")
    segment_audio = os.path.join(output_dir, "segment.wav")

    # ── 1. Extract video segment ─────────────────────────────────────────
    # -ss before -i  = input seeking (fast — seeks in the demuxer, not decoder)
    # -t             = duration, NOT end time
    # -crf 18        = visually lossless H.264 (good balance of size vs quality)
    # -preset fast   = reasonable encode speed for Colab
    video_cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_sec),
        "-i", input_video,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-map", "0",
        segment_video,
    ]
    logger.info("Extracting video segment: %.1fs → %.1fs", start_sec, end_sec)
    logger.debug("cmd: %s", " ".join(video_cmd))
    _run(video_cmd, "video extraction")

    # ── 2. Extract audio as 16 kHz mono WAV ──────────────────────────────
    # Why 16 kHz mono?
    #   • Whisper's native sample rate is 16 kHz.
    #   • XTTS v2 speaker-embedding extraction also uses 16 kHz.
    #   • Mono is standard for speech models (stereo adds no value).
    audio_cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_sec),
        "-i", input_video,
        "-t", str(duration),
        "-vn",                          # discard video
        "-acodec", "pcm_s16le",         # 16-bit PCM
        "-ar", "16000",                 # 16 kHz
        "-ac", "1",                     # mono
        segment_audio,
    ]
    logger.info("Extracting audio (16 kHz mono WAV)")
    _run(audio_cmd, "audio extraction")

    # ── Sanity check ─────────────────────────────────────────────────────
    for path, label in [(segment_video, "video"), (segment_audio, "audio")]:
        if not os.path.isfile(path):
            raise RuntimeError(f"{label} segment was not created by ffmpeg")

    logger.info("Extraction done → %s , %s", segment_video, segment_audio)
    return {"video": segment_video, "audio": segment_audio, "duration": duration}


def extract_audio(video_path: str, output_path: str) -> str:
    """
    Pull the full audio track out of any video as 16 kHz mono WAV.

    Used by the pipeline when we need audio from an intermediate video
    (e.g. after lip-sync, before face enhancement).

    Returns:
        output_path on success.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        output_path,
    ]
    logger.info("Extracting audio → %s", output_path)
    _run(cmd, "audio extraction")
    return output_path


# ── Private helper ───────────────────────────────────────────────────────
def _run(cmd: list, label: str) -> None:
    """Run a subprocess and raise RuntimeError on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg {label} failed (rc={result.returncode}):\n{result.stderr}")
