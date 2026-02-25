# Capsync - AI Video Captioning

<div align="center">

![Capsync Banner](https://img.shields.io/badge/AI-Powered-8B5CF6?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Production%20Ready-10b981?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

**Professional AI-powered video captioning with stunning modern UI**

[Features](#features) • [Tech Stack](#tech-stack) • [Quick Start](#quick-start) • [Architecture](#architecture) • [Deployment](#deployment)

</div>

---

## 📖 Overview

Capsync is a **premium, full-stack web application** that automatically generates and overlays captions on videos using OpenAI's Whisper AI model. Built with modern technologies and featuring a glassmorphic UI design, it showcases professional-grade architecture suitable for production deployment.

### ✨ Key Highlights

- 🎨 **Modern UI** - Glassmorphic design with gradient backgrounds
- 🤖 **AI-Powered** - OpenAI Whisper for accurate transcription
- 🎬 **Multiple Styles** - 3 caption styles (Bottom Centered, Top Bar, Karaoke)
- 🌐 **Multi-language** - English, Hindi, and Hinglish support
- 📱 **Responsive** - Works seamlessly on all devices
- ⚡ **Fast** - Optimized rendering with Remotion

---

## 🚀 Features

### Core Functionality
- **Automatic Transcription** - Upload videos and get accurate captions using Whisper AI
- **Multiple Caption Styles** - Choose from bottom-centered, top-bar, or karaoke-style captions
- **Caption Editing** - Fine-tune transcribed text before rendering
- **Fast Rendering** - Programmatic video rendering with Remotion
- **Progress Tracking** - Visual workflow with Upload → Generate → Customize → Download

### UI/UX Features
- **Glassmorphic Design** - Semi-transparent cards with backdrop blur
- **Gradient Backgrounds** - Vibrant purple-to-blue gradients
- **Smooth Animations** - 60fps transitions and micro-interactions
- **Dark/Light Modes** - Full theme support
- **Drag-and-Drop** - Intuitive file upload with visual feedback

---

## 🛠 Tech Stack

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 18.3.1 | UI framework |
| **Vite** | 5.4.8 | Build tool & dev server |
| **Remotion** | 4.0.0 | Video composition |
| **@remotion/player** | 4.0.0 | Video preview |
| **Axios** | 1.7.7 | HTTP client |
| **Inter Font** | Latest | Professional typography |

**Key Features:**
- Modern React with hooks
- Hot Module Replacement (HMR)
- Fast build times with Vite
- Glassmorphic CSS with backdrop-filter
- CSS custom properties for theming

### Backend

#### API Service (Python)
| Technology | Version | Purpose |
|------------|---------|---------|
| **FastAPI** | 0.115.0 | REST API framework |
| **Uvicorn** | 0.30.6 | ASGI server |
| **faster-whisper** | 1.0.3 | Whisper AI implementation |
| **NumPy** | 1.23.0+ | Numerical processing |
| **python-multipart** | 0.0.9 | File upload handling |
| **FFmpeg** | 0.2.0 | Video processing |

**Key Features:**
- Async/await support
- Type hints with Pydantic
- Automatic API documentation
- CORS middleware
- Optimized Whisper inference

#### Render Service (TypeScript)
| Technology | Version | Purpose |
|------------|---------|---------|
| **Remotion** | 4.0.0 | Video rendering |
| **@remotion/renderer** | 4.0.0 | Server-side rendering |
| **TypeScript** | 5.6.2 | Type safety |
| **ts-node** | 10.9.2 | TypeScript execution |
| **yargs** | 17.7.2 | CLI argument parsing |

### Infrastructure
- **Node.js** - v16+ (Frontend & Render)
- **Python** - 3.11 (Backend API)
- **Whisper Models** - Cached ML models

---

## 🏗 Architecture

### System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        A[React Frontend<br/>Vite + Glassmorphic UI]
    end
    
    subgraph "Server Layer"
        B[FastAPI Backend<br/>Port 8000-8999]
        C[Render Service<br/>Remotion + TypeScript]
    end
    
    subgraph "AI/ML Layer"
        D[Whisper Model<br/>faster-whisper]
    end
    
    subgraph "Storage"
        E[Temp Files<br/>Video Processing]
    end
    
    A -->|HTTP/REST| B
    B -->|Invoke| C
    B -->|Transcribe| D
    B -->|Read/Write| E
    C -->|Read| A
    C -->|Write| E
    
    style A fill:#8B5CF6,color:#fff
    style B fill:#3B82F6,color:#fff
    style C fill:#10b981,color:#fff
    style D fill:#f59e0b,color:#fff
```

### Component Architecture

```mermaid
graph LR
    subgraph "Frontend Components"
        UI[App.jsx<br/>Main Layout]
        UP[UploadZone<br/>File Input]
        VID[VideoPreview<br/>Player]
        STYLE[StyleSelector<br/>Caption Styles]
    end
    
    subgraph "API Endpoints"
        TR[/transcribe<br/>POST]
        REN[/render<br/>POST]
    end
    
    subgraph "Services"
        WH[Whisper Service<br/>Transcription]
        REM[Remotion Service<br/>Rendering]
    end
    
    UI --> UP
    UI --> VID
    UI --> STYLE
    
    UP -->|Upload Video| TR
    TR --> WH
    WH -->|Segments| VID
    
    STYLE -->|Style + Video| REN
    REN --> REM
    REM -->|Captioned Video| VID
    
    style UI fill:#8B5CF6,color:#fff
    style TR fill:#3B82F6,color:#fff
    style REN fill:#3B82F6,color:#fff
    style WH fill:#f59e0b,color:#fff
    style REM fill:#10b981,color:#fff
```

### Data Flow Diagram

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Whisper
    participant Remotion
    
    User->>Frontend: Upload Video
    Frontend->>API: POST /transcribe
    API->>Whisper: Transcribe Audio
    Whisper-->>API: Return Segments
    API-->>Frontend: Caption Data
    Frontend->>User: Display Captions
    
    User->>Frontend: Select Style & Render
    Frontend->>API: POST /render
    API->>Remotion: Render with Captions
    Remotion-->>API: Captioned Video
    API-->>Frontend: Video File
    Frontend->>User: Download Video
```

### Directory Structure

```
capsync-5/
├── frontend/                 # React Application
│   ├── src/
│   │   ├── ui/              # UI Components
│   │   │   ├── App.jsx      # Main app component
│   │   │   ├── global.css   # Styles & theme
│   │   │   └── CaptionStyleSelector.jsx
│   │   └── video/           # Remotion compositions
│   │       ├── CaptionComposition.jsx
│   │       └── root.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── backend/
│   ├── api/                 # FastAPI Server
│   │   ├── main.py          # API routes
│   │   └── requirements.txt
│   ├── services/
│   │   └── render/          # Remotion Rendering
│   │       ├── render.ts
│   │       ├── package.json
│   │       └── tsconfig.json
│   └── models/
│       └── whisper/         # ML Models
│
└── scripts/
    └── start.sh             # Startup script
```

---

## ⚡ Quick Start

### Prerequisites

- **Python 3.11** - For the backend API
- **Node.js 16+** - For frontend and rendering
- **Homebrew** (macOS) - For Python installation

### Installation

```bash
# Clone the repository
git clone https://github.com/ighackerbot/capsync.git
cd capsync

# Run the startup script
bash scripts/start.sh
```

The script will:
1. Create Python virtual environment
2. Install all dependencies
3. Start backend (port 8000-8999)
4. Start frontend (port 5173-5999)
5. Open browser automatically

### Manual Setup

#### Backend

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

### Environment Variables

```bash
# Backend
export WHISPER_MODEL="small"        # Options: tiny, base, small, medium, large
export WHISPER_COMPUTE="int8"       # Compute type
export BACKEND_PORT=8000            # Custom backend port

# Frontend
export VITE_API_BASE="http://127.0.0.1:8000"  # Backend URL
export FRONTEND_PORT=5173                      # Custom frontend port
```

---

## 🐳 Deployment (Docker)

### Quick Deploy

```bash
# Clone and deploy
git clone https://github.com/ighackerbot/capsync.git
cd capsync

# Start everything
docker-compose up -d
```

That's it! Frontend at `http://localhost`, API at `http://localhost:8000`.

### Configuration

Create a `.env` file in the project root:

```bash
# Whisper AI model (tiny, base, small, medium, large)
WHISPER_MODEL=small
WHISPER_COMPUTE=int8

# Frontend → Backend connection
VITE_API_BASE=http://localhost:8000

# Docker project name
COMPOSE_PROJECT_NAME=capsync
```

### Common Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Rebuild after code changes
docker-compose up -d --build

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Production Deployment

For production, update `VITE_API_BASE` in `.env` to your domain and rebuild:

```bash
VITE_API_BASE=https://api.yourdomain.com docker-compose up -d --build
```

### Individual Container Build

```bash
# Backend only
docker build -t capsync-backend -f backend/api/Dockerfile backend/api
docker run -p 8000:8000 -e WHISPER_MODEL=small capsync-backend

# Frontend only
docker build -t capsync-frontend --build-arg VITE_API_BASE=http://localhost:8000 -f frontend/Dockerfile frontend
docker run -p 80:80 capsync-frontend
```


---

## 🔒 Production Checklist

- [ ] Set up SSL/TLS certificates (Let's Encrypt)
- [ ] Configure CORS for production domain
- [ ] Set up environment variables securely
- [ ] Enable rate limiting on API
- [ ] Set up monitoring (Sentry, LogRocket)
- [ ] Configure CDN for static assets
- [ ] Set up database for user data (if adding auth)
- [ ] Enable GZIP compression
- [ ] Set up automated backups
- [ ] Configure firewall rules

---

## 📊 Performance

- **Build Time**: ~30s (frontend)
- **Cold Start**: ~2s (backend)
- **Transcription**: ~0.3x realtime (for "small" model)
- **Rendering**: ~1-2min for 1min video
- **Bundle Size**: ~800KB (frontend, gzipped)

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgments

- **OpenAI Whisper** - For the amazing speech recognition model
- **Remotion** - For programmatic video generation
- **FastAPI** - For the high-performance backend framework

---

## 📧 Contact

**Project Link**: [https://github.com/ighackerbot/capsync](https://github.com/ighackerbot/capsync)

---

<div align="center">

Made with ❤️ using React, FastAPI, and Whisper AI

⭐ Star this repo if you find it helpful!

</div>
