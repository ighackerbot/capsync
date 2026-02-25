# ---------------------------------------------------------------------------
# dubbing/enhance.py — Face restoration using GFPGAN v1.4.
#
# PURPOSE:
#   After lip-sync, the face region often shows artifacts — slight blur,
#   color shifts, or loss of fine detail (skin texture, teeth, eyebrows).
#   GFPGAN is a face restoration GAN that fixes these artifacts and
#   produces a sharp, natural-looking face.  This is the "polish" step.
#
# WHY GFPGAN (not CodeFormer)?
#   Both are excellent.  We chose GFPGAN because:
#   • Lighter weight (~350 MB vs CodeFormer's ~1 GB).
#   • Faster inference (can do 30+ fps on T4).
#   • Built-in support for video processing via basicsr/realesrgan.
#   • The gfpgan pip package handles everything.
#   If you prefer CodeFormer, swap in the CodeFormer inference call below —
#   the interface is intentionally identical.
#
# APPROACH:
#   We process the video FRAME-BY-FRAME:
#     1. Extract all frames as PNGs using ffmpeg.
#     2. Run GFPGAN on each face-containing frame.
#     3. Reassemble frames into a video, muxing the Hindi audio back in.
#   This is simpler and more robust than trying to process the video
#   directly through GFPGAN's video interface.
#
# SCALABILITY NOTE:
#   Frame-by-frame processing is embarrassingly parallel.  For 500 hours:
#     1. Extract frames to a shared filesystem (S3 / GCS).
#     2. Distribute frame batches across GPU workers.
#     3. Each worker enhances its batch and writes back.
#     4. A coordinator reassembles the video from enhanced frames.
#   GFPGAN processes ~30 fps on T4, so 500 hours ≈ 54M frames ≈ 500 GPU-hours.
# ---------------------------------------------------------------------------

import glob
import logging
import os
import subprocess

logger = logging.getLogger(__name__)


def enhance_faces(
    input_video: str,
    output_video: str,
    audio_path: str | None = None,
) -> str:
    """
    Apply GFPGAN face restoration to every frame of a video.

    Workflow:
      1. ffmpeg → extract frames as PNG images.
      2. GFPGAN → enhance each frame (face regions only).
      3. ffmpeg → reassemble enhanced frames into a video.
      4. ffmpeg → mux the Hindi audio track back in.

    Args:
        input_video  : Path to the lip-synced video (from lip_sync.py).
        output_video : Path for the final enhanced MP4.
        audio_path   : Optional path to the Hindi audio to mux in.
                       If None, we copy audio from input_video.

    Returns:
        output_video on success.

    Raises:
        FileNotFoundError – input video missing.
        RuntimeError      – any ffmpeg / GFPGAN step fails.
    """
    if not os.path.isfile(input_video):
        raise FileNotFoundError(f"Input video not found: {input_video}")

    # ── Set up temp directories ──────────────────────────────────────────
    work_dir = os.path.join(os.path.dirname(output_video) or ".", "_enhance_tmp")
    frames_dir = os.path.join(work_dir, "frames")
    enhanced_dir = os.path.join(work_dir, "enhanced")
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(enhanced_dir, exist_ok=True)

    try:
        # ── Step 1: Extract frames ───────────────────────────────────────
        logger.info("Step 1/4: Extracting frames from video…")
        _extract_frames(input_video, frames_dir)

        # ── Step 2: Get source video FPS ─────────────────────────────────
        fps = _get_fps(input_video)
        logger.info("Source video FPS: %s", fps)

        # ── Step 3: Enhance faces with GFPGAN ────────────────────────────
        logger.info("Step 2/4: Enhancing faces with GFPGAN v1.4…")
        _enhance_frames(frames_dir, enhanced_dir)

        # ── Step 4: Reassemble video from enhanced frames ────────────────
        logger.info("Step 3/4: Reassembling video from enhanced frames…")
        temp_video = os.path.join(work_dir, "enhanced_no_audio.mp4")
        _reassemble_video(enhanced_dir, temp_video, fps)

        # ── Step 5: Mux audio back in ───────────────────────────────────
        logger.info("Step 4/4: Muxing audio into enhanced video…")
        _mux_audio(temp_video, audio_path or input_video, output_video)

    finally:
        # ── Cleanup temp files ───────────────────────────────────────────
        # We keep the work_dir on failure for debugging, delete on success.
        if os.path.isfile(output_video):
            import shutil
            shutil.rmtree(work_dir, ignore_errors=True)
            logger.debug("Cleaned up temp dir: %s", work_dir)

    if not os.path.isfile(output_video):
        raise RuntimeError(f"Enhancement did not produce output at {output_video}")

    logger.info("Face enhancement done → %s", output_video)
    return output_video


