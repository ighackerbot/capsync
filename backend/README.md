# Backend - Capsync Video Captioning Services

Backend services for the Capsync video captioning application, including the FastAPI server, video rendering service, and ML models.

## Architecture

```
backend/
├── api/                   # FastAPI REST API
│   ├── main.py           # API endpoints
│   └── requirements.txt  # Python dependencies
├── services/
│   └── render/           # Remotion video rendering service
│       ├── render.ts     # Rendering script
│       ├── package.json  # Node.js dependencies
│       └── tsconfig.json # TypeScript configuration
└── models/
    └── whisper/          # Whisper AI model files
```

## Services

### 1. API Service (FastAPI)

Provides REST endpoints for video transcription and rendering.

#### Prerequisites

- Python 3.11
- pip

#### Installation

```bash
cd backend/api
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Running

```bash
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000
```

#### Endpoints

- `POST /transcribe` - Transcribe audio from video
- `POST /render` - Render video with captions
- `GET /docs` - Interactive API documentation

#### Environment Variables

- `WHISPER_MODEL` - Whisper model size (default: `small`)
  - Options: `tiny`, `base`, `small`, `medium`, `large`
- `WHISPER_COMPUTE` - Compute type (default: `int8`)

### 2. Render Service (TypeScript/Remotion)

Handles video composition and rendering with captions.

#### Prerequisites

- Node.js (v16 or higher)
- npm

#### Installation

```bash
cd backend/services/render
npm install
```

#### Usage

This service is called automatically by the API when rendering videos. It can also be used standalone:

```bash
npx ts-node render.ts \
  --input /path/to/video.mp4 \
  --captions /path/to/captions.json \
  --style bottom-centered \
  --out /path/to/output.mp4
```

#### Caption Styles

- `bottom-centered` - Classic centered bottom captions
- `top-bar` - Top bar style captions
- `karaoke` - Karaoke-style word highlighting

### 3. Whisper Models

Pre-trained Whisper models for speech-to-text transcription.

The models are automatically downloaded on first use and cached in `backend/models/whisper/`.

## Development

### Running All Services

Use the convenience startup script from the project root:

```bash
bash scripts/start.sh
```

This will start both the backend API and frontend development server.

### API Documentation

When the API is running, visit `http://127.0.0.1:8000/docs` for interactive API documentation.

## Technology Stack

- **FastAPI** - Modern Python web framework
- **faster-whisper** - Optimized Whisper implementation
- **Remotion** - Programmatic video creation
- **TypeScript** - Type-safe rendering scripts
