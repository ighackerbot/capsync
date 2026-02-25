#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# dubbing/dub_video.py — Main pipeline orchestrator for Hindi video dubbing.
#
# PURPOSE:
#   This is the single entry point that chains all modules together:
#     1. extract.py   → Cut a 15-second video segment + extract audio
#     2. Whisper       → Transcribe the English audio (reuses capsync logic)
#     3. translate.py  → Translate English text to Hindi via IndicTrans2
#     4. voice_clone.py→ Generate Hindi speech in the original speaker's voice
#     5. duration_match.py → Time-stretch Hindi audio to fit original duration
#     6. lip_sync.py   → Re-animate lip movements to match Hindi audio
#     7. enhance.py    → Restore face quality with GFPGAN
#
# USAGE:
#   python dub_video.py --input video.mp4 --start 15 --end 30 --output dubbed.mp4
#
# DESIGN DECISIONS:
#   • Sequential model loading — on a T4 (16 GB VRAM) we can't keep all
#     models resident simultaneously.  Each module loads → uses → unloads
#     its model before the next one starts.  Memory timeline:
#       Whisper (~2 GB) → unload → IndicTrans2 (~4 GB) → unload →
#       XTTS v2 (~5 GB) → unload → VideoReTalking (~3 GB) → unload →
#       GFPGAN (~0.5 GB)
#   • Temp directory per run — all intermediate files go into a timestamped
#     temp dir.  On success, only the final output is kept.  On failure,
#     the temp dir is preserved for debugging.
#   • Structured logging — every step logs timing and file sizes to help
#     identify bottlenecks.
#
# SCALABILITY — HOW TO PROCESS 500 HOURS OVERNIGHT:
#   This script processes one segment at a time.  To scale to full-length
#   videos or massive batches, you would:
#
#   1. CHUNKING (this module's extract_segment already handles this):
#      Split the video into N-second chunks (e.g. 10-15 s each).
#      Each chunk is self-contained — independent audio + video.
#
#   2. DISTRIBUTED GPU WORKERS:
#      Use a task queue (Celery + Redis, AWS SQS, or Ray):
#        - Producer: pushes chunk metadata to the queue.
#        - Consumers: GPU workers pop chunks, run this pipeline, push results.
#      Each worker needs 1× T4 GPU and runs this exact script.
#
#   3. CONCAT/STITCH:
#      After all chunks are dubbed, concatenate them:
#        ffmpeg -f concat -i file_list.txt -c copy full_dubbed.mp4
#      The concat demuxer handles frame-accurate stitching.
#
#   4. COST ESTIMATE (AWS):
#      - g4dn.xlarge (1× T4) = $0.526/hr on-demand, ~$0.16/hr spot.
#      - Processing speed ≈ 3-5× real-time (15 s clip → 45-75 s of compute).
#      - 500 hours of video at 5× real-time = 2,500 GPU-hours.
#      - Cost: 2,500 × $0.16 = ~$400 on spot instances.
#
#   5. ORCHESTRATION:
#      Use AWS Step Functions or Airflow to manage the batch pipeline:
#        Ingest → Chunk → Fan-out to GPU fleet → Stitch → Deliver
#
#   The code below includes a batch_dub_video() placeholder that shows
#   the chunking + loop structure.  The distributed fan-out is an
#   infrastructure concern, not a code concern.
# ---------------------------------------------------------------------------

import argparse
import gc
import logging
import os
import sys
import tempfile
import time
from datetime import datetime

import torch

# ── Local module imports ─────────────────────────────────────────────────
# We import from the dubbing package (sibling modules).
from dubbing.extract import extract_segment
from dubbing.translate import translate_to_hindi, unload_model as unload_translator
from dubbing.voice_clone import clone_voice, unload_model as unload_voice_cloner
from dubbing.duration_match import match_duration
from dubbing.lip_sync import lip_sync_video
from dubbing.enhance import enhance_faces


