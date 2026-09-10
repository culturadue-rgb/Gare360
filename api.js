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

// --- Gare in lavorazione, documenti, scadenze ------------------------------
async function upload(path, formData) {
  const res = await fetch(BASE + path, { method: "POST", body: formData });
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try { const j = await res.json(); msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j); } catch {}
    throw new Error(msg);
  }
  return res.json();
}

const qs = (o) => {
  const p = Object.entries(o).filter(([, v]) => v !== undefined && v !== null && v !== "").map(([k, v]) => `${k}=${encodeURIComponent(v)}`);
  return p.length ? "?" + p.join("&") : "";
};

Object.assign(api, {
  costanti: () => call("/api/gare/costanti"),
  gare: (filtri = {}) => call("/api/gare" + qs(filtri)),
  creaGara: (g) => call("/api/gare", { method: "POST", body: json(g) }),
  gara: (id) => call(`/api/gare/${id}`),
  aggiornaGara: (id, campi) => call(`/api/gare/${id}`, { method: "PATCH", body: json(campi) }),
  eliminaGara: (id) => call(`/api/gare/${id}`, { method: "DELETE" }),
  riattivaMemoria: (id) => call(`/api/gare/${id}/memoria/riattiva`, { method: "POST" }),
  caricaDocumento: (id, file, categoria) => { const f = new FormData(); f.append("file", file); f.append("categoria", categoria); return upload(`/api/gare/${id}/documenti`, f); },
  rimuoviDocumento: (id, docId) => call(`/api/gare/${id}/documenti/${docId}`, { method: "DELETE" }),
  testoDocumento: (id, docId) => call(`/api/gare/${id}/documenti/${docId}/testo`),
  documenti: () => call("/api/documenti"),
  chatGara: (id, messaggio, modello) => call(`/api/gare/${id}/chat`, { method: "POST", body: json({ messaggio, modello: modello || null }) }),
  valutaGara: (id, modello) => call(`/api/gare/${id}/valuta`, { method: "POST", body: json({ modello: modello || null }) }),
  estraiInfo: (id, modello) => call(`/api/gare/${id}/estrai-info`, { method: "POST", body: json({ modello: modello || null }) }),
  estraiSimulatore: (id, modello) => call(`/api/gare/${id}/estrai-simulatore`, { method: "POST", body: json({ modello: modello || null }) }),
  scadenze: (p = {}) => call("/api/scadenze" + qs(p)),
  estraiScadenza: (file) => { const f = new FormData(); f.append("file", file); return upload("/api/scadenze/estrai", f); },
  confermaScadenza: (g) => call("/api/scadenze/conferma", { method: "POST", body: json(g) }),
});
