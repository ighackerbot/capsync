# ---------------------------------------------------------------------------
# dubbing/lip_sync.py — Lip-sync using VideoReTalking.
#
# PURPOSE:
#   Given a video of a person speaking and a NEW audio track (Hindi),
#   re-animate the person's lip movements to match the new audio.
#   This is what makes the dubbing look natural — without lip-sync the
#   viewer sees English mouth shapes with Hindi audio (uncanny valley).
#
# WHY VideoReTalking (not Wav2Lip)?
#   • Higher visual quality (preserves more facial detail).
#   • Better temporal consistency (fewer flickering artifacts).
#   • Handles head rotation and varied lighting better.
#   • Open-source (Apache 2.0 license).
#
# HOW IT WORKS:
#   VideoReTalking uses a 3-stage pipeline internally:
#     1. Face detection + landmark extraction (every frame).
#     2. Audio-driven lip region generation (neural net).
#     3. Face blending back into the original frame.
#   We call their inference.py script as a subprocess to keep our code
#   decoupled from their internals (they have many dependencies).
#
# SCALABILITY NOTE:
#   Lip-sync is GPU-intensive (~1-2× real-time on T4) and is typically
#   the second bottleneck after voice cloning.  For 500 hours:
#     1. Pre-segment the video into face-containing clips.
#     2. Distribute across GPU workers (one per clip).
#     3. Workers run VideoReTalking independently.
#     4. Concat results preserving original frame ordering.
#   VideoReTalking processes one face at a time — for multi-speaker
#   videos you'd need face diarization + per-speaker processing.
# ---------------------------------------------------------------------------

import logging
import os
import subprocess

logger = logging.getLogger(__name__)

# ── Where VideoReTalking repo will be cloned to ─────────────────────────
# On Colab this goes into /content/video-retalking.
# Locally it goes next to the dubbing/ folder.
_REPO_DIR = os.environ.get(
    "VIDEO_RETALKING_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "video-retalking"),
)

# ── URLs for pre-trained checkpoints ────────────────────────────────────
# VideoReTalking needs ~2 GB of checkpoints downloaded to ./checkpoints/.
# These are hosted by the original authors on GitHub Releases.
_REPO_URL = "https://github.com/OpenTalker/video-retalking.git"


def _ensure_repo() -> str:
    """
    Clone VideoReTalking repo + download checkpoints if not already present.

    We clone at runtime (not install time) because:
      1. The repo is ~50 MB + 2 GB checkpoints — too big for pip.
      2. Colab environments are ephemeral — each session needs a fresh clone.
      3. Keeping it outside our package avoids polluting our clean structure.

    Returns:
        Absolute path to the cloned repo directory.
    """
    repo_dir = os.path.abspath(_REPO_DIR)

    # ── Clone repo if missing ────────────────────────────────────────────
    if not os.path.isdir(os.path.join(repo_dir, "inference.py")):
        logger.info("Cloning VideoReTalking repo → %s", repo_dir)
        subprocess.run(
            ["git", "clone", _REPO_URL, repo_dir],
            check=True,
            capture_output=True,
            text=True,
        )
    else:
        logger.info("VideoReTalking repo already present at %s", repo_dir)

    # ── Download checkpoints if missing ──────────────────────────────────
    ckpt_dir = os.path.join(repo_dir, "checkpoints")
    if not os.path.isdir(ckpt_dir) or len(os.listdir(ckpt_dir)) == 0:
        logger.info("Downloading VideoReTalking checkpoints (~2 GB)…")

        # The official repo provides a download script.
        # If it doesn't exist, we download the essential checkpoints manually.
        download_script = os.path.join(repo_dir, "download_models.sh")
        if os.path.isfile(download_script):
            subprocess.run(
                ["bash", download_script],
                cwd=repo_dir,
                check=True,
                capture_output=True,
                text=True,
            )
        else:
            # Manual checkpoint download via gdown / wget.
            # This is a fallback — the official script is preferred.
            os.makedirs(ckpt_dir, exist_ok=True)
            _download_checkpoints_manual(ckpt_dir)

        logger.info("Checkpoints downloaded ✓")
    else:
        logger.info("Checkpoints already present ✓")

    # ── Install repo dependencies ────────────────────────────────────────
    req_file = os.path.join(repo_dir, "requirements.txt")
    if os.path.isfile(req_file):
        logger.info("Installing VideoReTalking pip dependencies…")
        subprocess.run(
            ["pip", "install", "-q", "-r", req_file],
            cwd=repo_dir,
            capture_output=True,
            text=True,
        )

    return repo_dir


