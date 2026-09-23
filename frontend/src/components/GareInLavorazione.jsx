import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { classeSettore, fmtDataOra, giorniLabel } from "../lib/util.js";
import CambioStato from "./CambioStato.jsx";

// Un colore per ogni passo del flusso, così lo stato si riconosce a colpo d'occhio.
const classeStato = (s) => ({
  "Da decidere": "decidere",
  "In lavorazione": "lavorazione",
  "Conclusa": "conclusa",
  "Archiviata": "archiviata",
}[s] || "");

export function CardGara({ g, attiva, onApri, stati, onCambiata }) {
  return (
    <div className={`card-gara ${attiva ? "attiva" : ""}`} role="button" tabIndex={0} onClick={() => onApri(g.id)} onKeyDown={(e) => e.key === "Enter" && onApri(g.id)}>
      <div>
        <div className="titolo">{g.titolo}</div>
        <div className="meta">
          <span className={`settore ${classeSettore(g.settore)}`}>{g.settore}</span>
          <span>{g.ente || "ente n.d."}</span>
          {stati ? <CambioStato gara={g} stati={stati} onCambiata={onCambiata} />
                 : <span className={`stato ${classeStato(g.stato)}`}>{g.stato}</span>}
          {g.n_documenti > 0 && <span>{g.n_documenti} doc.</span>}
          {!g.memoria_attiva && <span title="Memoria archiviata (più di 15 giorni senza attività)">memoria archiviata</span>}
        </div>
      </div>
      <div className="destra">
        <span className={`urg ${g.urgenza}`}>{g.scadenza ? `${giorniLabel(g.giorni_mancanti)}` : "senza scadenza"}</span>
        <span className="nota">scade {fmtDataOra(g.scadenza)}</span>
        <span className="nota">modif. {fmtDataOra(g.aggiornata)}</span>
      </div>
    </div>
  );
}

export default function GareInLavorazione({ stato, garaCorrente, onApri, versione, titolo, limite, stati, onCambiata }) {
  const [gare, setGare] = useState([]);
  const [filtro, setFiltro] = useState("");
  const [errore, setErrore] = useState(null);

  // Senza `stato` si mostrano le gare ancora aperte (Home); con `stato` solo
  // quelle di quel passo del flusso.
  useEffect(() => {
    const filtri = { settore: filtro || undefined };
    if (stato) filtri.stato = stato; else filtri.concluse = false;
    api.gare(filtri).then((r) => setGare(r.gare)).catch((e) => setErrore(e.message));
  }, [stato, filtro, versione]);

  const mostrate = limite ? gare.slice(0, limite) : gare;

  return (
    <div className="riquadro">
      <h2>{titolo || "Gare aperte"}<small>{gare.length} {gare.length === 1 ? "gara" : "gare"}</small></h2>
      <div className="filtri">
        {[["", "Tutte"], ["Cultura", "Cultura"], ["Sociale", "Sociale"], ["Altro", "Altro"]].map(([v, l]) => (
          <button key={v} aria-pressed={filtro === v} onClick={() => setFiltro(v)}>{l}</button>
        ))}
      </div>
      {errore && <div className="avviso errore">{errore}</div>}
      {mostrate.length === 0 && (
        <div className="vuoto">
          {stato ? `Nessuna gara nello stato «${stato}».`
                 : "Nessuna gara aperta. Creane una dal pulsante «+ Nuova gara»."}
        </div>
      )}
      {mostrate.map((g) => <CardGara key={g.id} g={g} attiva={g.id === garaCorrente} onApri={onApri} stati={stati} onCambiata={onCambiata} />)}
      {limite && gare.length > limite && <p className="nota">Altre {gare.length - limite} gare nelle sezioni del menu.</p>}
    </div>
  );
}
