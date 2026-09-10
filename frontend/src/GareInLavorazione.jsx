import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { classeSettore, fmtDataOra, giorniLabel } from "../lib/util.js";

const classeStato = (s) => (s === "GO" ? "go" : s === "NO GO" ? "nogo" : "");

export function CardGara({ g, attiva, onApri }) {
  return (
    <div className={`card-gara ${attiva ? "attiva" : ""}`} role="button" tabIndex={0} onClick={() => onApri(g.id)} onKeyDown={(e) => e.key === "Enter" && onApri(g.id)}>
      <div>
        <div className="titolo">{g.titolo}</div>
        <div className="meta">
          <span className={`settore ${classeSettore(g.settore)}`}>{g.settore}</span>
          <span>{g.ente || "ente n.d."}</span>
          <span className={`stato ${classeStato(g.stato)}`}>{g.stato}</span>
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

export default function GareInLavorazione({ concluse = false, garaCorrente, onApri, versione, titolo = "Gare in lavorazione", limite }) {
  const [gare, setGare] = useState([]);
  const [filtro, setFiltro] = useState("");
  const [errore, setErrore] = useState(null);

  useEffect(() => {
    api.gare({ concluse, settore: filtro || undefined }).then((r) => setGare(r.gare)).catch((e) => setErrore(e.message));
  }, [concluse, filtro, versione]);

  const mostrate = limite ? gare.slice(0, limite) : gare;

  return (
    <div className="riquadro">
      <h2>{titolo}<small>{gare.length} {gare.length === 1 ? "gara" : "gare"}</small></h2>
      <div className="filtri">
        {[["", "Tutte"], ["Cultura", "Cultura"], ["Sociale", "Sociale"], ["Altro", "Altro"]].map(([v, l]) => (
          <button key={v} aria-pressed={filtro === v} onClick={() => setFiltro(v)}>{l}</button>
        ))}
      </div>
      {errore && <div className="avviso errore">{errore}</div>}
      {mostrate.length === 0 && <div className="vuoto">{concluse ? "Nessuna gara conclusa." : "Nessuna gara in lavorazione. Creane una dal pulsante a sinistra o trascina un PDF nelle scadenze."}</div>}
      {mostrate.map((g) => <CardGara key={g.id} g={g} attiva={g.id === garaCorrente} onApri={onApri} />)}
      {limite && gare.length > limite && <p className="nota">Altre {gare.length - limite} gare nella sezione «Gare in lavorazione».</p>}
    </div>
  );
}