# ── Private helpers ──────────────────────────────────────────────────────


def _extract_frames(video_path: str, frames_dir: str) -> None:
    """Extract every frame from video as frame_NNNNNN.png."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-qscale:v", "2",      # High quality PNG extraction
        os.path.join(frames_dir, "frame_%06d.png"),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Frame extraction failed:\n{result.stderr}")

    count = len(glob.glob(os.path.join(frames_dir, "frame_*.png")))
    logger.info("Extracted %d frames", count)


def _get_fps(video_path: str) -> str:
    """Get the FPS of a video using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning("ffprobe failed — defaulting to 25 fps")
        return "25"
    # ffprobe returns fps as a fraction like "30000/1001" or "25/1"
    return result.stdout.strip() or "25"


def _enhance_frames(frames_dir: str, enhanced_dir: str) -> None:
    """
    Run GFPGAN on each frame in frames_dir.

    Uses the gfpgan Python package (pip install gfpgan).
    The GFPGANer class handles model loading, face detection, enhancement,
    and pasting the enhanced face back onto the original frame.
    """
    import cv2
    import numpy as np

    # Lazy import — only needed during enhancement
    from gfpgan import GFPGANer

    import torch

    # ── Initialize GFPGAN ────────────────────────────────────────────────
    # model_path — downloads automatically on first use.
    # upscale=1  — don't upscale (keep original resolution).
    # arch='clean' — use the "clean" architecture (best for faces).
    # bg_upsampler=None — we don't need background super-resolution.
    device = "cuda" if torch.cuda.is_available() else "cpu"

    restorer = GFPGANer(
        model_path="https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/GFPGANv1.4.pth",
        upscale=1,                  # 1× = keep original resolution
        arch="clean",               # "clean" variant for best quality
        channel_multiplier=2,       # Standard width multiplier
        bg_upsampler=None,          # Skip background super-res (faster)
        device=device,
    )

    logger.info("GFPGAN initialized on %s", device)

    # ── Process each frame ───────────────────────────────────────────────
    frame_paths = sorted(glob.glob(os.path.join(frames_dir, "frame_*.png")))
    total = len(frame_paths)

    for i, frame_path in enumerate(frame_paths):
        # Read frame
        img = cv2.imread(frame_path, cv2.IMREAD_COLOR)
        if img is None:
            logger.warning("Could not read frame: %s — skipping", frame_path)
            continue

        # Enhance face(s) in this frame
        # Returns:
        #   cropped_faces — list of detected+cropped faces
        #   restored_faces — list of enhanced face images
        #   restored_img — full frame with enhanced faces pasted back
        try:
            _, _, restored_img = restorer.enhance(
                img,
                has_aligned=False,      # Faces are NOT pre-aligned
                only_center_face=True,  # Single-speaker: only enhance center face
                paste_back=True,        # Paste enhanced face back onto frame
            )
        except Exception as e:
            # If GFPGAN fails on a frame (no face detected, etc.),
            # use the original frame instead of crashing.
            logger.warning("GFPGAN failed on frame %d: %s — using original", i, e)
            restored_img = img

        # Write enhanced frame
        out_path = os.path.join(enhanced_dir, os.path.basename(frame_path))
        cv2.imwrite(out_path, restored_img)

        # Log progress every 10%
        if (i + 1) % max(1, total // 10) == 0:
            logger.info("  Enhanced %d/%d frames (%.0f%%)", i + 1, total, (i + 1) / total * 100)

    logger.info("All %d frames enhanced ✓", total)


def _reassemble_video(frames_dir: str, output_video: str, fps: str) -> None:
    """Reassemble enhanced PNG frames into an MP4 (no audio)."""
    cmd = [
        "ffmpeg", "-y",
        "-framerate", fps,
        "-i", os.path.join(frames_dir, "frame_%06d.png"),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",      # Required for compatibility
        output_video,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Video reassembly failed:\n{result.stderr}")


def _mux_audio(video_path: str, audio_source: str, output_path: str) -> None:
    """
    Combine a video (no audio) with an audio track.

    Uses stream copy (no re-encoding) for speed — the video is already
    in the right codec from _reassemble_video().
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,           # Enhanced video (no audio)
        "-i", audio_source,         # Audio source (Hindi audio or original video)
        "-c:v", "copy",             # Don't re-encode video
        "-c:a", "aac",              # Encode audio as AAC
        "-b:a", "192k",
        "-map", "0:v:0",            # Take video from first input
        "-map", "1:a:0",            # Take audio from second input
        "-shortest",                # End at the shortest stream
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Audio muxing failed:\n{result.stderr}")
