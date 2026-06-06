import type { MatchResponse, SubmitPayload, SubmitResponse } from './types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`HTTP ${res.status}: ${err}`);
  }
  return res.json();
}

export async function healthCheck(): Promise<{ ok: boolean; llm_backend: string }> {
  return fetchApi('/api/health');
}

export async function matchComplaint(text: string): Promise<MatchResponse> {
  return fetchApi('/api/match', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}

export async function submitRequest(payload: SubmitPayload): Promise<SubmitResponse> {
  return fetchApi('/api/submit', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
