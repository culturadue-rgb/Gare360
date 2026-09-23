import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api.js";

/**
 * Archivio dei contratti collettivi e consultazione su fonti certe.
 *
 * Si trascinano i PDF nel contratto giusto e si registrano tipo, data di
 * sottoscrizione e validità. La chat risponde SOLO con il contenuto dei
 * documenti caricati, cita documento e pagina, e mostra sotto la risposta i
 * passaggi originali, perché una risposta su un CCNL vale solo se si può
 * verificare.
 */

export default function CCNL() {
  const [dati, setDati] = useState({ contratti: [], tipi_documento: [], documenti: [] });
  const [contratto, setContratto] = useState("");
  const [meta, setMeta] = useState({ tipo_documento: "testo contrattuale", data_sottoscrizione: "", validita_da: "", validita_a: "" });
  const [domanda, setDomanda] = useState("");
  const [risposta, setRisposta] = useState(null);
  const [daCancellare, setDaCancellare] = useState(null);
  const [errore, setErrore] = useState(null);
  const [inCorso, setInCorso] = useState(null);
  const fileRef = useRef(null);

  const carica = useCallback(() => {
    api.ccnl().then((d) => { setDati(d); if (!contratto && d.contratti.length) setContratto(d.contratti[0]); })
      .catch((e) => setErrore(e.message));
  }, [contratto]);
  useEffect(() => { carica(); }, [carica]);

  async function caricaFile(file) {
    if (!file) return;
    setInCorso("carico"); setErrore(null);
    try {
      const v = await api.caricaCCNL(contratto, file, meta);
      if (v.avviso) setErrore(v.avviso);
      carica();
    } catch (e) { setErrore(e.message); }
    finally { setInCorso(null); if (fileRef.current) fileRef.current.value = ""; }
  }

  async function chiedi() {
    if (!domanda.trim()) return;
    setInCorso("chiedo"); setErrore(null); setRisposta(null);
    try { setRisposta(await api.chiediCCNL({ domanda, contratto })); }
    catch (e) { setErrore(e.message); }
    finally { setInCorso(null); }
  }

  async function elimina(id) {
    try { await api.eliminaCCNL(id); setDaCancellare(null); carica(); }
    catch (e) { setErrore(e.message); setDaCancellare(null); }
  }

  const documenti = dati.documenti.filter((d) => d.ccnl === contratto);

  return (
    <div className="riquadro">
      <h2>Archivio CCNL</h2>

      <div className="filtri">
        {dati.contratti.map((c) => (
          <button key={c} aria-pressed={contratto === c} onClick={() => { setContratto(c); setRisposta(null); }}>
            {c} <small>({dati.documenti.filter((d) => d.ccnl === c).length})</small>
          </button>
        ))}
      </div>

      {/* ---------- caricamento ---------- */}
      <h3>Aggiungi un documento a «{contratto}»</h3>
      <div className="riga">
        <label className="campo"><span>Tipo</span>
          <select value={meta.tipo_documento} onChange={(e) => setMeta({ ...meta, tipo_documento: e.target.value })}>
            {dati.tipi_documento.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
        <label className="campo"><span>Sottoscritto il</span>
          <input type="date" value={meta.data_sottoscrizione}
                 onChange={(e) => setMeta({ ...meta, data_sottoscrizione: e.target.value })} /></label>
        <label className="campo"><span>Valido da</span>
          <input type="date" value={meta.validita_da} onChange={(e) => setMeta({ ...meta, validita_da: e.target.value })} /></label>
        <label className="campo"><span>Valido fino a</span>
          <input type="date" value={meta.validita_a} onChange={(e) => setMeta({ ...meta, validita_a: e.target.value })} /></label>
      </div>
      <input ref={fileRef} type="file" accept=".pdf" style={{ display: "none" }}
             onChange={(e) => caricaFile(e.target.files?.[0])} />
      <div className="azioni">
        <button className="btn primario" disabled={inCorso === "carico" || !contratto}
                onClick={() => fileRef.current?.click()}>
          {inCorso === "carico" ? "Leggo il PDF…" : "Scegli il PDF"}
        </button>
        <span className="nota">il testo viene estratto pagina per pagina</span>
      </div>

      {errore && <div className="avviso attenzione">{errore}</div>}

      {/* ---------- documenti ---------- */}
      {documenti.length === 0 ? (
        <div className="vuoto">Nessun documento per {contratto}.</div>
      ) : (
        <div className="tabella-scorrevole">
          <table className="tabella-archivio">
            <thead>
              <tr><th>Documento</th><th>Tipo</th><th>Sottoscritto</th><th>Validità</th><th>Pagine</th><th /></tr>
            </thead>
            <tbody>
              {documenti.map((d) => (
                <tr key={d.id_documento}>
                  <td title={d.nome_file}>{d.nome_file}</td>
                  <td>{d.tipo_documento}</td>
                  <td>{d.data_sottoscrizione || <span className="mancante">—</span>}</td>
                  <td>{[d.validita_da, d.validita_a].filter(Boolean).join(" → ") || <span className="mancante">—</span>}</td>
                  <td>{d.pagine_con_testo}/{d.numero_pagine}{d.pagine_con_testo < d.numero_pagine && " ⚠️"}</td>
                  <td><button className="btn piccolo pericolo" onClick={() => setDaCancellare(d)}>×</button></td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="nota">
            I rinnovi più recenti prevalgono; quelli vecchi restano consultabili.
            Nella colonna Pagine, il primo numero è quanto è davvero leggibile.
          </p>
        </div>
      )}

      {/* ---------- consultazione ---------- */}
      <h3>Chiedi ai documenti</h3>
      <p className="nota">
        Si risponde solo con quello che c'è scritto nei documenti caricati, citando
        documento e pagina. Se l'informazione non c'è, la risposta è
        «Non presente nei documenti caricati».
      </p>
      <div className="riga">
        <input type="text" placeholder="es. qual è il minimo retributivo del livello 3?"
               value={domanda} onChange={(e) => setDomanda(e.target.value)}
               onKeyDown={(e) => e.key === "Enter" && chiedi()} />
        <button className="btn primario" disabled={inCorso === "chiedo"} onClick={chiedi}>
          {inCorso === "chiedo" ? "Cerco…" : "Chiedi"}
        </button>
      </div>

      {risposta && (
        <div className="risposta-ccnl">
          <div className="md">{risposta.risposta}</div>

          {risposta.problemi?.length > 0 && (
            <div className="avviso errore">
              <b>Attenzione:</b> alcune citazioni non corrispondono ai passaggi trovati e sono
              state marcate con ⚠️ nel testo. Non fidarti di quelle.
              <ul>{risposta.problemi.map((p, i) => <li key={i}>{p}</li>)}</ul>
            </div>
          )}

          {risposta.passaggi?.length > 0 && (
            <details open>
              <summary>I passaggi originali ({risposta.passaggi.length})</summary>
              {risposta.passaggi.map((p, i) => (
                <div key={i} className="passaggio">
                  <div className="nota">
                    <b>{p.documento}</b> — {p.ccnl}, {p.tipo_documento}
                    {p.data_sottoscrizione && `, sottoscritto il ${p.data_sottoscrizione}`} — <b>pagina {p.pagina}</b>
                  </div>
                  <blockquote>{p.testo}</blockquote>
                </div>
              ))}
            </details>
          )}
        </div>
      )}

      {daCancellare && (
        <div className="modale-sfondo" onClick={() => setDaCancellare(null)}>
          <div className="modale" onClick={(e) => e.stopPropagation()}>
            <h3>Eliminare «{daCancellare.nome_file}»?</h3>
            <p>Il PDF e il suo testo estratto vengono cancellati. La consultazione non lo vedrà più.</p>
            <div className="azioni">
              <button className="btn pericolo" onClick={() => elimina(daCancellare.id_documento)}>Sì, elimina</button>
              <button className="btn" onClick={() => setDaCancellare(null)}>Annulla</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
