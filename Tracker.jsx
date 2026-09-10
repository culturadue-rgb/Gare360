import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import GrigliaEdit from "./GrigliaEdit.jsx";

export default function Tracker() {
  const [righe, setRighe] = useState([]);
  const [raw, setRaw] = useState("");
  const [msg, setMsg] = useState(null);
  const [errore, setErrore] = useState(null);

  async function carica() {
    try {
      const [t, r] = await Promise.all([api.tracker(), api.trackerRaw()]);
      setRighe(t.righe); setRaw(r.testo);
    } catch (e) { setErrore(e.message); }
  }
  useEffect(() => { carica(); }, []);

  async function salvaGriglia() {
    setMsg(null); setErrore(null);
    try {
      const pulite = righe.filter((r) => r.criterio?.trim() && r.resa != null)
        .map((r) => ({ criterio: r.criterio.trim(), tipo: r.tipo || "qualitativo", resa: Number(r.resa), n: Number(r.n) || 0, note: r.note || "" }));
      const t = await api.salvaTracker(pulite);
      setRighe(t.righe); setRaw((await api.trackerRaw()).testo);
      setMsg(`Tracker salvato: ${t.righe.length} criteri.`);
    } catch (e) { setErrore(e.message); }
  }

  async function salvaRaw() {
    setMsg(null); setErrore(null);
    try {
      const t = await api.salvaTrackerRaw(raw);
      setRighe(t.righe); setMsg("CSV salvato.");
    } catch (e) { setErrore(e.message); }
  }

  return (
    <div className="due-col inverso">
      <div>
        <h2>Tracker prestazioni per criterio</h2>
        <p className="nota">Il simulatore legge da qui la resa attesa di ogni criterio. Il file è <code>tracker.csv</code>: modificalo nella griglia, nell'editor testo, o in Excel.</p>
        <GrigliaEdit
          righe={righe} onChange={setRighe}
          nuovaRiga={() => ({ criterio: "", tipo: "qualitativo", resa: 0.7, n: 0, note: "" })}
          etichettaAggiungi="Aggiungi criterio"
          colonne={[
            { key: "criterio", label: "Criterio", type: "text" },
            { key: "tipo", label: "Tipo", type: "select", options: ["tabellare", "qualitativo"], width: 130 },
            { key: "resa", label: "Resa (0–1)", type: "number", min: 0, max: 1, step: 0.05, width: 100 },
            { key: "n", label: "Gare (n)", type: "number", min: 0, step: 1, width: 90 },
            { key: "note", label: "Note", type: "text" },
          ]}
        />
        <div className="azioni"><button className="btn primario pieno" onClick={salvaGriglia}>Salva tracker</button></div>
        {msg && <div className="avviso">{msg}</div>}
        {errore && <div className="avviso errore">{errore}</div>}

        <details style={{ marginTop: "1rem" }}>
          <summary>Editor testo del file CSV</summary>
          <div>
            <textarea className="mono" rows={10} value={raw} onChange={(e) => setRaw(e.target.value)} />
            <div className="azioni"><button className="btn contorno" onClick={salvaRaw}>Salva CSV</button></div>
          </div>
        </details>
      </div>

      <div>
        <h3>Come compilarlo</h3>
        <p>Una riga per criterio. Usa lo stesso nome che scriverai nel simulatore: l'abbinamento ignora maiuscole e spazi.</p>
        <p><b>resa</b>: frazione dei punti massimi che prendete di solito (0,70 = 70%).</p>
        <p><b>tipo</b>: tabellare o qualitativo.</p>
        <p><b>n</b>: su quante gare si basa il valore (solo informativo).</p>
        <p><b>note</b>: libere.</p>
        <p className="nota">Se nel simulatore inserisci un criterio che qui non c'è, viene usata una resa di default (80% tabellare, 65% qualitativo) e il dettaglio lo segnala come «default».</p>
      </div>
    </div>
  );
}
