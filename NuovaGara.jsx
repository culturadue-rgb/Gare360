import { useState } from "react";
import { api } from "../lib/api.js";

// Modulo di creazione/conferma gara. `iniziale` può arrivare dall'estrazione PDF.
export default function NuovaGara({ iniziale = {}, costanti, onCreata, onAnnulla, etichetta = "Crea gara" }) {
  const [g, setG] = useState({
    titolo: iniziale.titolo || "", ente: iniziale.ente || "", settore: iniziale.settore || "Altro",
    data: iniziale.data_scadenza || (iniziale.scadenza ? iniziale.scadenza.slice(0, 10) : ""),
    ora: iniziale.ora_scadenza || (iniziale.scadenza && iniziale.scadenza.length > 10 ? iniziale.scadenza.slice(11, 16) : ""),
    base_asta: iniziale.base_asta ?? "", note: iniziale.note || "",
  });
  const [errore, setErrore] = useState(null);
  const [attesa, setAttesa] = useState(false);
  const set = (k) => (e) => setG({ ...g, [k]: e.target.value });

  async function salva() {
    if (!g.titolo.trim()) { setErrore("Il titolo è obbligatorio."); return; }
    setAttesa(true); setErrore(null);
    try {
      const scadenza = g.data ? g.data + (g.ora ? "T" + g.ora : "T23:59") : null;
      const creata = await api.creaGara({ titolo: g.titolo, ente: g.ente, settore: g.settore, scadenza, note: g.note, base_asta: g.base_asta === "" ? null : Number(g.base_asta) });
      onCreata(creata);
    } catch (e) { setErrore(e.message); } finally { setAttesa(false); }
  }

  return (
    <div>
      {iniziale.fonte && <div className="avviso info">Dati proposti dalla lettura di <b>{iniziale.nome_file}</b> ({iniziale.fonte === "ai" ? "estrazione AI" : "estrazione automatica dal testo"}). Controllali e correggi prima di salvare.{iniziale.avviso && <> {iniziale.avviso}</>}</div>}
      <label className="campo"><span>Titolo della gara *</span><input type="text" value={g.titolo} onChange={set("titolo")} /></label>
      <label className="campo"><span>Ente / stazione appaltante</span><input type="text" value={g.ente} onChange={set("ente")} /></label>
      <div className="riga tre">
        <label className="campo"><span>Settore</span>
          <select value={g.settore} onChange={set("settore")}>{(costanti?.settori || ["Cultura", "Sociale", "Altro"]).map((s) => <option key={s}>{s}</option>)}</select>
        </label>
        <label className="campo"><span>Data scadenza</span><input type="date" value={g.data} onChange={set("data")} /></label>
        <label className="campo"><span>Ora</span><input type="time" value={g.ora} onChange={set("ora")} /></label>
      </div>
      <label className="campo"><span>Base d'asta (€)</span><input type="number" min="0" step="1000" value={g.base_asta} onChange={set("base_asta")} /></label>
      <label className="campo"><span>Note</span><textarea rows={2} value={g.note} onChange={set("note")} /></label>
      {errore && <div className="avviso errore">{errore}</div>}
      <div className="azioni">
        <button className="btn primario" onClick={salva} disabled={attesa}>{attesa ? "Salvo…" : etichetta}</button>
        {onAnnulla && <button className="btn" onClick={onAnnulla}>Annulla</button>}
      </div>
    </div>
  );
}
