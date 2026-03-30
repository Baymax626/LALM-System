export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080';

export async function pingBackend(signal) {
  const res = await fetch(`${API_BASE}/api/ping`, { method: 'GET', signal });
  return res.ok;
}

export async function postJson(path, body, signal) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal
  });
  const data = await res.json().catch(() => null);
  return { ok: res.ok, data };
}
