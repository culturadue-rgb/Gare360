import { useState } from "react";
import { api } from "../lib/api.js";
import GrigliaEdit from "./GrigliaEdit.jsx";

const FORMULE = [
  ["lineare", "Interpolazione lineare sul ribasso"],
  ["proporzionale", "Proporzionale al ribasso (R / Rmax)"],
  ["bilineare", "Bilineare con soglia (a due rette)"],
];

const n = (v, d = 2) => (typeof v === "number" ? v.toFixed(d) : "—");

export default function Simulatore() {
  const [cfg, setCfg] = useState({
    nome: "Nuova gara", base_asta: 500000, punti_tecnico: 70, punti_economico: 30,
    formula_prezzo: "lineare", coeff_bilineare: 0.85, usa_soglia: false, soglia: 40, riparametrazione: false,
  });
  const [criteri, setCriteri] = useState([
    { nome: "Progetto tecnico", tipo: "qualitativo", punti_max: 30, resa_override: null },
    { nome: "Migliorie", tipo: "qualitativo", punti_max: 20, resa_override: null },
    { nome: "Certificazioni", tipo: "tabellare", punti_max: 10, resa_override: null },
    { nome: "Esperienza analoga", tipo: "tabellare", punti_max: 10, resa_override: null },
  ]);
  const [ribasso, setRibasso] = useState(12);
  const [conc, setConc] = useState([
    { nome: "Concorrente A", livello_tecnico: 0.85, ribasso: 15 },
    { nome: "Concorrente B", livello_tecnico: 0.7, ribasso: 22 },
  ]);
  const [res, setRes] = useState(null);
  const [errore, setErrore] = useState(null);
  const [attesa, setAttesa] = useState(false);

  const set = (k) => (e) => setCfg({ ...cfg, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.type === "number" ? Number(e.target.value) : e.target.value });

  const sommaCriteri = criteri.reduce((s, c) => s + (Number(c.punti_max) || 0), 0);

  async function simula() {
    setAttesa(true); setErrore(null);
    try {
      const r = await api.simula({
        config: {
          nome: cfg.nome, base_asta: cfg.base_asta, punti_tecnico: cfg.punti_tecnico, punti_economico: cfg.punti_economico,
          formula_prezzo: cfg.formula_prezzo, coeff_bilineare: Number(cfg.coeff_bilineare),
          soglia_sbarramento: cfg.usa_soglia ? cfg.soglia : null, riparametrazione: cfg.riparametrazione,
          criteri: criteri.filter((c) => c.nome?.trim() && c.punti_max != null)
            .map((c) => ({ ...c, punti_max: Number(c.punti_max), resa_override: c.resa_override === "" ? null : c.resa_override })),
        },
        ribasso_nostro: ribasso,
        concorrenti: conc.filter((c) => c.nome?.trim()),
      });
      setRes(r);
    } catch (e) { setErrore(e.message); } finally { setAttesa(false); }
  }

  const noi = res?.noi;
  const s = res?.sensibilita;

  return (
    <div className="due-col">
      <div>
        <h2>Configurazione gara</h2>
        <label className="campo"><span>Nome gara</span><input type="text" value={cfg.nome} onChange={set("nome")} /></label>
        <label className="campo"><span>Importo a base d'asta (€)</span><input type="number" min="0" step="10000" value={cfg.base_asta} onChange={set("base_asta")} /></label>
        <div className="riga">
          <label className="campo"><span>Punti tecnico</span><input type="number" min="0" max="100" step="5" value={cfg.punti_tecnico} onChange={set("punti_tecnico")} /></label>
          <label className="campo"><span>Punti economico</span><input type="number" min="0" max="100" step="5" value={cfg.punti_economico} onChange={set("punti_economico")} /></label>
        </div>
        {Math.abs(cfg.punti_tecnico + cfg.punti_economico - 100) > 1e-6 && <div className="avviso">Tecnico + economico dovrebbero fare 100.</div>}

        <label className="campo"><span>Formula punteggio prezzo</span>
          <select value={cfg.formula_prezzo} onChange={set("formula_prezzo")}>
            {FORMULE.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
        {cfg.formula_prezzo === "bilineare" && (
          <label className="campo"><span>Coefficiente X</span>
            <select value={cfg.coeff_bilineare} onChange={set("coeff_bilineare")}>
              {[0.8, 0.85, 0.9].map((v) => <option key={v} value={v}>{v.toFixed(2)}</option>)}
            </select>
          </label>
        )}
        <div className="riga">
          <div>
            <label className="spunta"><input type="checkbox" checked={cfg.usa_soglia} onChange={set("usa_soglia")} /> Soglia di sbarramento</label>
            <label className="campo"><span>Punti tecnici minimi</span><input type="number" min="0" max="100" value={cfg.soglia} disabled={!cfg.usa_soglia} onChange={set("soglia")} /></label>
          </div>
          <label className="spunta"><input type="checkbox" checked={cfg.riparametrazione} onChange={set("riparametrazione")} /> Riparametrazione tecnica</label>
        </div>

        <h3>Criteri tecnici</h3>
        <p className="nota">Lascia vuota la resa per usare il tracker (stesso nome di criterio); 0–1 per forzarla qui.</p>
        <GrigliaEdit
          righe={criteri} onChange={setCriteri}
          nuovaRiga={() => ({ nome: "", tipo: "qualitativo", punti_max: 0, resa_override: null })}
          etichettaAggiungi="Aggiungi criterio"
          colonne={[
            { key: "nome", label: "Criterio", type: "text" },
            { key: "tipo", label: "Tipo", type: "select", options: ["tabellare", "qualitativo"], width: 130 },
            { key: "punti_max", label: "Punti max", type: "number", min: 0, step: 1, width: 90 },
            { key: "resa_override", label: "Resa manuale", type: "number", min: 0, max: 1, step: 0.05, width: 110 },
          ]}
        />
        {Math.abs(sommaCriteri - cfg.punti_tecnico) > 1e-6 && <div className="avviso">I criteri sommano {sommaCriteri} punti ma il tecnico vale {cfg.punti_tecnico}.</div>}

        <h3>Offerta economica</h3>
        <label className="campo"><span>Nostro ribasso</span>
          <div className="slider">
            <input type="range" min="0" max="60" step="0.5" value={ribasso} onChange={(e) => setRibasso(Number(e.target.value))} />
            <output>{ribasso.toFixed(1)}%</output>
          </div>
        </label>

        <h3>Concorrenti (profili ipotizzati)</h3>
        <GrigliaEdit
          righe={conc} onChange={setConc}
          nuovaRiga={() => ({ nome: `Concorrente ${String.fromCharCode(65 + conc.length)}`, livello_tecnico: 0.75, ribasso: 15 })}
          etichettaAggiungi="Aggiungi concorrente"
          colonne={[
            { key: "nome", label: "Nome", type: "text" },
            { key: "livello_tecnico", label: "Livello tecnico (0–1)", type: "number", min: 0, max: 1, step: 0.05, width: 140 },
            { key: "ribasso", label: "Ribasso %", type: "number", min: 0, max: 100, step: 0.5, width: 100 },
          ]}
        />

        <div className="azioni" style={{ marginTop: "1rem" }}>
          <button className="btn primario pieno" onClick={simula} disabled={attesa}>{attesa ? "Calcolo…" : "Simula"}</button>
        </div>
        {errore && <div className="avviso errore">{errore}</div>}
      </div>

      <div>
        <h2>Risultato</h2>
        {!res ? (
          <div className="vuoto">Compila la configurazione e premi <b>Simula</b>. Stessi input, stesso risultato: nessuna casualità.</div>
        ) : (
          <>
            <div className="metriche">
              <div className="metrica"><span>Posizione</span><strong>{res.posizione}°</strong></div>
              <div className="metrica"><span>Totale</span><strong>{n(noi.totale)}</strong></div>
              <div className="metrica"><span>Tecnico</span><strong>{n(noi.tecnico)}</strong></div>
              <div className="metrica"><span>Economico</span><strong>{n(noi.economico)}</strong></div>
            </div>

            {noi.escluso
              ? <div className="esito esclusa">Esclusi: tecnico sotto la soglia di {n(s.punti_tecnici_mancanti)} punti</div>
              : res.posizione === 1
                ? <div className="esito vinta">Gara vinta nella simulazione</div>
                : <div className="esito persa">Distacco dal primo: {n(res.distacco)} punti</div>}

            <h3>Graduatoria</h3>
            <table>
              <thead><tr><th>Offerente</th><th className="num">Tecnico</th><th className="num">Economico</th><th className="num">Totale</th><th className="num">Ribasso</th></tr></thead>
              <tbody>
                {res.graduatoria.map((o) => (
                  <tr key={o.nome} className={o.nome === "Noi" ? "noi" : o.escluso ? "escluso" : ""}>
                    <td>{o.nome}{o.escluso ? " (escluso)" : ""}</td>
                    <td className="num">{n(o.tecnico)}</td><td className="num">{n(o.economico)}</td>
                    <td className="num">{n(o.totale)}</td><td className="num">{n(o.ribasso, 1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <h3>Cosa serve per vincere</h3>
            {noi.escluso ? (
              <p>Servono almeno <b>{n(s.punti_tecnici_mancanti)} punti tecnici</b> in più per superare lo sbarramento.</p>
            ) : res.posizione === 1 ? (
              <p>Con questi profili di concorrenti la nostra offerta è già prima.</p>
            ) : (
              <>
                {s.ribasso_minimo_vittoria != null
                  ? <p>A tecnico invariato, il ribasso minimo per vincere è <b>{n(s.ribasso_minimo_vittoria, 1)}%</b> (oggi {n(noi.ribasso, 1)}%).</p>
                  : <p>Nessun ribasso fino al 100% basta da solo: bisogna recuperare sul tecnico.</p>}
                <p>A ribasso invariato, servono <b>{n(s.punti_tecnici_mancanti)} punti tecnici</b> in più.</p>
              </>
            )}

            <h3>Dettaglio criteri (da dove viene il tecnico)</h3>
            <table>
              <thead><tr><th>Criterio</th><th className="num">Punti max</th><th className="num">Resa</th><th className="num">Punti attesi</th><th>Fonte resa</th></tr></thead>
              <tbody>
                {Object.entries(noi.dettaglio_criteri).map(([k, v]) => (
                  <tr key={k}><td>{k}</td><td className="num">{v.punti_max}</td><td className="num">{Math.round(v.resa * 100)}%</td><td className="num">{n(v.punti)}</td><td>{v.fonte}</td></tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  );
}
