import { useState } from "react";
import { api } from "../lib/api.js";
import Archiviazione from "./Archiviazione.jsx";

/**
 * Il selettore di stato di una gara, con le due conseguenze che non devono
 * accadere di nascosto:
 *
 *   -> Archiviata     si apre il modulo delle 34 colonne. La gara cambia stato
 *                     solo quando la riga è stata scritta in archivio.
 *   -> Da decidere    se c'erano scadenze in calendario, si chiede se toglierle
 *                     invece di cancellarle da soli.
 */
export default function CambioStato({ gara, stati = [], onCambiata }) {
  const [archiviazione, setArchiviazione] = useState(false);
  const [chiediCalendario, setChiediCalendario] = useState(null);
  const [errore, setErrore] = useState(null);
  const [attesa, setAttesa] = useState(false);

  async function cambia(nuovo) {
    if (nuovo === gara.stato) return;
    setErrore(null);

    // Archiviare passa sempre dal modulo: non è un cambio di stato qualsiasi.
    if (nuovo === "Archiviata") { setArchiviazione(true); return; }

    setAttesa(true);
    try {
      const g = await api.aggiornaGara(gara.id, { stato: nuovo });
      if (g.calendario?.azione === "generate") {
        const c = g.calendario;
        if (c.create?.length) setErrore(null);
      }
      if (g.calendario?.azione === "chiedi_rimozione") {
        setChiediCalendario({ voci: g.calendario.voci });
      }
      onCambiata?.(g);
    } catch (e) { setErrore(e.message); }
    finally { setAttesa(false); }
  }

  async function rimuoviScadenze(rimuovi) {
    if (rimuovi) {
      try { await api.rimuoviScadenzeGara(gara.id); } catch (e) { setErrore(e.message); }
    }
    setChiediCalendario(null);
    onCambiata?.();
  }

  return (
    <>
      <select className="cambio-stato" value={gara.stato} disabled={attesa}
              onChange={(e) => cambia(e.target.value)} onClick={(e) => e.stopPropagation()}>
        {stati.map((s) => <option key={s} value={s}>{s}</option>)}
      </select>

      {errore && <div className="avviso errore">{errore}</div>}

      {archiviazione && (
        <Archiviazione
          garaId={gara.id} titolo={gara.titolo}
          onAnnulla={() => setArchiviazione(false)}
          onFatto={(r) => { setArchiviazione(false); onCambiata?.(r.gara); }}
        />
      )}

      {chiediCalendario && (
        <div className="modale-sfondo" onClick={() => rimuoviScadenze(false)}>
          <div className="modale" onClick={(e) => e.stopPropagation()}>
            <h3>Togliere le scadenze dal calendario?</h3>
            <p>
              Questa gara torna a «Da decidere» e ha <b>{chiediCalendario.voci}</b>{" "}
              {chiediCalendario.voci === 1 ? "scadenza" : "scadenze"} in calendario.
              Le tolgo o le lascio?
            </p>
            <p className="nota">
              Se le lasci restano visibili e modificabili; rientrando in lavorazione
              non verranno duplicate.
            </p>
            <div className="azioni">
              <button className="btn pericolo" onClick={() => rimuoviScadenze(true)}>Toglile</button>
              <button className="btn" onClick={() => rimuoviScadenze(false)}>Lasciale</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