def _download_checkpoints_manual(ckpt_dir: str) -> None:
    """
    Download VideoReTalking checkpoints individually.

    This is the fallback method.  The checkpoint URLs below point to the
    official releases.  We use gdown where files are on Google Drive and
    wget for direct HTTP links.

    If running on Colab, gdown is pre-installed.  Otherwise pip install it.
    """
    # The exact checkpoint files needed by VideoReTalking.
    # These URLs are from the official repo's README / release page.
    checkpoints = {
        # filename : (url, description)
        "30_net_gen.pth": (
            "https://github.com/OpenTalker/video-retalking/releases/download/v0.0.1/30_net_gen.pth",
            "Face parsing network"
        ),
        "BFM.zip": (
            "https://github.com/OpenTalker/video-retalking/releases/download/v0.0.1/BFM.zip",
            "3D Face Model"
        ),
        "DNet.pt": (
            "https://github.com/OpenTalker/video-retalking/releases/download/v0.0.1/DNet.pt",
            "Deformation network"
        ),
        "ENet.pth": (
            "https://github.com/OpenTalker/video-retalking/releases/download/v0.0.1/ENet.pth",
            "Enhancement network"
        ),
        "expression.mat": (
            "https://github.com/OpenTalker/video-retalking/releases/download/v0.0.1/expression.mat",
            "Expression basis"
        ),
        "face3d_pretrain_epoch_20.pth": (
            "https://github.com/OpenTalker/video-retalking/releases/download/v0.0.1/face3d_pretrain_epoch_20.pth",
            "3D face reconstruction"
        ),
        "GFPGANv1.3.pth": (
            "https://github.com/OpenTalker/video-retalking/releases/download/v0.0.1/GFPGANv1.3.pth",
            "Face restoration (built-in)"
        ),
        "GPEN-BFR-512.pth": (
            "https://github.com/OpenTalker/video-retalking/releases/download/v0.0.1/GPEN-BFR-512.pth",
            "Face enhancement"
        ),
        "LNet.pth": (
            "https://github.com/OpenTalker/video-retalking/releases/download/v0.0.1/LNet.pth",
            "Lip sync network"
        ),
        "ParseNet-latest.pth": (
            "https://github.com/OpenTalker/video-retalking/releases/download/v0.0.1/ParseNet-latest.pth",
            "Face parsing"
        ),
        "shape_predictor_68_face_landmarks.dat": (
            "https://github.com/OpenTalker/video-retalking/releases/download/v0.0.1/shape_predictor_68_face_landmarks.dat",
            "dlib face landmarks"
        ),
    }

    for filename, (url, desc) in checkpoints.items():
        filepath = os.path.join(ckpt_dir, filename)
        if os.path.isfile(filepath):
            continue
        logger.info("Downloading %s (%s)…", filename, desc)
        subprocess.run(
            ["wget", "-q", "-O", filepath, url],
            check=True,
            capture_output=True,
            text=True,
        )

    # Unzip BFM.zip if needed
    bfm_zip = os.path.join(ckpt_dir, "BFM.zip")
    if os.path.isfile(bfm_zip):
        subprocess.run(
            ["unzip", "-o", "-q", bfm_zip, "-d", ckpt_dir],
            capture_output=True, text=True,
        )


def lip_sync_video(
    video_path: str,
    audio_path: str,
    output_path: str,
) -> str:
    """
    Re-animate lip movements in video_path to match audio_path.

    This shells out to VideoReTalking's inference.py script.  We do this
    (rather than importing their Python code) because:
      1. Their code has many implicit sys.path assumptions.
      2. Subprocess isolation prevents dependency conflicts.
      3. If VideoReTalking updates, we just git pull — no code changes.

    Args:
        video_path  : Input video with original lip movements.
        audio_path  : Hindi audio to sync lips to (from duration_match.py).
        output_path : Where to write the lip-synced video.

    Returns:
        output_path on success.

    Raises:
        FileNotFoundError – input files missing.
        RuntimeError      – inference script fails.
    """
    for path, label in [(video_path, "video"), (audio_path, "audio")]:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"{label} not found: {path}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # ── Ensure repo + checkpoints are available ──────────────────────────
    repo_dir = _ensure_repo()

    # ── Build inference command ───────────────────────────────────────────
    # VideoReTalking's inference.py expects:
    #   --face <video>   — the face video
    #   --audio <audio>  — the driving audio
    #   --outfile <path> — where to save the result
    cmd = [
        "python",
        os.path.join(repo_dir, "inference.py"),
        "--face", os.path.abspath(video_path),
        "--audio", os.path.abspath(audio_path),
        "--outfile", os.path.abspath(output_path),
    ]

    logger.info("Running VideoReTalking lip-sync…")
    logger.debug("cmd: %s", " ".join(cmd))

    result = subprocess.run(
        cmd,
        cwd=repo_dir,          # Run from repo dir so relative imports work
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"VideoReTalking inference failed (rc={result.returncode}):\n"
            f"STDOUT: {result.stdout[-500:]}\n"
            f"STDERR: {result.stderr[-500:]}"
        )

    if not os.path.isfile(output_path):
        raise RuntimeError(f"Lip-sync did not produce output at {output_path}")

    logger.info("Lip-sync done → %s", output_path)
    return output_path
