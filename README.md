# Capsync

A video captioning application that automatically generates and overlays captions on videos using AI-powered speech recognition.

## Features

- 🎥 **Automatic Transcription** - Upload videos and get accurate captions using OpenAI's Whisper model
- 🎨 **Multiple Caption Styles** - Choose from bottom-centered, top-bar, or karaoke-style captions
- ✏️ **Caption Editing** - Fine-tune transcribed text before rendering
- 🚀 **Fast Rendering** - Programmatic video rendering with Remotion
- 🌐 **Modern UI** - Clean, responsive React interface

## Architecture

This project follows an industry-standard monorepo structure with clear separation of concerns:

```
capsync-5/
├── frontend/          # React + Vite UI application
├── backend/
│   ├── api/          # FastAPI REST server
│   ├── services/     # Video rendering service
│   └── models/       # ML models (Whisper)
└── scripts/          # Utility scripts
```

## Quick Start

### Prerequisites

- **Python 3.11** - For the backend API
- **Node.js 16+** - For frontend and rendering service
- **Homebrew** (macOS) - For Python installation

### Installation & Running

The simplest way to get started is using the provided startup script:

```bash
git clone https://github.com/ighackerbot/capsync.git
cd capsync
bash scripts/start.sh
```

This script will:
1. Set up Python virtual environment and install dependencies
2. Install Node.js dependencies for frontend and render service
3. Start the backend API server
4. Start the frontend development server
5. Automatically open the application in your browser

### Manual Setup

If you prefer to run services separately:

#### Backend API

```bash
cd backend/api
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Usage

1. **Upload a Video** - Select a video file (MP4 recommended)
2. **Transcribe** - Click transcribe to generate captions using AI
3. **Edit Captions** - Review and edit the generated caption text
4. **Choose Style** - Select your preferred caption style
5. **Render** - Generate the final video with captions

## Configuration

### Environment Variables

- `WHISPER_MODEL` - Whisper model size (default: `small`)
  - Options: `tiny`, `base`, `small`, `medium`, `large`
  - Larger models are more accurate but slower
- `WHISPER_COMPUTE` - Compute type (default: `int8`)
- `BACKEND_PORT` - Backend API port (default: random 8000-8999)
- `FRONTEND_PORT` - Frontend dev server port (default: random 5173-5999)

## Technology Stack

### Frontend
- React 18
- Vite
- Remotion
- Axios

### Backend
- FastAPI (Python)
- faster-whisper
- Remotion (TypeScript/Node.js)

## Project Structure

See individual README files for detailed information:
- [Frontend Documentation](frontend/README.md)
- [Backend Documentation](backend/README.md)

## Resources

- **Demo Video**: [Watch on Google Drive](https://drive.google.com/file/d/1C6TwIYtc0g7i9eYx1fz5GvtF85sHvlDT/view)
- **Model Download**: [Whisper Models](https://drive.google.com/file/d/1rVm6dwJfJ1LLMjhwVQqNZdKDW08ZlLjp/view)

## API Documentation

When the backend is running, interactive API documentation is available at:
- **Swagger UI**: `http://127.0.0.1:<BACKEND_PORT>/docs`
- **ReDoc**: `http://127.0.0.1:<BACKEND_PORT>/redoc`

## License

See LICENSE file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
