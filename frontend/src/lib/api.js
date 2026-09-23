// Tutte le chiamate al backend passano da qui.
// VITE_API_URL: URL del backend (Render). Vuoto in sviluppo => proxy di Vite su /api.
const BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

// Serve ai link di scaricamento diretto, che non passano da fetch.
export const BASE_API = BASE;

// --- Password condivisa ----------------------------------------------------
// Resta nella scheda del browser (sessionStorage): chiudendo la scheda va via,
// e non viene mai scritta su disco. Viaggia a ogni richiesta nell'intestazione
// X-App-Password.
const CHIAVE = "gare360_password";

export const auth = {
  leggi: () => { try { return sessionStorage.getItem(CHIAVE) || ""; } catch { return ""; } },
  salva: (pw) => { try { sessionStorage.setItem(CHIAVE, pw); } catch {} },
  cancella: () => { try { sessionStorage.removeItem(CHIAVE); } catch {} },
};

// Quando il backend risponde "password sbagliata", l'app deve tornare alla
// schermata di accesso: lo segnaliamo con un evento, così api.js resta
// indipendente da React.
function segnalaAccessoNegato() {
  auth.cancella();
  window.dispatchEvent(new CustomEvent("gare360:accesso-negato"));
}

function intestazioni(extra = {}) {
  const pw = auth.leggi();
  return { ...(pw ? { "X-App-Password": pw } : {}), ...extra };
}

async function leggiErrore(res) {
  let msg = `${res.status} ${res.statusText}`;
  try {
    const j = await res.json();
    msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j);
  } catch {}
  return msg;
}

async function call(path, options = {}) {
  const res = await fetch(BASE + path, {
    ...options,
    headers: intestazioni({ "Content-Type": "application/json", ...(options.headers || {}) }),
  });
  if (!res.ok) {
    const msg = await leggiErrore(res);
    if (res.status === 401) segnalaAccessoNegato();
    throw new Error(msg);
  }
  return res.json();
}

// Verifica una password chiedendo una rotta protetta qualsiasi.
export async function verificaPassword(pw) {
  const res = await fetch(BASE + "/api/gare/costanti", { headers: { "X-App-Password": pw } });
  if (res.status === 401) return { ok: false, messaggio: "Password non corretta." };
  if (!res.ok) return { ok: false, messaggio: await leggiErrore(res) };
  return { ok: true };
}

const json = (body) => JSON.stringify(body);

export const api = {
  health: () => call("/api/health"),
  simula: (payload) => call("/api/simula", { method: "POST", body: json(payload) }),

  archivio: () => call("/api/archivio"),
  salvaArchivioRaw: (testo) => call("/api/archivio/raw", { method: "PUT", body: json({ testo }) }),
  aggiungiScheda: (scheda) => call("/api/archivio/schede", { method: "POST", body: json(scheda) }),

  // --- Archivi storici (Sociale, Cultura, Servizi educativi) ---
  archivi: () => call("/api/archivi"),
  archivioRighe: (nome, filtri = {}) => call(`/api/archivi/${encodeURIComponent(nome)}` + qs(filtri)),
  archivioFiltri: (nome) => call(`/api/archivi/${encodeURIComponent(nome)}/filtri`),
  archivioAggiungi: (nome, riga) => call(`/api/archivi/${encodeURIComponent(nome)}`, { method: "POST", body: json(riga) }),
  archivioAggiorna: (nome, id, campi) => call(`/api/archivi/${encodeURIComponent(nome)}/${encodeURIComponent(id)}`, { method: "PATCH", body: json(campi) }),
  archivioElimina: (nome, id) => call(`/api/archivi/${encodeURIComponent(nome)}/${encodeURIComponent(id)}`, { method: "DELETE" }),
  importaArchivi: (file) => { const f = new FormData(); f.append("file", file); return upload("/api/archivi-importa", f); },

  prompt: () => call("/api/prompt"),
  salvaPrompt: (testo) => call("/api/prompt", { method: "PUT", body: json({ testo }) }),
  chat: (payload) => call("/api/chat", { method: "POST", body: json(payload) }),
};

// --- Gare in lavorazione, documenti, scadenze ------------------------------
async function upload(path, formData) {
  // Nessun Content-Type: lo imposta il browser con il confine del multipart.
  const res = await fetch(BASE + path, { method: "POST", body: formData, headers: intestazioni() });
  if (!res.ok) {
    const msg = await leggiErrore(res);
    if (res.status === 401) segnalaAccessoNegato();
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
  // --- Scheda di rilevazione ---
  schedaCampi: () => call("/api/scheda/campi"),
  estraiScheda: (file) => { const f = new FormData(); f.append("file", file); return upload("/api/scheda/estrai", f); },
  controllaCriteri: (criteri) => call("/api/criteri/controlla", { method: "POST", body: json(criteri) }),

  scadenze: (p = {}) => call("/api/scadenze" + qs(p)),
  estraiScadenza: (file) => { const f = new FormData(); f.append("file", file); return upload("/api/scadenze/estrai", f); },
  confermaScadenza: (g) => call("/api/scadenze/conferma", { method: "POST", body: json(g) }),
});
