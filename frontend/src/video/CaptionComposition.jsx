import React, { useMemo } from 'react';
import { AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig, Video } from 'remotion';

export const CaptionComposition = ({ videoUrl, segments, styleKey }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();

  const containerStyle = useMemo(() => {
    switch (styleKey) {
      case 'top-bar':
        return {
          position: 'absolute',
          top: 0,
          left: 0,
          width,
          padding: 24,
          background: 'linear-gradient(180deg, rgba(0,0,0,0.8), rgba(0,0,0,0))',
          color: 'white',
          textAlign: 'center',
        };
      case 'karaoke':
        return {
          position: 'absolute',
          bottom: 80,
          left: 0,
          width,
          display: 'flex',
          justifyContent: 'center',
          color: 'white',
          textShadow: '0 2px 10px rgba(0,0,0,0.6)',
        };
      default:
        return {
          position: 'absolute',
          bottom: 48,
          left: 0,
          width,
          display: 'flex',
          justifyContent: 'center',
          color: 'white',
          textShadow: '0 2px 10px rgba(0,0,0,0.6)',
        };
    }
  }, [styleKey, width]);

  const textStyle = useMemo(() => {
    const base = {
      fontFamily: 'Noto Sans Devanagari, Noto Sans, system-ui, sans-serif',
      fontWeight: 700,
      fontSize: 48,
      lineHeight: 1.2,
      padding: '12px 16px',
      borderRadius: 12,
      background: styleKey === 'top-bar' ? 'transparent' : 'rgba(0,0,0,0.5)',
    };
    if (styleKey === 'karaoke') {
      return { ...base, background: 'transparent', borderBottom: '6px solid #7c93ff' };
    }
    return base;
  }, [styleKey]);

  return (
    <AbsoluteFill style={{ backgroundColor: 'black' }}>
      <Video src={videoUrl} />
      {segments.map((s) => (
        <Sequence key={s.id} from={Math.floor(s.start * fps)} durationInFrames={Math.max(1, Math.floor((s.end - s.start) * fps))}>
          <div style={containerStyle}>
            <div style={textStyle}>{s.text}</div>
          </div>
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};


