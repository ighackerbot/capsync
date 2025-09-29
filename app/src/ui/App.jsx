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
      <div
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 10,
          background: 'var(--bg)',
          borderBottom: '1px solid var(--panel-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '12px 16px'
        }}
      >
        <h1
          style={{
            margin: 0,
            fontSize: 22,
            fontWeight: 800,
            letterSpacing: 0.5,
            textTransform: 'uppercase',
            color: 'var(--fg)'
          }}
        >
          capsync
        </h1>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: 16, padding: 16, flex: 1, minHeight: 0 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <h2 style={{ margin: 0 }}>Remotion Captioner</h2>
          <button onClick={toggleTheme} aria-label="Toggle theme">
            Theme: {theme === 'light' ? 'Light' : 'Dark'}
          </button>
          <input accept="video/mp4" type="file" ref={fileRef} onChange={onFileChange} />
          <button onClick={onGenerate} disabled={!fileRef.current?.files?.[0] || isTranscribing}>
            {isTranscribing ? 'Transcribing…' : 'Generate Captions'}
          </button>
          <CaptionStyleSelector value={styleKey} onChange={setStyleKey} />
          <button onClick={onRender} disabled={!videoUrl || segments.length === 0}>Render MP4</button>
          <div style={{ color: 'var(--muted)', fontSize: 12 }}>
            Hinglish supported. Fonts: Noto Sans + Noto Sans Devanagari.
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div
            style={{
              width: '100%',
              maxWidth: 960,
              aspectRatio: '16 / 9',
              background: 'var(--panel-bg)',
              border: '1px solid var(--panel-border)',
              borderRadius: 12,
              overflow: 'hidden',
              boxShadow: '0 8px 24px rgba(0,0,0,0.25)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
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


