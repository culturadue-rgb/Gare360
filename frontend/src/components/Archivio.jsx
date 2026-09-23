import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api.js";

/**
 * Un archivio storico: Sociale, Cultura o Servizi educativi.
 *
 * Tabella con le 34 colonne del foglio, nello stesso ordine. Ogni riga si apre,
 * si corregge campo per campo e si cancella (con conferma). Ricerca libera e i
 * tre filtri — regione, esito, anno — lavorano insieme.
 *
 * In tabella si mostrano le colonne che si guardano sempre; tutte le altre si
 * vedono e si modificano aprendo la riga.
 */

const COLONNE_IN_VISTA = [
  "id_gara", "stazione_appaltante", "titolo_gara", "regione", "esito_gara",
  "base_asta", "punteggio_tecnico", "max_punteggio_tecnico", "scarto_tecnico",
  "nostro_ribasso", "n_concorrenti",
];

const ETICHETTE = {
  id_gara: "ID gara", cig: "CIG", stazione_appaltante: "Stazione appaltante",
  titolo_gara: "Oggetto della gara", settore: "Settore", area: "Area / CPV",
  Coordinatore_revisione: "Referente interno", scadenza_gara: "Scadenza offerte",
  stato_gara: "Stato procedura", esito_gara: "Esito per noi",
  url_cartella: "Cartella documenti", note: "Note", base_asta: "Base d'asta",
  regione: "Regione", comune: "Comune", punteggio_economico: "Nostro punteggio economico",
  punteggio_tecnico: "Nostro punteggio tecnico", max_punteggio_tecnico: "Punteggio tecnico massimo",
  scarto_tecnico: "Scarto dal vincitore (tecnico)", ore_lavoro: "Ore di progettazione",
  data_segnalazione: "Data segnalazione", data_consegna: "Data consegna",
  relazioni_tecniche: "N. relazioni tecniche", max_punteggio_economico: "Punteggio economico massimo",
  punteggio_tecnico_aggiudicatario: "Punteggio tecnico del vincitore",
  punteggio_economico_aggiudicatario: "Punteggio economico del vincitore",
  n_concorrenti: "Offerte presentate", uscente: "Eravamo il gestore uscente?",
  importo_offerto: "Importo della nostra offerta", nostro_ribasso: "Nostro ribasso %",
  modalita_partecipazione: "Forma di partecipazione", data_aggiudicazione: "Data aggiudicazione",
  provincia: "Provincia", origine_dato: "Origine del dato",
};

// I due campi che l'app ricalcola da sola, ma solo se li lasci vuoti.
const CALCOLATI = {
  scarto_tecnico: "vincitore − nostro, 0 se vinta",
  nostro_ribasso: "1 − offerto / base d'asta",
};

const vuoto = (v) => v === undefined || v === null || String(v).trim() === "";

