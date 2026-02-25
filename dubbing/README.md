# Hindi Video Dubbing Pipeline

> **Extension of [Capsync](../README.md)** — adds AI-powered Hindi dubbing to the existing video captioning system.

---

## 🎯 What This Does

Takes an English-language video and produces a **Hindi-dubbed version** with:
- 🗣️ **Cloned speaker voice** — Hindi audio sounds like the original speaker
- 👄 **Lip-sync** — mouth movements match the Hindi audio
- 🎨 **Face restoration** — GFPGAN cleans up any lip-sync artifacts

### Pipeline Flow

```
Input Video → Extract Segment → Whisper Transcription → IndicTrans2 Translation
→ XTTS v2 Voice Cloning → Duration Matching → VideoReTalking Lip-Sync
→ GFPGAN Enhancement → Final Dubbed MP4
```

---

## 📁 Project Structure

```
dubbing/
├── __init__.py          # Package init
├── extract.py           # ffmpeg video/audio segment extraction
├── translate.py         # IndicTrans2 English → Hindi translation
├── voice_clone.py       # XTTS v2 speaker voice cloning
├── duration_match.py    # Pitch-preserving time-stretch
├── lip_sync.py          # VideoReTalking lip-sync
├── enhance.py           # GFPGAN face restoration
├── dub_video.py         # Main pipeline orchestrator (CLI entry point)
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

---

## 🚀 Google Colab Setup (Step-by-Step)

### Step 1: Clone the Repository

```python
!git clone https://github.com/ighackerbot/capsync.git
%cd capsync
```

### Step 2: Install System Dependencies

```python
# ffmpeg is pre-installed on Colab.
# rubberband-cli is needed for high-quality time-stretching.
!apt-get install -y rubberband-cli
```

### Step 3: Install Python Dependencies

```python
!pip install -r dubbing/requirements.txt
```

### Step 4: Upload Your Video

```python
from google.colab import files
uploaded = files.upload()  # Upload your .mp4 file
video_name = list(uploaded.keys())[0]
print(f"Uploaded: {video_name}")
```

### Step 5: Run the Pipeline

```python
# Dub a 15-second segment (0:15 to 0:30)
!python -m dubbing.dub_video \
    --input "{video_name}" \
    --start 15 \
    --end 30 \
    --output "dubbed_output.mp4" \
    --whisper-model small \
    -v
```

### Step 6: Download the Result

```python
files.download("dubbed_output.mp4")
```

### Expected Runtime on Colab T4

| Step | Time (15-sec clip) | VRAM |
|---|---|---|
| Extract segment | ~2 s | 0 GB |
| Whisper transcription | ~5 s | ~2 GB |
| IndicTrans2 translation | ~10 s | ~4 GB |
| XTTS v2 voice cloning | ~30-45 s | ~5 GB |
| Duration matching | ~1 s | 0 GB |
| VideoReTalking lip-sync | ~60-90 s | ~3 GB |
| GFPGAN enhancement | ~20-30 s | ~0.5 GB |
| **Total** | **~2-3 min** | **Peak ~5 GB** |

---

## 🧠 Models Used

| Model | Size | Purpose | License |
|---|---|---|---|
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (small) | ~500 MB | English transcription | MIT |
| [IndicTrans2](https://huggingface.co/ai4bharat/indictrans2-en-indic-1B) | ~4 GB | En→Hi translation | MIT |
| [XTTS v2](https://huggingface.co/coqui/XTTS-v2) | ~1.8 GB | Voice cloning + Hindi TTS | MPL-2.0 |
| [VideoReTalking](https://github.com/OpenTalker/video-retalking) | ~2 GB | Lip-sync | Apache-2.0 |
| [GFPGAN v1.4](https://github.com/TencentARC/GFPGAN) | ~350 MB | Face restoration | Apache-2.0 |

> **Total model downloads on first run: ~8.5 GB** (cached after that)

---

## 💰 AWS Cost Estimation

### Per-Minute-of-Video Cost (g4dn.xlarge — 1× T4 GPU)

| Pricing | Rate | Cost per Video-Minute |
|---|---|---|
| On-demand | $0.526/hr | ~$0.044 |
| Spot instance | ~$0.16/hr | ~$0.013 |

**Calculation:**
- Processing speed ≈ 3-5× real-time (1 min video → 3-5 min compute)
- 1 min video at 5× real-time = 5 min GPU = 0.083 hr
- On-demand: 0.083 × $0.526 = **$0.044/min**
- Spot: 0.083 × $0.16 = **$0.013/min**

### Batch Pricing (500 Hours of Video)

| | On-Demand | Spot |
|---|---|---|
| **GPU hours** | ~2,500 hrs | ~2,500 hrs |
| **Total cost** | ~$1,315 | ~$400 |
| **Wall-clock time** (10× T4s) | ~10.4 days | ~10.4 days |
| **Wall-clock time** (50× T4s) | ~2.1 days | ~2.1 days |

---

## 📐 Architecture for Scale (500+ Hours)

```
┌────────────┐     ┌──────────────┐     ┌────────────────┐
│  Ingest    │ ──→ │  Chunker     │ ──→ │  Task Queue    │
│  S3 bucket │     │  (extract.py)│     │  (SQS / Redis) │
└────────────┘     └──────────────┘     └───────┬────────┘
                                                │
                        ┌───────────────────────┼───────────┐
                        ▼                       ▼           ▼
                  ┌──────────┐          ┌──────────┐  ┌──────────┐
                  │ GPU #1   │          │ GPU #2   │  │ GPU #N   │
                  │ T4 worker│          │ T4 worker│  │ T4 worker│
                  │ dub_video│          │ dub_video│  │ dub_video│
                  └────┬─────┘          └────┬─────┘  └────┬─────┘
                       │                     │             │
                       ▼                     ▼             ▼
                  ┌────────────────────────────────────────────┐
                  │  Stitcher (ffmpeg concat demuxer)          │
                  │  → Final dubbed video on S3                │
                  └────────────────────────────────────────────┘
```

Each GPU worker runs the **exact same** `dub_video.py` on its chunk — zero code changes needed. The scaling is purely an infrastructure concern (task queue + auto-scaling group).

---

## 🔧 CLI Reference

```bash
# Basic usage (15-sec segment at 0:15–0:30)
python -m dubbing.dub_video -i video.mp4 -o dubbed.mp4

# Custom time range
python -m dubbing.dub_video -i video.mp4 --start 60 --end 90 -o dubbed.mp4

# Use larger Whisper model for better transcription
python -m dubbing.dub_video -i video.mp4 -o dubbed.mp4 --whisper-model medium

# Full video batch processing
python -m dubbing.dub_video -i video.mp4 -o dubbed.mp4 --batch --chunk-duration 15

# Debug mode (verbose logs + keep temp files)
python -m dubbing.dub_video -i video.mp4 -o dubbed.mp4 -v --keep-temp
```

---

## ⚠️ Known Limitations

1. **Single speaker only** — lip-sync targets the center face. Multi-speaker requires face diarization.
2. **First run is slow** — ~8.5 GB of model downloads. Subsequent runs use cache.
3. **VRAM ceiling** — All models are loaded/unloaded sequentially to fit in 16 GB T4 VRAM.
4. **VideoReTalking cloned at runtime** — ephemeral Colab sessions need re-cloning.

---

## 📝 License

Same as the parent Capsync project — MIT License.
