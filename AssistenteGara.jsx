import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api.js";
import { classeSettore, fmtDataOra, giorniLabel } from "../lib/util.js";
import Modale from "./Modale.jsx";
import NuovaGara from "./NuovaGara.jsx";

// Chat dell'assistente sulla gara selezionata. Senza gara: chat generica (endpoint /api/chat esistente).
export default function AssistenteGara({ garaId, onSelezionaGara, elencoGare, costanti, salute, modello, onGaraAggiornata, onSimula, apriNuova, setApriNuova }) {
  const [g, setG] = useState(null);
  const [chatGenerica, setChatGenerica] = useState([]);
  const [domanda, setDomanda] = useState("");
  const [attesa, setAttesa] = useState(null); // etichetta dell'operazione in corso
  const [errore, setErrore] = useState(null);
  const [categoria, setCategoria] = useState("disciplinare");
  const [over, setOver] = useState(false);
  const [anteprima, setAnteprima] = useState(null);
  const fine = useRef(null);
  const fileRef = useRef(null);

  useEffect(() => {
    setErrore(null);
    if (!garaId) { setG(null); return; }
    api.gara(garaId).then(setG).catch((e) => setErrore(e.message));
  }, [garaId]);
  useEffect(() => { fine.current?.scrollIntoView({ block: "end" }); }, [g?.chat?.length, chatGenerica.length, attesa]);

  const aggiorna = (nuova) => { setG(nuova); onGaraAggiornata?.(nuova); };
  const senzaChiave = salute && !salute.chiave_api_configurata;

  async function invia() {
    const q = domanda.trim();
    if (!q || attesa) return;
    setDomanda(""); setAttesa("Sto ragionando…"); setErrore(null);
    try {
      if (g) {
        const r = await api.chatGara(g.id, q, modello);
        aggiorna(r.gara);
      } else {
        const messaggi = [...chatGenerica, { role: "user", content: q }];
        setChatGenerica(messaggi);
        const r = await api.chat({ messaggi, includi_contesto: true, modello: modello || null });
        setChatGenerica([...messaggi, { role: "assistant", content: r.risposta }]);
      }
    } catch (e) { setErrore(e.message); setDomanda(q); } finally { setAttesa(null); }
  }

  async function azione(nome, fn) {
    setAttesa(nome); setErrore(null);
    try { const r = await fn(); if (r?.gara) aggiorna(r.gara); return r; }
    catch (e) { setErrore(e.message); } finally { setAttesa(null); }
  }

  async function carica(files) {
    if (!g || !files?.length) return;
    setAttesa("Carico e leggo i documenti…"); setErrore(null);
    try {
      let nuova = g;
      for (const f of files) nuova = await api.caricaDocumento(g.id, f, categoria);
      aggiorna(nuova);
    } catch (e) { setErrore(e.message); } finally { setAttesa(null); if (fileRef.current) fileRef.current.value = ""; }
  }

  async function estraiPerSimulatore() {
    const r = await azione("Estraggo criteri e formule per il simulatore…", () => api.estraiSimulatore(g.id, modello));
    if (r?.dati) onSimula?.(r.dati, g);
  }

  const chat = g ? g.chat : chatGenerica;

  return (
    <div className="riquadro">
      {g ? (
        <div className="testa-gara">
          <div>
            <h2>{g.titolo}</h2>
            <div className="meta">
              <span className={`settore ${classeSettore(g.settore)}`}>{g.settore}</span>
              <span>{g.ente || "ente n.d."}</span>
              <span>scade {fmtDataOra(g.scadenza)}{g.scadenza && <> · <b className={`urg ${g.giorni_mancanti != null && g.giorni_mancanti <= 3 ? "alta" : ""}`}>{giorniLabel(g.giorni_mancanti ?? Math.round((new Date(g.scadenza) - new Date()) / 864e5))}</b></>}</span>
              <label>Stato <select value={g.stato} onChange={(e) => azione("Aggiorno lo stato…", () => api.aggiornaGara(g.id, { stato: e.target.value }).then((x) => ({ gara: x })))}>
                {(costanti?.stati || []).map((s) => <option key={s}>{s}</option>)}
              </select></label>
              <label>Settore <select value={g.settore} onChange={(e) => azione("Aggiorno il settore…", () => api.aggiornaGara(g.id, { settore: e.target.value }).then((x) => ({ gara: x })))}>
                {(costanti?.settori || []).map((s) => <option key={s}>{s}</option>)}
              </select></label>
              <button className="link" onClick={() => onSelezionaGara(null)}>Chiudi gara</button>
            </div>
          </div>
        </div>
      ) : (
        <div className="testa-gara">
          <div>
            <h2>Assistente</h2>
            <div className="selezione" style={{ marginTop: ".4rem" }}>
              <select value="" onChange={(e) => e.target.value && onSelezionaGara(e.target.value)}>
                <option value="">Seleziona una gara in lavorazione…</option>
                {elencoGare.map((x) => <option key={x.id} value={x.id}>{x.settore} · {x.titolo}</option>)}
              </select>
              <button className="btn primario piccolo" onClick={() => setApriNuova(true)}>Nuova gara</button>
            </div>
            <p className="nota" style={{ marginTop: ".4rem" }}>Senza una gara selezionata l'assistente risponde usando tracker e archivio storico. Seleziona o crea una gara per lavorare sui suoi documenti.</p>
          </div>
        </div>
      )}

      {senzaChiave && <div className="avviso info">L'assistente AI è spento perché sul server manca <code>ANTHROPIC_API_KEY</code>. Puoi comunque creare gare, caricare documenti e usare simulatore, calendario e archivio.</div>}
      {g && !g.memoria_attiva && (
        <div className="avviso">Memoria archiviata: sono passati più di {costanti?.memoria_giorni || 15} giorni dall'ultima attività, quindi conversazione e analisi precedenti non vengono più passate all'assistente. <button className="link" onClick={() => azione("Riattivo…", () => api.riattivaMemoria(g.id).then((x) => ({ gara: x })))}>Riattiva la memoria</button></div>
      )}

      {g && (
        <details open={g.documenti.length === 0}>
          <summary><span>Documenti della gara</span><span className="nota">{g.documenti.length} caricati · entrano subito nel contesto dell'assistente</span></summary>
          <div>
            <ul className="docs">
              {g.documenti.map((d) => (
                <li key={d.id}>
                  <span className="nome">{d.nome}</span>
                  <span className="cat">{d.categoria}{d.troncato ? " · testo troncato" : ""}{d.caratteri === 0 ? " · nessun testo leggibile" : ""}</span>
                  <button className="link" onClick={async () => setAnteprima({ nome: d.nome, testo: (await api.testoDocumento(g.id, d.id)).testo })}>testo</button>
                  <button className="link" onClick={() => azione("Rimuovo…", () => api.rimuoviDocumento(g.id, d.id).then((x) => ({ gara: x })))}>rimuovi</button>
                </li>
              ))}
            </ul>
            <div className="selezione" style={{ margin: ".6rem 0 .4rem" }}>
              <span className="nota">Categoria del prossimo file:</span>
              <select value={categoria} onChange={(e) => setCategoria(e.target.value)}>{(costanti?.categorie_documento || []).map((c) => <option key={c}>{c}</option>)}</select>
            </div>
            <div className={`dropzone ${over ? "over" : ""}`}
              onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
              onDrop={(e) => { e.preventDefault(); setOver(false); carica([...e.dataTransfer.files]); }}
              onClick={() => fileRef.current?.click()}>
              <input ref={fileRef} type="file" multiple accept=".pdf,.docx,.txt,.md,.csv" onChange={(e) => carica([...e.target.files])} />
              Trascina qui bando, disciplinare, capitolato, allegati, chiarimenti (PDF, Word, testo) o clicca per scegliere
            </div>
          </div>
        </details>
      )}

      {g && (
        <div className="azioni-ai">
          <button className="btn contorno piccolo" disabled={!!attesa || senzaChiave || !g.documenti.length} onClick={() => azione("Valuto la gara…", () => api.valutaGara(g.id, modello))}>Valuta la gara (GO / NO GO)</button>
          <button className="btn contorno piccolo" disabled={!!attesa || senzaChiave || !g.documenti.length} onClick={() => azione("Estraggo requisiti, scadenze, criticità…", () => api.estraiInfo(g.id, modello))}>Estrai requisiti e scadenze</button>
          <button className="btn contorno piccolo" disabled={!!attesa || senzaChiave || !g.documenti.length} onClick={estraiPerSimulatore}>Prepara il simulatore</button>
          {g.dati_simulatore && <button className="btn piccolo" onClick={() => onSimula?.(g.dati_simulatore, g)}>Riapri nel simulatore</button>}
        </div>
      )}

      {g?.info_estratte && (
        <details><summary><span>Informazioni estratte</span><span className="nota">requisiti, criticità, scadenze</span></summary>
          <div className="md">{JSON.stringify(g.info_estratte, null, 2)}</div>
        </details>
      )}

      <div className="chat">
        {chat.length === 0 && <div className="vuoto">{g ? "Carica i documenti e chiedi: «Quali sono i requisiti di partecipazione?», «Ci conviene partecipare?», «Quali sono le scadenze?»" : "Chiedi allo stratega-gare come impostare la prossima offerta."}</div>}
        {chat.map((m, i) => <div key={i} className={`bolla ${m.role} md`}>{m.content}</div>)}
        {attesa && <div className="bolla assistant attesa">{attesa}</div>}
        <div ref={fine} />
      </div>
      <div className="chat-input">
        <input type="text" placeholder={g ? `Domanda su «${g.titolo}»…` : "Chiedi allo stratega-gare…"} value={domanda} onChange={(e) => setDomanda(e.target.value)} onKeyDown={(e) => e.key === "Enter" && invia()} disabled={senzaChiave} />
        <button className="btn primario" onClick={invia} disabled={!!attesa || !domanda.trim() || senzaChiave}>Invia</button>
      </div>
      {errore && <div className="avviso errore">{errore}</div>}

      {anteprima && <Modale titolo={anteprima.nome} onClose={() => setAnteprima(null)}><div className="md">{anteprima.testo || "(nessun testo estratto)"}</div></Modale>}
      {apriNuova && (
        <Modale titolo="Nuova gara" onClose={() => setApriNuova(false)}>
          <NuovaGara costanti={costanti} onAnnulla={() => setApriNuova(false)} onCreata={(nuova) => { setApriNuova(false); onSelezionaGara(nuova.id); onGaraAggiornata?.(nuova); }} />
        </Modale>
      )}
    </div>
  );
}