export default function Archivio({ archivio }) {
  const [colonne, setColonne] = useState([]);
  const [righe, setRighe] = useState([]);
  const [filtri, setFiltri] = useState({ regioni: [], esiti: [], anni: [] });
  const [q, setQ] = useState({ testo: "", regione: "", esito: "", anno: "" });
  const [apertaId, setApertaId] = useState(null);
  const [bozza, setBozza] = useState(null);
  const [daCancellare, setDaCancellare] = useState(null);
  const [errore, setErrore] = useState(null);
  const [msg, setMsg] = useState(null);
  const [caricamento, setCaricamento] = useState(true);

  const carica = useCallback(async () => {
    setCaricamento(true); setErrore(null);
    try {
      const r = await api.archivioRighe(archivio, q);
      setColonne(r.colonne); setRighe(r.righe);
    } catch (e) { setErrore(e.message); setRighe([]); }
    finally { setCaricamento(false); }
  }, [archivio, q]);

  useEffect(() => { carica(); }, [carica]);

  // Cambiando archivio si riparte puliti: filtri, riga aperta e messaggi.
  useEffect(() => {
    setApertaId(null); setBozza(null); setMsg(null);
    setQ({ testo: "", regione: "", esito: "", anno: "" });
    api.archivioFiltri(archivio).then(setFiltri).catch(() => {});
  }, [archivio]);

  function apri(riga) {
    if (apertaId === riga.id_gara) { setApertaId(null); setBozza(null); return; }
    setApertaId(riga.id_gara); setBozza({ ...riga }); setMsg(null); setErrore(null);
  }

  async function salva() {
    setErrore(null);
    try {
      await api.archivioAggiorna(archivio, apertaId, bozza);
      setMsg(`Gara «${apertaId}» salvata.`);
      setApertaId(null); setBozza(null);
      await carica();
    } catch (e) { setErrore(e.message); }
  }

  async function cancella(id) {
    setErrore(null);
    try {
      await api.archivioElimina(archivio, id);
      setMsg(`Gara «${id}» eliminata.`);
      setDaCancellare(null); setApertaId(null); setBozza(null);
      await carica();
    } catch (e) { setErrore(e.message); setDaCancellare(null); }
  }

  const titolo = archivio.replace("_", " ");
  const filtroAttivo = q.testo || q.regione || q.esito || q.anno;

  return (
    <div className="riquadro">
      <h2>Archivio {titolo}<small>{righe.length} {righe.length === 1 ? "gara" : "gare"}</small></h2>

      <div className="filtri archivio-filtri">
        <input
          type="search" placeholder="Cerca in tutte le colonne…" value={q.testo}
          onChange={(e) => setQ({ ...q, testo: e.target.value })}
        />
        <select value={q.regione} onChange={(e) => setQ({ ...q, regione: e.target.value })}>
          <option value="">Tutte le regioni</option>
          {filtri.regioni.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <select value={q.esito} onChange={(e) => setQ({ ...q, esito: e.target.value })}>
          <option value="">Tutti gli esiti</option>
          {filtri.esiti.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <select value={q.anno} onChange={(e) => setQ({ ...q, anno: e.target.value })}>
          <option value="">Tutti gli anni</option>
          {filtri.anni.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        {filtroAttivo && (
          <button onClick={() => setQ({ testo: "", regione: "", esito: "", anno: "" })}>Azzera filtri</button>
        )}
      </div>

      {errore && <div className="avviso errore">{errore}</div>}
      {msg && <div className="avviso">{msg}</div>}
      {caricamento && <p className="nota">Carico…</p>}

      {!caricamento && righe.length === 0 && !errore && (
        <div className="vuoto">
          {filtroAttivo ? "Nessuna gara corrisponde ai filtri." : "Questo archivio è vuoto."}
        </div>
      )}

      {righe.length > 0 && (
        <div className="tabella-scorrevole">
          <table className="tabella-archivio">
            <thead>
              <tr>
                {COLONNE_IN_VISTA.map((c) => <th key={c}>{ETICHETTE[c] || c}</th>)}
                <th />
              </tr>
            </thead>
            <tbody>
              {righe.map((r) => (
                <tr key={r.id_gara} className={apertaId === r.id_gara ? "aperta" : ""}>
                  {COLONNE_IN_VISTA.map((c) => (
                    <td key={c} title={r[c]}>
                      {vuoto(r[c]) ? <span className="mancante">—</span> : r[c]}
                    </td>
                  ))}
                  <td className="azioni-riga">
                    <button className="btn piccolo" onClick={() => apri(r)}>
                      {apertaId === r.id_gara ? "Chiudi" : "Apri"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {bozza && (
        <div className="scheda-modifica">
          <h3>{bozza.id_gara} — {bozza.titolo_gara || "senza oggetto"}</h3>
          <p className="nota">
            Tutti i campi si possono correggere a mano. I due calcolati si
            ricalcolano da soli <b>solo se li lasci vuoti</b>: se ci scrivi un
            valore, quello resta.
          </p>

          <div className="griglia-campi">
            {colonne.map((c) => (
              <label key={c} className="campo">
                <span>
                  {ETICHETTE[c] || c}
                  {CALCOLATI[c] && <em className="nota piccola"> · calcolato: {CALCOLATI[c]}</em>}
                </span>
                {c === "note" ? (
                  <textarea
                    rows={3} value={bozza[c] ?? ""}
                    onChange={(e) => setBozza({ ...bozza, [c]: e.target.value })}
                  />
                ) : (
                  <input
                    type="text" value={bozza[c] ?? ""}
                    readOnly={c === "id_gara"}
                    title={c === "id_gara" ? "L'identificativo non si cambia: è la chiave con cui la gara viene ritrovata" : undefined}
                    onChange={(e) => setBozza({ ...bozza, [c]: e.target.value })}
                  />
                )}
              </label>
            ))}
          </div>

          <div className="azioni">
            <button className="btn primario" onClick={salva}>Salva modifiche</button>
            <button className="btn" onClick={() => { setApertaId(null); setBozza(null); }}>Annulla</button>
            <button className="btn pericolo" onClick={() => setDaCancellare(bozza.id_gara)}>
              Elimina questa gara
            </button>
          </div>
        </div>
      )}

      {daCancellare && (
        <div className="modale-sfondo" onClick={() => setDaCancellare(null)}>
          <div className="modale" onClick={(e) => e.stopPropagation()}>
            <h3>Eliminare la gara «{daCancellare}»?</h3>
            <p>
              La riga viene tolta dall'archivio <b>{titolo}</b>. Non si può annullare:
              se vuoi conservarla, scarica prima la copia di sicurezza da Impostazioni.
            </p>
            <div className="azioni">
              <button className="btn pericolo" onClick={() => cancella(daCancellare)}>Sì, elimina</button>
              <button className="btn" onClick={() => setDaCancellare(null)}>Annulla</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
