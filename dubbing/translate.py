# ---------------------------------------------------------------------------
# dubbing/translate.py — English → Hindi translation using IndicTrans2.
#
# PURPOSE:
#   Takes Whisper segments (English text + timestamps) and translates
#   each into natural, context-aware Hindi.
#
# WHY IndicTrans2 (not Google Translate / ChatGPT)?
#   • Open-source — no API key, no cost, no rate limits.
#   • SOTA quality for Indian languages (22 scheduled languages).
#   • 1B-param variant fits on T4 in float16 (~4 GB VRAM).
#   • Produces natural Hindi (not word-for-word literal output).
#
# MODEL:
#   ai4bharat/indictrans2-en-indic-1B  (HuggingFace)
#   Custom SentencePiece tokenizer with language tags.
#   trust_remote_code=True is mandatory (custom model architecture).
#
# SCALABILITY NOTE:
#   Translation is the fastest step in the pipeline — ~50 ms per segment
#   on a T4.  At 500 hours of video the bottleneck is voice cloning, not
#   translation.  If needed, batch all segments into a single generate()
#   call (IndicTrans2 supports batch decoding natively).
# ---------------------------------------------------------------------------

import gc
import logging
from typing import Any, Dict, List

import torch

logger = logging.getLogger(__name__)

# ── Module-level cache (load once, reuse across calls) ───────────────────
_model = None
_tokenizer = None


def _load_model():
    """
    Lazy-load IndicTrans2 model + tokenizer on first call.

    Why lazy?
      1. Model is ~4 GB — don't block import time.
      2. Lets the pipeline unload Whisper first, freeing VRAM.
      3. In distributed mode, not every worker needs this model.
    """
    global _model, _tokenizer
    if _model is not None:
        return _model, _tokenizer

    logger.info("Loading IndicTrans2 En→Hi model (first call — may take ~60 s)…")

    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    model_name = "ai4bharat/indictrans2-en-indic-1B"

    # Tokenizer — handles language-direction tags internally.
    _tokenizer = AutoTokenizer.from_pretrained(
        model_name, trust_remote_code=True,
    )

    # Model — float16 halves VRAM usage (8 GB → 4 GB).
    # device_map="auto" places the model on GPU if available, else CPU.
    _model = AutoModelForSeq2SeqLM.from_pretrained(
        model_name,
        trust_remote_code=True,
        torch_dtype=torch.float16,
        device_map="auto",
    )

    logger.info("IndicTrans2 loaded ✓")
    return _model, _tokenizer


def translate_to_hindi(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Translate a list of Whisper segments from English to Hindi.

    Input format (from Whisper):
        [{"id": "…", "start": 0.0, "end": 2.5, "text": "Hello world"}, …]

    Output — same list with a new "hindi" key added to each dict:
        [{"id": "…", "start": 0.0, "end": 2.5, "text": "Hello world",
          "hindi": "नमस्ते दुनिया"}, …]

    Timestamps and IDs are preserved — they're needed downstream for
    duration matching and lip-sync alignment.

    CONTEXT-AWARE APPROACH:
    We feed each segment individually (not concatenated) because
    IndicTrans2 sentence-level translation is already high quality, and
    splitting a multi-sentence output back to per-segment timing is
    error-prone.  Context is implicitly maintained by beam search.
    """
    if not segments:
        logger.warning("translate_to_hindi received empty segment list.")
        return segments

    model, tokenizer = _load_model()
    device = next(model.parameters()).device

    logger.info("Translating %d segments to Hindi…", len(segments))

    translated = []
    for i, seg in enumerate(segments):
        english = seg["text"].strip()

        # ── Skip empty / silence segments ────────────────────────────────
        if not english:
            seg["hindi"] = ""
            translated.append(seg)
            continue

        # ── Tokenize ─────────────────────────────────────────────────────
        # max_length=256 is generous for a single spoken segment (<10 s).
        inputs = tokenizer(
            english,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=256,
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # ── Generate Hindi translation ───────────────────────────────────
        # num_beams=5     → beam search for higher quality
        # length_penalty  → 1.0 = neutral (don't bias short/long)
        # early_stopping  → stop all beams when first finishes
        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=256,
                num_beams=5,
                length_penalty=1.0,
                early_stopping=True,
            )

        hindi = tokenizer.decode(
            output_ids[0], skip_special_tokens=True, clean_up_tokenization_spaces=True,
        ).strip()

        seg["hindi"] = hindi
        logger.debug("  [%d/%d] '%s' → '%s'", i + 1, len(segments), english, hindi)
        translated.append(seg)

    logger.info("Translation complete — %d segments.", len(translated))
    return translated


def unload_model() -> None:
    """
    Free IndicTrans2 from GPU memory so the next model (XTTS v2) can load.

    On a T4 (16 GB VRAM) we cannot keep IndicTrans2 + XTTS v2 in memory
    simultaneously. The pipeline calls:
        translate.unload_model()   ← frees ~4 GB
        voice_clone.clone_voice()  ← loads XTTS v2 into the freed space
    """
    global _model, _tokenizer
    del _model, _tokenizer
    _model = _tokenizer = None
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.info("IndicTrans2 unloaded — GPU memory freed ✓")
