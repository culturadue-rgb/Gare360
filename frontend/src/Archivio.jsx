import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import GrigliaEdit from "./GrigliaEdit.jsx";

const VUOTA = () => ({
  titolo: "", ente: "", anno: "", base_asta: null, punti_tecnico: 70, punti_economico: 30,
  risultato: "vinta", punteggio_nostro: null, punteggio_vincitore: null,
  ribasso_nostro: null, ribasso_vincitore: null, formula_prezzo: "",
  criteri: [{ criterio: "", tipo: "qualitativo", punti_max: 0, punti_presi: 0, note: "" }],
  funzionato: "", persi: "", riutilizzabili: "", note_ente: "",
});

export default function Archivio() {
  const [schede, setSchede] = useState([]);
  const [testo, setTesto] = useState("");
  const [nuova, setNuova] = useState(VUOTA());
  const [msg, setMsg] = useState(null);
  const [errore, setErrore] = useState(null);

  async function carica() {
    try { const a = await api.archivio(); setSchede(a.schede); setTesto(a.testo); }
    catch (e) { setErrore(e.message); }
  }
  useEffect(() => { carica(); }, []);

  const set = (k) => (e) => setNuova({ ...nuova, [k]: e.target.type === "number" ? (e.target.value === "" ? null : Number(e.target.value)) : e.target.value });

  async function salvaTesto() {
    setMsg(null); setErrore(null);
    try { await api.salvaArchivioRaw(testo); await carica(); setMsg("Archivio salvato."); }
    catch (e) { setErrore(e.message); }
  }

  async function aggiungi() {
    setMsg(null); setErrore(null);
    if (!nuova.titolo.trim()) { setErrore("Il nome della gara è obbligatorio."); return; }
    try {
      await api.aggiungiScheda({ ...nuova, criteri: nuova.criteri.filter((c) => c.criterio?.trim()) });
      await carica(); setMsg(`Scheda «${nuova.titolo}» aggiunta.`); setNuova(VUOTA());
    } catch (e) { setErrore(e.message); }
  }

  const classeEsito = (r) => (r || "").toLowerCase().startsWith("vint") ? "vinta" : "persa";

  return (
    <div className="due-col inverso">
      <div>
        <h2>Schede gara</h2>
        <p className="nota">Le schede vivono in <code>storico-gare.md</code>, stesso formato del template del progetto.</p>
        {schede.length === 0 && <div className="vuoto">Nessuna scheda ancora. Aggiungine una dal modulo o incolla il verbale nell'editor qui sotto.</div>}
        {schede.map((s, i) => (
          <details key={i}>
            <summary><span>{s.titolo}</span><span className="nota">{s.risultato || "esito n.d."} · {s.anno || "anno n.d."}</span></summary>
            <div>
              <span className={`esito ${classeEsito(s.risultato)}`}>{s.risultato || "esito n.d."}</span>
              <p>Ente: {s.ente || "—"} · Base d'asta: {s.base_asta ?? "—"} · Nostro ribasso: {s.ribasso_nostro ?? "—"}% · Ribasso vincitore: {s.ribasso_vincitore ?? "—"}%</p>
              {s.criteri.length > 0 && (
                <table>
                  <thead><tr><th>Criterio</th><th>Tipo</th><th className="num">Max</th><th className="num">Presi</th><th>Note</th></tr></thead>
                  <tbody>{s.criteri.map((c, j) => <tr key={j}><td>{c.criterio}</td><td>{c.tipo}</td><td className="num">{c.punti_max}</td><td className="num">{c.punti_presi}</td><td>{c.note}</td></tr>)}</tbody>
                </table>
              )}
              <details style={{ marginTop: ".6rem" }}><summary>Testo completo della scheda</summary><div className="md">{s.blocco}</div></details>
            </div>
          </details>
        ))}

        <h3>Editor del file completo</h3>
        <textarea className="mono" rows={16} value={testo} onChange={(e) => setTesto(e.target.value)} />
        <div className="azioni"><button className="btn primario" onClick={salvaTesto}>Salva file</button></div>
        {msg && <div className="avviso">{msg}</div>}
        {errore && <div className="avviso errore">{errore}</div>}
      </div>

      <div>
        <h2>Nuova scheda</h2>
        <label className="campo"><span>Nome / oggetto della gara *</span><input type="text" value={nuova.titolo} onChange={set("titolo")} /></label>
        <label className="campo"><span>Ente / stazione appaltante</span><input type="text" value={nuova.ente} onChange={set("ente")} /></label>
        <div className="riga">
          <label className="campo"><span>Anno</span><input type="text" value={nuova.anno} onChange={set("anno")} /></label>
          <label className="campo"><span>Base d'asta (€)</span><input type="number" min="0" step="10000" value={nuova.base_asta ?? ""} onChange={set("base_asta")} /></label>
        </div>
        <div className="riga">
          <label className="campo"><span>Punti tecnico</span><input type="number" min="0" max="100" value={nuova.punti_tecnico ?? ""} onChange={set("punti_tecnico")} /></label>
          <label className="campo"><span>Punti economico</span><input type="number" min="0" max="100" value={nuova.punti_economico ?? ""} onChange={set("punti_economico")} /></label>
        </div>
        <label className="campo"><span>Risultato</span>
          <select value={nuova.risultato} onChange={set("risultato")}>
            {["vinta", "persa", "esclusa", "ritirata"].map((v) => <option key={v}>{v}</option>)}
          </select>
        </label>
        <div className="riga">
          <label className="campo"><span>Nostro punteggio totale</span><input type="number" min="0" max="100" step="0.01" value={nuova.punteggio_nostro ?? ""} onChange={set("punteggio_nostro")} /></label>
          <label className="campo"><span>Punteggio vincitore</span><input type="number" min="0" max="100" step="0.01" value={nuova.punteggio_vincitore ?? ""} onChange={set("punteggio_vincitore")} /></label>
        </div>
        <div className="riga">
          <label className="campo"><span>Nostro ribasso %</span><input type="number" min="0" max="100" step="0.5" value={nuova.ribasso_nostro ?? ""} onChange={set("ribasso_nostro")} /></label>
          <label className="campo"><span>Ribasso vincitore %</span><input type="number" min="0" max="100" step="0.5" value={nuova.ribasso_vincitore ?? ""} onChange={set("ribasso_vincitore")} /></label>
        </div>
        <label className="campo"><span>Meccanismo punti prezzo</span><input type="text" value={nuova.formula_prezzo} onChange={set("formula_prezzo")} /></label>

        <h3>Punteggi voce per voce (dal verbale)</h3>
        <GrigliaEdit
          righe={nuova.criteri} onChange={(c) => setNuova({ ...nuova, criteri: c })}
          nuovaRiga={() => ({ criterio: "", tipo: "qualitativo", punti_max: 0, punti_presi: 0, note: "" })}
          etichettaAggiungi="Aggiungi voce"
          colonne={[
            { key: "criterio", label: "Criterio", type: "text" },
            { key: "tipo", label: "Tipo", type: "select", options: ["tabellare", "qualitativo"], width: 120 },
            { key: "punti_max", label: "Max", type: "number", min: 0, step: 0.5, width: 75 },
            { key: "punti_presi", label: "Presi", type: "number", min: 0, step: 0.5, width: 75 },
            { key: "note", label: "Note", type: "text" },
          ]}
        />

        <label className="campo" style={{ marginTop: ".8rem" }}><span>Cosa ha funzionato</span><textarea rows={2} value={nuova.funzionato} onChange={set("funzionato")} /></label>
        <label className="campo"><span>Dove abbiamo lasciato punti e perché</span><textarea rows={2} value={nuova.persi} onChange={set("persi")} /></label>
        <label className="campo"><span>Contenuti riutilizzabili</span><textarea rows={2} value={nuova.riutilizzabili} onChange={set("riutilizzabili")} /></label>
        <label className="campo"><span>Note su commissione / ente</span><textarea rows={2} value={nuova.note_ente} onChange={set("note_ente")} /></label>
        <div className="azioni"><button className="btn primario pieno" onClick={aggiungi}>Aggiungi all'archivio</button></div>
      </div>
    </div>
  );
}
