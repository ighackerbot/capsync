# Frontend - Capsync Video Captioning UI

React-based user interface for the Capsync video captioning application.

## Technology Stack

- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **Remotion** - Video composition and rendering
- **Axios** - HTTP client for API communication

## Project Structure

```
frontend/
├── src/
│   ├── main.jsx           # Application entry point
│   ├── ui/                # UI components
│   │   ├── App.jsx
│   │   └── CaptionStyleSelector.jsx
│   └── video/             # Remotion video compositions
│       ├── CaptionComposition.jsx
│       └── root.jsx
├── index.html             # HTML template
├── package.json           # Dependencies and scripts
└── vite.config.js         # Vite configuration
```

## Getting Started

### Prerequisites

- Node.js (v16 or higher)
- npm or yarn

### Installation

```bash
cd frontend
npm install
```

### Development

Start the development server:

```bash
npm run dev
```

The application will be available at `http://localhost:5173` (or another port if 5173 is in use).

### Environment Variables

- `VITE_API_BASE` - Backend API base URL (set automatically by the startup script)

### Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Features

- Video upload and preview
- Automatic transcription using Whisper AI
- Multiple caption styles (bottom-centered, top-bar, karaoke)
- Real-time caption editing
- Video rendering with captions

## API Integration

The frontend communicates with the backend API for:
- Video transcription (`/transcribe`)
- Video rendering with captions (`/render`)
