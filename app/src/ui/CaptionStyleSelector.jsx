import React from 'react';

export const CAPTION_STYLES = {
  'bottom-centered': 'Bottom Centered',
  'top-bar': 'Top Bar',
  'karaoke': 'Karaoke Style',
};

export function CaptionStyleSelector({ value, onChange }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <label style={{ fontSize: 12, color: 'var(--muted)' }}>Caption style</label>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {Object.entries(CAPTION_STYLES).map(([k, label]) => (
          <option key={k} value={k}>
            {label}
          </option>
        ))}
      </select>
    </div>
  );
}