# ── Logging setup ────────────────────────────────────────────────────────
def _setup_logging(verbose: bool = False) -> None:
    """
    Configure structured logging for the entire pipeline.

    Log format includes timestamp + module name + level so you can
    trace exactly which step produced which output.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


# ── Whisper transcription (reuses capsync's faster-whisper) ──────────────
def _transcribe(audio_path: str, model_size: str = "small") -> list:
    """
    Transcribe an audio file using faster-whisper.

    This reuses the same Whisper setup as capsync's backend/api/main.py.
    We import faster_whisper directly (it's already a dependency).

    Args:
        audio_path : Path to 16 kHz mono WAV file.
        model_size : Whisper model size ("tiny", "base", "small", "medium", "large-v2").

    Returns:
        List of segment dicts:
            [{"id": "0", "start": 0.0, "end": 2.5, "text": "Hello"}, ...]
    """
    logger = logging.getLogger("dub_video.transcribe")
    logger.info("Loading Whisper '%s' model…", model_size)

    from faster_whisper import WhisperModel

    # ── Compute type selection ───────────────────────────────────────────
    # int8 on CPU, float16 on GPU — best speed/accuracy tradeoff for each.
    if torch.cuda.is_available():
        compute_type = "float16"
        device = "cuda"
    else:
        compute_type = "int8"
        device = "cpu"

    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    logger.info("Transcribing audio…")
    segments_iter, info = model.transcribe(
        audio_path,
        task="transcribe",      # Transcribe (not translate — we do that ourselves)
        language="en",          # Source language is English
    )

    segments = []
    for i, seg in enumerate(segments_iter):
        segments.append({
            "id": str(i),
            "start": float(seg.start),
            "end": float(seg.end),
            "text": seg.text.strip(),
        })
        logger.debug("  [%.1f–%.1f] %s", seg.start, seg.end, seg.text.strip())

    logger.info("Transcribed %d segments (detected language: %s, prob: %.2f)",
                len(segments), info.language, info.language_probability)

    # ── Unload Whisper to free VRAM for the translator ───────────────────
    del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.info("Whisper unloaded — GPU memory freed ✓")

    return segments


# ── Main pipeline ────────────────────────────────────────────────────────
def dub_video(
    input_video: str,
    output_path: str,
    start_sec: float = 15.0,
    end_sec: float = 30.0,
    whisper_model: str = "small",
    keep_temp: bool = False,
) -> str:
    """
    Run the full Hindi dubbing pipeline on a video segment.

    This is the main function that orchestrates all steps.  Each step
    produces intermediate files in a temp directory.  The final output
    is a single MP4 file.

    Args:
        input_video   : Path to the source video.
        output_path   : Where to save the final dubbed MP4.
        start_sec     : Start of the segment to dub (seconds).
        end_sec       : End of the segment to dub (seconds).
        whisper_model : Whisper model size for transcription.
        keep_temp     : If True, don't delete intermediate files.

    Returns:
        output_path on success.
    """
    logger = logging.getLogger("dub_video")
    pipeline_start = time.time()

    # ── Create temp working directory ────────────────────────────────────
    # All intermediate files go here.  Named with timestamp for debugging.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_dir = tempfile.mkdtemp(prefix=f"dubbing_{timestamp}_")
    logger.info("Working directory: %s", temp_dir)

    try:
        # ════════════════════════════════════════════════════════════════
        # STEP 1: Extract video segment + audio
        # ════════════════════════════════════════════════════════════════
        logger.info("=" * 60)
        logger.info("STEP 1/7: Extracting segment (%.1f–%.1f s)", start_sec, end_sec)
        logger.info("=" * 60)

        step_start = time.time()
        segment = extract_segment(input_video, temp_dir, start_sec, end_sec)
        segment_video = segment["video"]    # segment.mp4
        segment_audio = segment["audio"]    # segment.wav
        target_duration = segment["duration"]

        logger.info("  → Done in %.1f s", time.time() - step_start)

        # ════════════════════════════════════════════════════════════════
        # STEP 2: Transcribe English audio with Whisper
        # ════════════════════════════════════════════════════════════════
        logger.info("=" * 60)
        logger.info("STEP 2/7: Transcribing with Whisper ('%s')", whisper_model)
        logger.info("=" * 60)

        step_start = time.time()
        segments = _transcribe(segment_audio, whisper_model)

        if not segments:
            raise RuntimeError("Whisper produced no segments — is there speech in this clip?")

        logger.info("  → %d segments in %.1f s", len(segments), time.time() - step_start)

        # ════════════════════════════════════════════════════════════════
        # STEP 3: Translate English → Hindi with IndicTrans2
        # ════════════════════════════════════════════════════════════════
        logger.info("=" * 60)
        logger.info("STEP 3/7: Translating to Hindi (IndicTrans2)")
        logger.info("=" * 60)

        step_start = time.time()
        translated = translate_to_hindi(segments)

        # Combine all Hindi text into one string for voice synthesis.
        # We join with spaces because XTTS v2 handles punctuation internally.
        hindi_text = " ".join(seg["hindi"] for seg in translated if seg["hindi"])

        if not hindi_text.strip():
            raise RuntimeError("Translation produced empty Hindi text.")

        logger.info("  → Hindi: '%s'", hindi_text[:100] + ("…" if len(hindi_text) > 100 else ""))
        logger.info("  → Done in %.1f s", time.time() - step_start)

        # Free IndicTrans2 VRAM before loading XTTS v2.
        unload_translator()

        # ════════════════════════════════════════════════════════════════
        # STEP 4: Clone speaker voice + generate Hindi audio
        # ════════════════════════════════════════════════════════════════
        logger.info("=" * 60)
        logger.info("STEP 4/7: Voice cloning with XTTS v2")
        logger.info("=" * 60)

        step_start = time.time()
        hindi_audio_raw = os.path.join(temp_dir, "hindi_raw.wav")
        clone_voice(segment_audio, hindi_text, hindi_audio_raw)

        logger.info("  → Done in %.1f s", time.time() - step_start)

        # Free XTTS v2 VRAM before lip-sync.
        unload_voice_cloner()

        # ════════════════════════════════════════════════════════════════
        # STEP 5: Time-stretch Hindi audio to match original duration
        # ════════════════════════════════════════════════════════════════
        logger.info("=" * 60)
        logger.info("STEP 5/7: Duration matching (target=%.2f s)", target_duration)
        logger.info("=" * 60)

        step_start = time.time()
        hindi_audio_matched = os.path.join(temp_dir, "hindi_matched.wav")
        match_duration(hindi_audio_raw, target_duration, hindi_audio_matched)

        logger.info("  → Done in %.1f s", time.time() - step_start)

        # ════════════════════════════════════════════════════════════════
        # STEP 6: Lip-sync video to Hindi audio
        # ════════════════════════════════════════════════════════════════
        logger.info("=" * 60)
        logger.info("STEP 6/7: Lip-sync with VideoReTalking")
        logger.info("=" * 60)

        step_start = time.time()
        lip_synced = os.path.join(temp_dir, "lip_synced.mp4")
        lip_sync_video(segment_video, hindi_audio_matched, lip_synced)

        logger.info("  → Done in %.1f s", time.time() - step_start)

        # ════════════════════════════════════════════════════════════════
        # STEP 7: Face restoration with GFPGAN
        # ════════════════════════════════════════════════════════════════
        logger.info("=" * 60)
        logger.info("STEP 7/7: Face enhancement with GFPGAN")
        logger.info("=" * 60)

        step_start = time.time()
        enhance_faces(lip_synced, output_path, audio_path=hindi_audio_matched)

        logger.info("  → Done in %.1f s", time.time() - step_start)

        # ════════════════════════════════════════════════════════════════
        # DONE
        # ════════════════════════════════════════════════════════════════
        total_time = time.time() - pipeline_start
        logger.info("=" * 60)
        logger.info("PIPELINE COMPLETE in %.1f s", total_time)
        logger.info("Output: %s", output_path)
        logger.info("=" * 60)

        return output_path

    except Exception:
        logger.exception("Pipeline failed — intermediate files kept at: %s", temp_dir)
        raise

    finally:
        # ── Cleanup temp directory ───────────────────────────────────────
        if not keep_temp and os.path.isfile(output_path):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.debug("Cleaned up temp dir: %s", temp_dir)


# ── Batch processing placeholder ────────────────────────────────────────
def batch_dub_video(
    input_video: str,
    output_path: str,
    chunk_duration_sec: float = 15.0,
    whisper_model: str = "small",
) -> str:
    """
    [PLACEHOLDER] Process a full-length video by splitting into chunks.

    This function demonstrates the structure for scaling the pipeline to
    full-length videos.  Each chunk is processed independently, then the
    results are concatenated.

    For true distributed processing, replace the for-loop below with a
    task queue fan-out (Celery, Ray, AWS Batch).

    Args:
        input_video        : Path to the full-length video.
        output_path        : Where to save the final dubbed video.
        chunk_duration_sec : Duration of each chunk (seconds).
        whisper_model      : Whisper model size.

    Returns:
        output_path on success.
    """
    logger = logging.getLogger("dub_video.batch")
    import subprocess

    # ── Get total video duration ─────────────────────────────────────────
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        input_video,
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    total_duration = float(result.stdout.strip())
    logger.info("Total video duration: %.1f s", total_duration)

    # ── Generate chunk boundaries ────────────────────────────────────────
    chunks = []
    start = 0.0
    while start < total_duration:
        end = min(start + chunk_duration_sec, total_duration)
        chunks.append((start, end))
        start = end

    logger.info("Split into %d chunks of %.1f s each", len(chunks), chunk_duration_sec)

    # ── Process each chunk ───────────────────────────────────────────────
    # In production, this loop would be replaced with a distributed
    # task queue.  Each iteration is fully independent.
    chunk_outputs = []
    for i, (start, end) in enumerate(chunks):
        logger.info("Processing chunk %d/%d (%.1f–%.1f s)", i + 1, len(chunks), start, end)
        chunk_output = output_path.replace(".mp4", f"_chunk_{i:04d}.mp4")

        dub_video(
            input_video=input_video,
            output_path=chunk_output,
            start_sec=start,
            end_sec=end,
            whisper_model=whisper_model,
        )
        chunk_outputs.append(chunk_output)

    # ── Concatenate all chunks ───────────────────────────────────────────
    # ffmpeg concat demuxer joins the chunks without re-encoding.
    concat_list = output_path.replace(".mp4", "_concat_list.txt")
    with open(concat_list, "w") as f:
        for path in chunk_outputs:
            f.write(f"file '{path}'\n")

    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        output_path,
    ]

    subprocess.run(concat_cmd, check=True, capture_output=True, text=True)

    # ── Cleanup chunk files ──────────────────────────────────────────────
    for path in chunk_outputs:
        os.remove(path)
    os.remove(concat_list)

    logger.info("Batch processing complete → %s", output_path)
    return output_path


# ── CLI entry point ──────────────────────────────────────────────────────
def main():
    """
    Parse command-line arguments and run the dubbing pipeline.

    Usage:
        python dub_video.py --input video.mp4 --start 15 --end 30 --output dubbed.mp4
        python dub_video.py --input video.mp4 --batch  # Process entire video
    """
    parser = argparse.ArgumentParser(
        description="Hindi Video Dubbing Pipeline — Capsync Extension",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dub a 15-second segment (default: 0:15–0:30)
  python dub_video.py --input video.mp4 --output dubbed.mp4

  # Dub a custom range
  python dub_video.py --input video.mp4 --start 60 --end 90 --output dubbed.mp4

  # Process entire video in chunks (placeholder — see batch_dub_video)
  python dub_video.py --input video.mp4 --batch --output dubbed.mp4

  # Verbose logging + keep intermediate files
  python dub_video.py --input video.mp4 --output dubbed.mp4 -v --keep-temp
        """,
    )

    parser.add_argument(
        "--input", "-i", required=True,
        help="Path to the input video file (MP4, MOV, AVI, etc.)",
    )
    parser.add_argument(
        "--output", "-o", required=True,
        help="Path for the final dubbed output MP4",
    )
    parser.add_argument(
        "--start", type=float, default=15.0,
        help="Start time in seconds (default: 15.0)",
    )
    parser.add_argument(
        "--end", type=float, default=30.0,
        help="End time in seconds (default: 30.0)",
    )
    parser.add_argument(
        "--whisper-model", default="small",
        choices=["tiny", "base", "small", "medium", "large-v2"],
        help="Whisper model size (default: small)",
    )
    parser.add_argument(
        "--batch", action="store_true",
        help="Process the entire video in chunks (placeholder mode)",
    )
    parser.add_argument(
        "--chunk-duration", type=float, default=15.0,
        help="Chunk duration in seconds for batch mode (default: 15.0)",
    )
    parser.add_argument(
        "--keep-temp", action="store_true",
        help="Keep intermediate files for debugging",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable debug-level logging",
    )

    args = parser.parse_args()

    # ── Setup logging ────────────────────────────────────────────────────
    _setup_logging(verbose=args.verbose)
    logger = logging.getLogger("dub_video")

    # ── Validate input ───────────────────────────────────────────────────
    if not os.path.isfile(args.input):
        logger.error("Input video not found: %s", args.input)
        sys.exit(1)

    # ── Run pipeline ─────────────────────────────────────────────────────
    try:
        if args.batch:
            batch_dub_video(
                input_video=args.input,
                output_path=args.output,
                chunk_duration_sec=args.chunk_duration,
                whisper_model=args.whisper_model,
            )
        else:
            dub_video(
                input_video=args.input,
                output_path=args.output,
                start_sec=args.start,
                end_sec=args.end,
                whisper_model=args.whisper_model,
                keep_temp=args.keep_temp,
            )
    except Exception:
        logger.exception("Pipeline failed.")
        sys.exit(1)

    logger.info("✓ All done. Output: %s", args.output)


if __name__ == "__main__":
    main()
