// Tutte le chiamate al backend passano da qui.
//
// Indirizzo del backend, in ordine:
//   1. VITE_API_URL, se qualcuno l'ha impostata (serve per puntare a un backend
//      diverso senza ritoccare il codice);
//   2. in sviluppo, stringa vuota: ci pensa il proxy di Vite su /api;
//   3. altrimenti il backend vero su Render.
//
// Il terzo caso c'e' apposta: senza di lui, se la variabile su Vercel manca o si
// perde, il sito cerca il backend su se stesso, non lo trova e mostra soltanto
// "Il backend non risponde" - un guasto che sembra grave e invece e' una casella
// vuota in un pannello.
const PREDEFINITO = "https://gare360.onrender.com";
const BASE = (import.meta.env.VITE_API_URL || (import.meta.env.DEV ? "" : PREDEFINITO))
  .replace(/\/$/, "");

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
  provaChiave: () => call("/api/chiave/prova", { method: "POST" }),

  // --- Salvataggio: il server gratuito riparte vuoto, la copia sta altrove ---
  statoSalvataggio: () => call("/api/salvataggio/stato"),
  salvataggioLeggero: () => call("/api/salvataggio/leggero"),
  ripristinaLeggero: (dati, soloSeVuoto = true) =>
    call(`/api/salvataggio/leggero?solo_se_vuoto=${soloSeVuoto}`, { method: "POST", body: json(dati) }),
  ripristinaCompleto: (file) => { const f = new FormData(); f.append("file", file); return upload("/api/salvataggio/completo", f); },
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

  // --- Ponte manuale: l'app prepara il testo, l'utente lo incolla su claude.ai
  //     e riporta indietro la risposta. Serve senza chiave API a pagamento.
  testoScheda: (file) => { const f = new FormData(); f.append("file", file); return upload("/api/scheda/testo", f); },
  incollaScheda: (testo) => call("/api/scheda/incolla", { method: "POST", body: json({ testo }) }),
  controllaCriteri: (criteri) => call("/api/criteri/controlla", { method: "POST", body: json(criteri) }),

  // --- Archivio CCNL ---
  ccnl: (contratto) => call("/api/ccnl" + qs(contratto ? { contratto } : {})),
  caricaCCNL: (contratto, file, meta) => {
    const f = new FormData(); f.append("file", file);
    Object.entries(meta || {}).forEach(([k, v]) => f.append(k, v ?? ""));
    return upload(`/api/ccnl/${encodeURIComponent(contratto)}/documenti`, f);
  },
  aggiornaCCNL: (id, campi) => call(`/api/ccnl/documenti/${id}`, { method: "PATCH", body: json(campi) }),
  eliminaCCNL: (id) => call(`/api/ccnl/documenti/${id}`, { method: "DELETE" }),
  chiediCCNL: (corpo) => call("/api/ccnl/chiedi", { method: "POST", body: json(corpo) }),
  testoCCNL: (corpo) => call("/api/ccnl/testo", { method: "POST", body: json(corpo) }),
  incollaCCNL: (corpo) => call("/api/ccnl/incolla", { method: "POST", body: json(corpo) }),

  // --- Archiviazione di una gara ---
  precompilaArchivio: (gid) => call(`/api/gare/${gid}/precompila-archivio`),
  archiviaGara: (gid, corpo) => call(`/api/gare/${gid}/archivia`, { method: "POST", body: json(corpo) }),

  // --- Simulatore e storico ---
  stimeStoriche: (p = {}) => call("/api/storico/stime" + qs(p)),
  profiliConcorrenti: (p = {}) => call("/api/storico/concorrenti" + qs(p)),
  simulaScenari: (corpo) => call("/api/simula/scenari", { method: "POST", body: json(corpo) }),
  analizzaGara: (gid, corpo) => call(`/api/gare/${gid}/analisi`, { method: "POST", body: json(corpo) }),
  testoAnalisi: (gid, corpo) => call(`/api/gare/${gid}/analisi/testo`, { method: "POST", body: json(corpo) }),
  incollaAnalisi: (gid, testo, nota) => call(`/api/gare/${gid}/analisi/incolla`, { method: "POST", body: json({ testo, nota }) }),
  elencoAnalisi: (gid) => call(`/api/gare/${gid}/analisi`),
  leggiAnalisi: (gid, id) => call(`/api/gare/${gid}/analisi/${id}`),
  eliminaAnalisi: (gid, id) => call(`/api/gare/${gid}/analisi/${id}`, { method: "DELETE" }),

  // --- Calendario ---
  calendario: (p = {}) => call("/api/calendario" + qs(p)),
  aggiungiVoceCalendario: (v) => call("/api/calendario", { method: "POST", body: json(v) }),
  aggiornaVoceCalendario: (id, campi) => call(`/api/calendario/${id}`, { method: "PATCH", body: json(campi) }),
  eliminaVoceCalendario: (id) => call(`/api/calendario/${id}`, { method: "DELETE" }),
  rimuoviScadenzeGara: (gid) => call(`/api/gare/${gid}/scadenze`, { method: "DELETE" }),
  rigeneraScadenzeGara: (gid) => call(`/api/gare/${gid}/scadenze/rigenera`, { method: "POST" }),

  scadenze: (p = {}) => call("/api/scadenze" + qs(p)),
  estraiScadenza: (file) => { const f = new FormData(); f.append("file", file); return upload("/api/scadenze/estrai", f); },
  confermaScadenza: (g) => call("/api/scadenze/conferma", { method: "POST", body: json(g) }),
});
