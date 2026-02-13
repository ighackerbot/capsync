import React, { useEffect, useRef, useState } from 'react';
import { Player } from '@remotion/player';
import { CaptionComposition } from '../video/CaptionComposition.jsx';
import { CaptionStyleSelector } from './CaptionStyleSelector.jsx';
import { generateCaptions, renderVideo } from './sttClient.js';

export default function App() {
  const [videoUrl, setVideoUrl] = useState(null);
  const [segments, setSegments] = useState([]);
  const [styleKey, setStyleKey] = useState('bottom-centered');
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isRendering, setIsRendering] = useState(false);
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('theme');
    if (saved === 'light' || saved === 'dark') return saved;
    return 'dark';
  });
  const [durationInSeconds, setDurationInSeconds] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  const fileRef = useRef(null);

  const onFileChange = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const url = URL.createObjectURL(f);
    setVideoUrl(url);
    setCurrentStep(1);

    // Read accurate duration from metadata
    try {
      const probe = document.createElement('video');
      probe.preload = 'metadata';
      probe.addEventListener('loadedmetadata', () => {
        const dur = Number.isFinite(probe.duration) ? probe.duration : 0;
        setDurationInSeconds(dur || 0);
      });
      probe.src = URL.createObjectURL(f);
    } catch (err) {
      console.error('Failed to read video metadata', err);
      setDurationInSeconds(0);
    }
  };

  const [isDragging, setIsDragging] = useState(false);
  const onDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (!f) return;
    if (!fileRef.current) return;
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(f);
    fileRef.current.files = dataTransfer.files;
    const evt = new Event('change', { bubbles: true });
    fileRef.current.dispatchEvent(evt);
  };

  const onDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const onDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const onGenerate = async () => {
    if (!fileRef.current?.files?.[0]) return;
    setIsTranscribing(true);
    try {
      const { segments } = await generateCaptions(fileRef.current.files[0]);
      setSegments(segments);
      setCurrentStep(2);
    } catch (e) {
      console.error(e);
      alert('Failed to generate captions. Please try again.');
    } finally {
      setIsTranscribing(false);
    }
  };

  const onRender = async () => {
    if (!fileRef.current?.files?.[0]) return;
    setIsRendering(true);
    try {
      const blob = await renderVideo(fileRef.current.files[0], segments, styleKey);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'captioned-video.mp4';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setCurrentStep(3);
    } catch (e) {
      console.error(e);
      alert('Render failed. Please try again.');
    } finally {
      setIsRendering(false);
    }
  };

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'light') {
      root.setAttribute('data-theme', 'light');
    } else {
      root.removeAttribute('data-theme');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((t) => (t === 'light' ? 'dark' : 'light'));
  };

  const steps = ['Upload', 'Generate', 'Customize', 'Download'];

  return (
    <div className="app-container">
      {/* Navbar */}
      <nav className="navbar">
        <div className="brand">
          <div className="brand-mark" />
          <span className="gradient-text">CAPSYNC</span>
        </div>
        <button className="btn btn-ghost" onClick={toggleTheme} aria-label="Toggle theme">
          {theme === 'light' ? (
            <>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
              Dark
            </>
          ) : (
            <>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="5" />
                <line x1="12" y1="1" x2="12" y2="3" />
                <line x1="12" y1="21" x2="12" y2="23" />
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                <line x1="1" y1="12" x2="3" y2="12" />
                <line x1="21" y1="12" x2="23" y2="12" />
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
              </svg>
              Light
            </>
          )}
        </button>
      </nav>

      {/* Main Content */}
      <div className="content-grid">
        {/* Left Panel - Controls */}
        <div className="card controls-card fade-in">
          <div>
            <h2 style={{ marginBottom: '8px' }}>
              <span className="gradient-text">Create Captions</span>
            </h2>
            <p className="text-muted text-sm">
              AI-powered video captioning with Whisper
            </p>
          </div>

          {/* Progress Steps */}
          <div className="progress-steps">
            {steps.map((step, idx) => (
              <div
                key={idx}
                className={`progress-step ${idx < currentStep ? 'completed' : ''} ${idx === currentStep ? 'active' : ''}`}
              >
                {step}
              </div>
            ))}
          </div>

          {/* Upload Dropzone */}
          <div
            className={`upload-dropzone ${isDragging ? 'dragging' : ''}`}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            role="button"
            tabIndex={0}
            onClick={() => fileRef.current?.click()}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') fileRef.current?.click();
            }}
            aria-label="Upload video via click or drag and drop"
          >
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <div>
              <p>Drag and drop your video here</p>
              <p className="text-sm">
                or <strong>browse files</strong>
              </p>
              <p className="text-xs text-subtle" style={{ marginTop: '8px' }}>
                Supports MP4, WebM, MOV
              </p>
            </div>
            <input
              className="hidden-input"
              accept="video/mp4,video/webm,video/quicktime"
              type="file"
              ref={fileRef}
              onChange={onFileChange}
            />
          </div>

          {videoUrl && (
            <div className="text-sm" style={{ padding: '8px 12px', background: 'var(--glass-bg)', borderRadius: 'var(--radius-sm)', border: 'var(--border-glass)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
                <span className="text-muted">
                  Duration: {durationInSeconds > 0 ? `${durationInSeconds.toFixed(1)}s` : 'Loading...'}
                </span>
              </div>
            </div>
          )}

          {/* Generate Button */}
          <button
            className="btn btn-primary"
            onClick={onGenerate}
            disabled={!fileRef.current?.files?.[0] || isTranscribing}
            style={{ fontSize: '1rem', padding: '14px 24px' }}
          >
            {isTranscribing ? (
              <span className="status">
                <span className="spinner" />
                Transcribing with AI...
              </span>
            ) : (
              <>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 19V6M5 12l7-7 7 7" />
                </svg>
                Generate Captions
              </>
            )}
          </button>

          {/* Caption Style Selector */}
          {segments.length > 0 && (
            <div className="fade-in">
              <CaptionStyleSelector value={styleKey} onChange={setStyleKey} />
            </div>
          )}

          {/* Render Button */}
          <button
            className="btn btn-primary mt-auto"
            onClick={onRender}
            disabled={!videoUrl || segments.length === 0 || isRendering}
            style={{ fontSize: '1rem', padding: '14px 24px' }}
          >
            {isRendering ? (
              <span className="status">
                <span className="spinner" />
                Rendering Video...
              </span>
            ) : (
              <>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                Download Captioned Video
              </>
            )}
          </button>

          {/* Info Footer */}
          <div className="text-xs text-subtle" style={{ padding: '12px', background: 'var(--glass-bg)', borderRadius: 'var(--radius-sm)', border: 'var(--border-glass)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
              <span className="font-bold">Powered by Whisper AI</span>
            </div>
            <p>Supports English, Hindi, and Hinglish with high accuracy.</p>
          </div>
        </div>

        {/* Right Panel - Video Preview */}
        <div className="video-card card fade-in">
          {videoUrl ? (
            <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Player
                  component={CaptionComposition}
                  compositionWidth={1280}
                  compositionHeight={720}
                  durationInFrames={Math.max(1, Math.floor(durationInSeconds * 30))}
                  fps={30}
                  inputProps={{ videoUrl, segments, styleKey }}
                  controls
                  style={{ width: '100%', borderRadius: 'var(--radius-md)', overflow: 'hidden', boxShadow: 'var(--shadow-lg)' }}
                />
              </div>
              {segments.length > 0 && (
                <div style={{ padding: '12px', background: 'var(--glass-bg)', borderRadius: 'var(--radius-sm)', border: 'var(--border-glass)' }}>
                  <div className="text-sm text-muted" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                    </svg>
                    <span>
                      <span className="font-bold">{segments.length}</span> caption segments generated
                    </span>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div style={{ textAlign: 'center', color: 'var(--fg-muted)' }}>
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ margin: '0 auto 16px', opacity: 0.5 }}>
                <polygon points="23 7 16 12 23 17 23 7" />
                <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
              </svg>
              <h3 style={{ marginBottom: '8px' }}>
                No Video Yet
              </h3>
              <p className="text-sm">
                Upload a video to get started with AI captioning
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
