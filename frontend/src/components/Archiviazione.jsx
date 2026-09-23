import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

/**
 * Modulo di archiviazione di una gara.
 *
 * Archiviare non è un cambio di stato qualsiasi: la gara entra nell'archivio
 * storico, cioè nella memoria su cui il simulatore ragionerà per tutte le gare
 * future. Per questo si compila un modulo con tutte e 34 le colonne, e la gara
 * passa ad "Archiviata" solo quando la riga è stata scritta davvero.
 *
 * I campi che l'app già conosce arrivano precompilati. Quelli che solo una
 * persona può sapere — esito, punteggi, concorrenti, ore di lavoro — restano
 * vuoti: sono proprio quelli che rendono utile l'archivio.
 */

const ETICHETTE = {
  id_gara: "ID gara", cig: "CIG", stazione_appaltante: "Stazione appaltante",
  titolo_gara: "Oggetto della gara", settore: "Settore", area: "Area / CPV",
  Coordinatore_revisione: "Referente interno", scadenza_gara: "Scadenza offerte",
  stato_gara: "Stato procedura", esito_gara: "Esito per noi",
  url_cartella: "Cartella documenti", note: "Note", base_asta: "Base d'asta",
  regione: "Regione", comune: "Comune", punteggio_economico: "Nostro punteggio economico",
  punteggio_tecnico: "Nostro punteggio tecnico", max_punteggio_tecnico: "Punteggio tecnico massimo",
  scarto_tecnico: "Scarto dal vincitore", ore_lavoro: "Ore di progettazione",
  data_segnalazione: "Data segnalazione", data_consegna: "Data consegna",
  relazioni_tecniche: "N. relazioni tecniche", max_punteggio_economico: "Punteggio economico massimo",
  punteggio_tecnico_aggiudicatario: "Punteggio tecnico del vincitore",
  punteggio_economico_aggiudicatario: "Punteggio economico del vincitore",
  n_concorrenti: "Offerte presentate", uscente: "Eravamo il gestore uscente?",
  importo_offerto: "Importo della nostra offerta", nostro_ribasso: "Nostro ribasso %",
  modalita_partecipazione: "Forma di partecipazione", data_aggiudicazione: "Data aggiudicazione",
  provincia: "Provincia", origine_dato: "Origine del dato",
};

export default function Archiviazione({ garaId, titolo, onFatto, onAnnulla }) {
  const [dati, setDati] = useState(null);
  const [riga, setRiga] = useState({});
  const [archivio, setArchivio] = useState("");
  const [errore, setErrore] = useState(null);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    api.precompilaArchivio(garaId)
      .then((d) => { setDati(d); setRiga(d.riga); setArchivio(d.archivio_proposto); })
      .catch((e) => setErrore(e.message));
  }, [garaId]);

  async function archivia() {
    setSalvando(true); setErrore(null);
    try {
      const r = await api.archiviaGara(garaId, { archivio, riga });
      onFatto?.(r);
    } catch (e) { setErrore(e.message); }
    finally { setSalvando(false); }
  }

  if (!dati) {
    return (
      <div className="modale-sfondo" onClick={onAnnulla}>
        <div className="modale" onClick={(e) => e.stopPropagation()}>
          <p className="nota">{errore || "Preparo il modulo…"}</p>
          {errore && <div className="azioni"><button className="btn" onClick={onAnnulla}>Chiudi</button></div>}
        </div>
      </div>
    );
  }

  const mancanti = dati.da_completare.filter((c) => !String(riga[c] ?? "").trim());

  return (
    <div className="modale-sfondo" onClick={onAnnulla}>
      <div className="modale largo" onClick={(e) => e.stopPropagation()}>
        <h3>Archiviare «{titolo}»</h3>
        <p className="nota">
          La gara entra nell'archivio storico e diventa parte della memoria su cui il
          simulatore ragionerà d'ora in poi. Quello che l'app sapeva è già compilato;
          il resto serve che lo metta tu.
        </p>

        <label className="campo">
          <span>In quale archivio</span>
          <select value={archivio} onChange={(e) => setArchivio(e.target.value)}>
            {dati.archivi.map((a) => <option key={a} value={a}>{a.replace("_", " ")}</option>)}
          </select>
        </label>

        {mancanti.length > 0 && (
          <div className="avviso attenzione">
            <b>Campi ancora vuoti che varrebbe la pena compilare:</b>{" "}
            {mancanti.map((c) => ETICHETTE[c] || c).join(", ")}.
            <p className="nota">
              Si può archiviare lo stesso, ma senza punteggi e concorrenti questa gara
              non aiuterà il simulatore: resterà una riga in più, non un dato in più.
            </p>
          </div>
        )}

        <div className="griglia-campi">
          {dati.colonne.map((c) => (
            <label key={c} className="campo">
              <span>
                {ETICHETTE[c] || c}
                {dati.da_completare.includes(c) && <em className="nota piccola"> · da te</em>}
              </span>
              {c === "esito_gara" ? (
                <select value={riga[c] ?? ""} onChange={(e) => setRiga({ ...riga, [c]: e.target.value })}>
                  <option value="">—</option>
                  {dati.esiti.map((v) => <option key={v} value={v}>{v}</option>)}
                </select>
              ) : c === "stato_gara" ? (
                <select value={riga[c] ?? ""} onChange={(e) => setRiga({ ...riga, [c]: e.target.value })}>
                  <option value="">—</option>
                  {dati.stati_gara.map((v) => <option key={v} value={v}>{v}</option>)}
                </select>
              ) : c === "note" ? (
                <textarea rows={2} value={riga[c] ?? ""} onChange={(e) => setRiga({ ...riga, [c]: e.target.value })} />
              ) : (
                <input type="text" value={riga[c] ?? ""} onChange={(e) => setRiga({ ...riga, [c]: e.target.value })} />
              )}
            </label>
          ))}
        </div>

        {errore && <div className="avviso errore">{errore}</div>}

        <div className="azioni">
          <button className="btn primario" disabled={salvando} onClick={archivia}>
            {salvando ? "Archivio…" : "Archivia la gara"}
          </button>
          <button className="btn" onClick={onAnnulla}>Annulla</button>
        </div>
        <p className="nota">
          Lo scarto tecnico e il ribasso si calcolano da soli se li lasci vuoti e ci sono
          i dati da cui ricavarli.
        </p>
      </div>
    </div>
  );
}
