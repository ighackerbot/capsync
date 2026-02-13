import React from 'react';

export const CAPTION_STYLES = {
  'bottom-centered': {
    label: 'Bottom Centered',
    description: 'Classic centered captions at the bottom',
    icon: '⬇️'
  },
  'top-bar': {
    label: 'Top Bar',
    description: 'Full-width bar at the top',
    icon: '⬆️'
  },
  'karaoke': {
    label: 'Karaoke Style',
    description: 'Word-by-word highlighting',
    icon: '🎤'
  },
};

export function CaptionStyleSelector({ value, onChange }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <label className="text-sm font-bold" style={{ color: 'var(--fg)' }}>
        Caption Style
      </label>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 8 }}>
        {Object.entries(CAPTION_STYLES).map(([key, { label, description, icon }]) => (
          <button
            key={key}
            className={`btn ${value === key ? 'btn-primary' : ''}`}
            onClick={() => onChange(key)}
            style={{
              textAlign: 'left',
              padding: '12px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              transition: 'all var(--transition-base)',
            }}
          >
            <span style={{ fontSize: '1.5rem' }}>{icon}</span>
            <div style={{ flex: 1 }}>
              <div className="font-bold" style={{ marginBottom: '2px' }}>
                {label}
              </div>
              <div className="text-xs" style={{ opacity: value === key ? 0.9 : 0.6 }}>
                {description}
              </div>
            </div>
            {value === key && (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
