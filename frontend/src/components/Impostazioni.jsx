import { useCallback, useEffect, useRef, useState } from "react";
import { api, BASE_API } from "../lib/api.js";
import * as memoria from "../lib/memoria.js";

export default function Impostazioni({ salute, modello, setModello, costanti }) {
  const [prompt, setPrompt] = useState("");
  const [msg, setMsg] = useState(null);
  const [errore, setErrore] = useState(null);
  const [statoArchivi, setStatoArchivi] = useState(null);
  const [copiaBrowser, setCopiaBrowser] = useState(() => memoria.leggi());
  const [ripristinando, setRipristinando] = useState(false);
  const [esitoRipristino, setEsitoRipristino] = useState(null);
  const [provando, setProvando] = useState(false);
  const [esitoChiave, setEsitoChiave] = useState(null);
  const [caricando, setCaricando] = useState(false);
  const fileRef = useRef(null);
  const ripristinoRef = useRef(null);

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

  async function ripristinaDaFile(file) {
    if (!file) return;
    setRipristinando(true); setEsitoRipristino(null);
    try {
      const r = await api.ripristinaCompleto(file);
      setEsitoRipristino({ ok: true, messaggio: `Ripristinati ${r.file_ripristinati} file. Ricarica la pagina per vederli.` });
    } catch (e) {
      setEsitoRipristino({ ok: false, messaggio: e.message });
    } finally {
      setRipristinando(false);
    }
  }

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


      {/* ---------------- Salvataggio ----------------
          Il piano gratuito di Render non dà un disco al server: si spegne dopo
          un quarto d'ora e riparte pulito. Finché è così, la memoria dell'app
          deve stare altrove, e va detto senza girarci intorno. */}
      <h3>Salvataggio dei dati</h3>
      <p className="nota">
        Il server gratuito <b>non ha un disco</b>: si spegne dopo un quarto d'ora di
        inattività e riparte vuoto. Per questo l'app tiene due copie.
      </p>

      <p className="nota">
        <b>1. Copia automatica nel browser.</b>{" "}
        {copiaBrowser
          ? <>Aggiornata il <b>{(copiaBrowser.quando || "").replace("T", " alle ").slice(0, 19)}</b>{" "}
              ({Object.keys(copiaBrowser.file || {}).length} file). Quando il server riparte
              vuoto, viene rimessa da sola.</>
          : <>Non ce n'è ancora una: comparirà dopo la prima modifica.</>}
        {" "}Vale solo su questo computer e questo browser, e sparisce se cancelli i dati di
        navigazione. Non contiene i PDF originali.
      </p>

      <p className="nota">
        <b>2. Copia completa scaricabile.</b> Contiene <i>tutto</i>, PDF compresi, e non
        dipende da niente. È quella da tenere da parte.
      </p>
      <div className="azioni">
        <a className="btn primario" href={`${BASE_API}/api/salvataggio/completo`} download>
          Salva tutto (scarica il file)
        </a>
        <input ref={ripristinoRef} type="file" accept=".zip" style={{ display: "none" }}
               onChange={(e) => { ripristinaDaFile(e.target.files?.[0]); e.target.value = ""; }} />
        <button className="btn" disabled={ripristinando} onClick={() => ripristinoRef.current?.click()}>
          {ripristinando ? "Ripristino…" : "Ripristina da un file"}
        </button>
      </div>
      {esitoRipristino && (
        <p className={esitoRipristino.ok ? "avviso" : "avviso errore"}>{esitoRipristino.messaggio}</p>
      )}

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
