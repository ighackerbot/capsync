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
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('theme');
    if (saved === 'light' || saved === 'dark') return saved;
    return 'dark';
  });
  const [durationInSeconds, setDurationInSeconds] = useState(0);
  const fileRef = useRef(null);

  const onFileChange = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const url = URL.createObjectURL(f);
    setVideoUrl(url);

    // Read accurate duration from metadata
    try {
      const probe = document.createElement('video');
      probe.preload = 'metadata';
      probe.addEventListener('loadedmetadata', () => {
        const dur = Number.isFinite(probe.duration) ? probe.duration : 0;
        setDurationInSeconds(dur || 0);
      });
      // Use a separate URL to avoid revoking or interfering with the preview
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
    } catch (e) {
      console.error(e);
      alert('Failed to generate captions');
    } finally {
      setIsTranscribing(false);
    }
  };

  const onRender = async () => {
    if (!fileRef.current?.files?.[0]) return;
    try {
      const blob = await renderVideo(fileRef.current.files[0], segments, styleKey);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'captioned.mp4';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
      alert('Render failed');
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="navbar">
        <div className="brand" aria-label="Capsync">
          <span className="brand-mark" />
          <span>capsync</span>
        </div>
        <button className="btn btn-ghost" onClick={toggleTheme} aria-label="Toggle theme">
          Theme: {theme === 'light' ? 'Light' : 'Dark'}
        </button>
      </div>
      <div className="content-grid" style={{ flex: 1 }}>
        <div className="card controls-card">
          <h2 style={{ margin: 0 }}>CaptionFlow</h2>

          <div
            className={`upload-dropzone ${isDragging ? 'dragging' : ''}`}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            role="button"
            tabIndex={0}
            onClick={() => fileRef.current?.click()}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileRef.current?.click(); }}
            aria-label="Upload video via click or drag and drop"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M12 16V8m0 0l-3 3m3-3l3 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M20 16a4 4 0 00-3.8-4 5 5 0 00-9.4 0A4 4 0 004 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span>Drag and drop your MP4 here or <strong>browse</strong></span>
            <input className="hidden-input" accept="video/mp4" type="file" ref={fileRef} onChange={onFileChange} />
          </div>

          <button className="btn" onClick={onGenerate} disabled={!fileRef.current?.files?.[0] || isTranscribing}>
            {isTranscribing ? (
              <span className="status"><span className="spinner" /> Transcribing…</span>
            ) : (
              'Generate Captions'
            )}
          </button>

          <CaptionStyleSelector value={styleKey} onChange={setStyleKey} />

          <button className="btn btn-primary" onClick={onRender} disabled={!videoUrl || segments.length === 0}>Download MP4</button>

          <div style={{ color: 'var(--muted)', fontSize: 12 }}>
            Hinglish supported. Fonts: Noto Sans + Noto Sans Devanagari.
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="card video-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {videoUrl ? (
              <Player
                component={CaptionComposition}
                compositionWidth={1280}
                compositionHeight={720}
                durationInFrames={Math.max(1, Math.floor(durationInSeconds * 30))}
                fps={30}
                inputProps={{ videoUrl, segments, styleKey }}
                controls
                style={{ width: '100%', height: '100%' }}
              />
            ) : (
              <div style={{ color: 'var(--muted)' }}>Upload an MP4 to preview</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


