// Tutte le chiamate al backend passano da qui.
// VITE_API_URL: URL del backend (Render). Vuoto in sviluppo => proxy di Vite su /api.
const BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

async function call(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j);
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

const json = (body) => JSON.stringify(body);

export const api = {
  health: () => call("/api/health"),
  simula: (payload) => call("/api/simula", { method: "POST", body: json(payload) }),

  tracker: () => call("/api/tracker"),
  salvaTracker: (righe) => call("/api/tracker", { method: "PUT", body: json(righe) }),
  trackerRaw: () => call("/api/tracker/raw"),
  salvaTrackerRaw: (testo) => call("/api/tracker/raw", { method: "PUT", body: json({ testo }) }),

  archivio: () => call("/api/archivio"),
  salvaArchivioRaw: (testo) => call("/api/archivio/raw", { method: "PUT", body: json({ testo }) }),
  aggiungiScheda: (scheda) => call("/api/archivio/schede", { method: "POST", body: json(scheda) }),

  prompt: () => call("/api/prompt"),
  salvaPrompt: (testo) => call("/api/prompt", { method: "PUT", body: json({ testo }) }),
  chat: (payload) => call("/api/chat", { method: "POST", body: json(payload) }),
};
