import axios from 'axios';

const API_BASE = (import.meta && import.meta.env && import.meta.env.VITE_API_BASE) || 'http://127.0.0.1:8000';

export async function generateCaptions(file) {
  const form = new FormData();
  form.append('file', file);
  const { data } = await axios.post(`${API_BASE}/transcribe`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function renderVideo(file, segments, style) {
  const form = new FormData();
  form.append('file', file);
  form.append('segments_json', JSON.stringify({ segments }));
  form.append('style', style);
  const resp = await axios.post(`${API_BASE}/render`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  });
  return resp.data;
}


