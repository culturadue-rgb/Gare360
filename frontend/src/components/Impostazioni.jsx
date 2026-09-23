import { useCallback, useEffect, useRef, useState } from "react";
import { api, BASE_API } from "../lib/api.js";

export default function Impostazioni({ salute, modello, setModello, costanti }) {
  const [prompt, setPrompt] = useState("");
  const [msg, setMsg] = useState(null);
  const [errore, setErrore] = useState(null);
  const [statoArchivi, setStatoArchivi] = useState(null);
  const [provando, setProvando] = useState(false);
  const [esitoChiave, setEsitoChiave] = useState(null);
  const [caricando, setCaricando] = useState(false);
  const fileRef = useRef(null);

  const leggiStato = useCallback(() => {
    api.archivi().then((r) => setStatoArchivi(r.stato)).catch(() => {});
  }, []);

  useEffect(() => { api.prompt().then((p) => setPrompt(p.testo)).catch(() => {}); }, []);
  useEffect(() => { leggiStato(); }, [leggiStato]);

  async function salva() {
    setMsg(null); setErrore(null);
    try { await api.salvaPrompt(prompt); setMsg("Prompt salvato."); }
    catch (e) { setErrore(e.message); }
  }

  async function caricaArchivio(file) {
    if (!file) return;
    setMsg(null); setErrore(null); setCaricando(true);
    try {
      const r = await api.importaArchivi(file);
      const righe = Object.entries(r.gare_per_archivio)
        .map(([a, n]) => `${a.replace("_", " ")}: ${n}`).join(" · ");
      setMsg(`Archivio caricato — ${righe}`);
      leggiStato();
    } catch (e) {
      setErrore(e.message);
    } finally {
      setCaricando(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  const gare = statoArchivi?.gare;
  const totale = gare
    ? Object.values(gare).reduce((s, n) => s + (typeof n === "number" ? n : 0), 0)
    : 0;

  async function provaChiave() {
    setProvando(true);
    setEsitoChiave(null);
    try {
      setEsitoChiave(await api.provaChiave());
    } catch (e) {
      setEsitoChiave({ ok: false, messaggio: "Non sono riuscito a contattare il backend: " + e.message });
    } finally {
      setProvando(false);
    }
  }

  return (
    <div className="riquadro">
      <h2>Impostazioni</h2>
      <p>
        Backend: {salute ? "attivo" : "non raggiungibile"} · assistente AI:{" "}
        <b>{salute?.chiave_api_configurata ? "pronto" : "senza chiave (imposta ANTHROPIC_API_KEY sul server)"}</b>
        {" "}· memoria delle gare: {costanti?.memoria_giorni || 15} giorni dall'ultima attività.
      </p>

      {/* ---------------- Chiave dell'AI ----------------
          "Configurata" vuol dire solo che la casella non è vuota. Se la chiave è
          sbagliata lo si scopre altrimenti a metà di un'estrazione, con un errore
          incomprensibile: meglio poterla provare quando si vuole. */}
      <h3>Chiave dell'assistente AI</h3>
      {salute?.chiave_api?.nota && (
        <p className="nota">{salute.chiave_api.nota}</p>
      )}
      <p>
        <button className="btn contorno" onClick={provaChiave} disabled={provando}>
          {provando ? "Provo…" : "Prova la chiave"}
        </button>
        {" "}
        <span className="nota">Fa una richiesta minima ad Anthropic: costa pochissimo.</span>
      </p>
      {esitoChiave && (
        <p className={esitoChiave.ok ? "avviso" : "avviso errore"}>{esitoChiave.messaggio}</p>
      )}

      {/* ---------------- Archivio storico ---------------- */}
      <h3>Archivio storico</h3>
      {statoArchivi?.disponibile ? (
        <p className="nota">
          Letto da: <b>{statoArchivi.descrizione}</b> — {totale} gare in totale
          {gare && <> ({Object.entries(gare).map(([a, n]) => `${a.replace("_", " ")} ${n}`).join(", ")})</>}.
        </p>
      ) : (
        <div className="avviso">
          L'archivio non è ancora caricato: le sezioni Sociale, Cultura e Servizi
          educativi risultano vuote. Carica qui il file
          <code> Archivio_Gare360_unificato.xlsx</code>.
        </div>
      )}

      <div className="azioni">
        <input
          ref={fileRef} type="file" accept=".xlsx" style={{ display: "none" }}
          onChange={(e) => caricaArchivio(e.target.files?.[0])}
        />
        <button className="btn primario" disabled={caricando} onClick={() => fileRef.current?.click()}>
          {caricando ? "Carico…" : statoArchivi?.disponibile ? "Sostituisci l'archivio" : "Carica l'archivio Excel"}
        </button>
        <a className="btn" href={`${BASE_API}/api/archivi-esporta`} download>
          Esporta gli archivi in Excel
        </a>
      </div>

      <p className="nota">
        <b>Scarica spesso la copia di sicurezza.</b> Finché i dati non stanno su
        Google Drive, l'archivio vive sul disco del server: sul piano gratuito di
        Render quel disco si svuota a ogni riavvio, e il file esportato è l'unica
        copia che sopravvive con certezza.
      </p>

      {/* ---------------- Google Drive ---------------- */}
      <h3>Google Drive</h3>
      <p className="nota">
        {salute?.drive?.collegato ? (
          <>Collegato. <a href={salute.drive.url} target="_blank" rel="noreferrer">Apri la cartella su Drive</a>.</>
        ) : (
          <>
            Non collegato ({salute?.drive?.motivo || "stato sconosciuto"}). Finché
            resta così l'archivio sta sul disco del server. Per collegarlo servono
            le tre variabili <code>GOOGLE_CLIENT_ID</code>,{" "}
            <code>GOOGLE_CLIENT_SECRET</code> e <code>GOOGLE_REFRESH_TOKEN</code>{" "}
            impostate su Render.
          </>
        )}
      </p>

      {/* ---------------- Assistente ---------------- */}
      <h3>Assistente</h3>
      <label className="campo">
        <span>Modello (vuoto = {salute?.modello_default || "default del server"})</span>
        <input type="text" value={modello} onChange={(e) => setModello(e.target.value)}
               placeholder={salute?.modello_default || ""} />
      </label>

      <h3>Prompt di sistema</h3>
      <p className="nota">
        È la base di ogni risposta; alla gara aperta vengono aggiunti
        automaticamente l'archivio storico e i documenti caricati.
      </p>
      <textarea rows={14} value={prompt} onChange={(e) => setPrompt(e.target.value)} />
      <div className="azioni"><button className="btn primario" onClick={salva}>Salva prompt</button></div>

      {msg && <div className="avviso">{msg}</div>}
      {errore && <div className="avviso errore">{errore}</div>}
    </div>
  );
}
