# ---------------------------------------------------------------------------
# dubbing/voice_clone.py — Speaker voice cloning using Coqui XTTS v2.
#
# PURPOSE:
#   Given a reference audio clip of the original speaker AND a Hindi text
#   string, generate Hindi speech that sounds like the original speaker.
#
# WHY XTTS v2?
#   • Open-source (MPL-2.0) — no API cost.
#   • Supports Hindi out of the box (multi-lingual, 17 languages).
#   • True voice cloning — uses a short reference clip (~6-15 s) to capture
#     speaker timbre, pitch, and cadence.
#   • Runs on a T4 GPU (~5 GB VRAM in float32).
#
# HOW IT WORKS (high level):
#   1. A speaker encoder reads the reference WAV and produces a fixed-length
#      speaker embedding vector (captures "who" is speaking).
#   2. The text-to-speech decoder generates a mel-spectrogram conditioned on
#      both the Hindi text and the speaker embedding.
#   3. A HiFi-GAN vocoder converts the mel-spectrogram to a waveform.
#   All three steps happen inside a single model.synthesize() call.
#
# SCALABILITY NOTE:
#   XTTS v2 inference is the slowest step (~2-4× real-time on T4).
#   For 500 hours of video you would:
#     1. Pre-compute the speaker embedding ONCE per speaker (it's reusable).
#     2. Distribute text chunks across multiple GPU workers.
#     3. Each worker loads XTTS v2 and generates audio for its chunk.
#     4. Concatenate the audio chunks in order.
#   Speaker embedding extraction is fast (~200 ms), so step 1 is negligible.
# ---------------------------------------------------------------------------

import gc
import logging
import os

import torch

logger = logging.getLogger(__name__)

# ── Module-level cache ───────────────────────────────────────────────────
_tts = None


def _load_model():
    """
    Lazy-load XTTS v2 via Coqui TTS library.

    The model name 'tts_models/multilingual/multi-dataset/xtts_v2' is the
    official identifier in Coqui's model registry.  On first call it will
    download ~1.8 GB of checkpoints to ~/.local/share/tts/.

    We use gpu=True to run inference on CUDA.  On Colab T4 this uses
    ~5 GB VRAM.
    """
    global _tts
    if _tts is not None:
        return _tts

    logger.info("Loading XTTS v2 model (first call — downloads ~1.8 GB)…")

    from TTS.api import TTS

    # ── Select device ────────────────────────────────────────────────────
    # XTTS v2 needs a GPU for reasonable speed (CPU is ~30× slower).
    use_gpu = torch.cuda.is_available()
    if not use_gpu:
        logger.warning(
            "No GPU detected — voice cloning will be VERY slow. "
            "Use Google Colab with a T4 GPU for production speed."
        )

    _tts = TTS(
        model_name="tts_models/multilingual/multi-dataset/xtts_v2",
        gpu=use_gpu,
    )

    logger.info("XTTS v2 loaded ✓ (device=%s)", "cuda" if use_gpu else "cpu")
    return _tts


def clone_voice(
    reference_audio: str,
    hindi_text: str,
    output_path: str,
) -> str:
    """
    Generate Hindi speech that sounds like the speaker in reference_audio.

    The workflow:
      1. XTTS v2 extracts a speaker embedding from reference_audio.
         (This captures vocal timbre, pitch range, speaking style.)
      2. The TTS decoder generates Hindi speech using that embedding.
      3. The output WAV is written to output_path.

    Args:
        reference_audio : Path to the original speaker's audio (WAV, 6-15 s).
                          Longer clips give better cloning but >30 s has
                          diminishing returns.
        hindi_text      : The Hindi text to speak (output of translate.py).
        output_path     : Where to save the generated WAV file.

    Returns:
        output_path on success.

    Raises:
        FileNotFoundError – reference audio missing.
        RuntimeError      – TTS generation fails.

    IMPORTANT — Duration:
        The generated audio will NOT match the original segment duration.
        Hindi sentences are often longer/shorter than English.
        Use duration_match.py AFTER this step to time-stretch to the
        correct length.
    """

    if not os.path.isfile(reference_audio):
        raise FileNotFoundError(f"Reference audio not found: {reference_audio}")
    if not hindi_text.strip():
        raise ValueError("hindi_text is empty — nothing to synthesize.")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    tts = _load_model()

    logger.info("Cloning voice → Hindi TTS for: '%.60s…'", hindi_text)

    # ── Generate speech ──────────────────────────────────────────────────
    # tts_to_file() does everything in one call:
    #   1. Encodes reference_audio into a speaker embedding.
    #   2. Tokenizes hindi_text for the Hindi language head.
    #   3. Runs autoregressive decoding → mel spectrogram.
    #   4. Vocodes mel → waveform.
    #   5. Writes WAV to output_path.
    #
    # language="hi" tells XTTS v2 to use its Hindi phoneme set.
    # speaker_wav is the reference clip for voice cloning.
    tts.tts_to_file(
        text=hindi_text,
        file_path=output_path,
        speaker_wav=reference_audio,
        language="hi",
    )

    if not os.path.isfile(output_path):
        raise RuntimeError(f"XTTS v2 did not produce output at {output_path}")

    logger.info("Voice cloning done → %s", output_path)
    return output_path


def unload_model() -> None:
    """
    Free XTTS v2 from GPU memory after voice cloning is complete.

    Called by dub_video.py before loading the lip-sync model.
    Same pattern as translate.unload_model() — sequential model loading
    to stay within 16 GB VRAM on a free Colab T4.
    """
    global _tts
    if _tts is not None:
        del _tts
        _tts = None
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.info("XTTS v2 unloaded — GPU memory freed ✓")
