import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api.js";

/**
 * Simulatore di gara.
 *
 * Due livelli, tenuti separati di proposito:
 *   A) il CALCOLO, fatto dal codice: stessi ingressi, stessi numeri, sempre.
 *   B) l'ANALISI strategica, che è l'unica cosa affidata all'AI, e solo su
 *      richiesta esplicita. L'AI commenta i numeri, non li rifà.
 *
 * I parametri arrivano dalla scheda della gara e restano tutti modificabili;
 * "Ripristina dalla scheda" li riporta com'erano.
 */

const RIBASSI_RAPIDI = [3, 5, 7];
const n = (v) => { const x = Number(String(v ?? "").replace(",", ".")); return Number.isFinite(x) ? x : null; };

const ARCHIVIO_DI = (settore) => {
  const s = (settore || "").toLowerCase();
  if (s.startsWith("cultur")) return "Cultura";
  if (s.startsWith("social")) return "Sociale";
  if (s.startsWith("serviz") || s.startsWith("educ")) return "Servizi_educativi";
  return "Cultura";
};

const FORMULA_API = {
  "Lineare / proporzionale al ribasso": "lineare",
  "Bilineare con soglia": "bilineare",
};

export default function Simulatore({ elencoGare = [], garaId, onSelezionaGara }) {
  const [gara, setGara] = useState(null);
  const [par, setPar] = useState(null);          // parametri modificabili
  const [rivali, setRivali] = useState([]);
  const [ribassi, setRibassi] = useState(RIBASSI_RAPIDI);
  const [ribassoLibero, setRibassoLibero] = useState("");
  const [deltaTecnici, setDeltaTecnici] = useState([-2, 4]);
  const [stime, setStime] = useState(null);
  const [escluse, setEscluse] = useState([]);
  const [risultati, setRisultati] = useState(null);
  const [analisi, setAnalisi] = useState([]);
  const [analisiAperta, setAnalisiAperta] = useState(null);
  const [inCorso, setInCorso] = useState(null);
  const [errore, setErrore] = useState(null);

  // ---- caricamento della gara scelta -------------------------------------
  useEffect(() => {
    if (!garaId) { setGara(null); setPar(null); setRisultati(null); return; }
    api.gara(garaId).then((g) => { setGara(g); setPar(daScheda(g)); setRisultati(null); })
      .catch((e) => setErrore(e.message));
    api.elencoAnalisi(garaId).then((r) => setAnalisi(r.analisi)).catch(() => {});
  }, [garaId]);

  const archivio = ARCHIVIO_DI(gara?.settore);

  const caricaStime = useCallback(() => {
    api.stimeStoriche({ archivio, escludi: escluse.join(",") })
      .then(setStime).catch(() => setStime(null));
  }, [archivio, escluse]);
  useEffect(() => { caricaStime(); }, [caricaStime]);

  function daScheda(g) {
    const c = g?.criteri || {};
    return {
      peso_tecnico: c.peso_tecnico ?? "",
      peso_economico: c.peso_economico ?? "",
      soglia: c.soglia_sbarramento ?? "",
      riparametrazione: c.riparametrazione === "Sì",
      formula: c.formula_economica ?? "",
      coefficiente: c.coefficiente_formula ?? "0.85",
      formula_testo: c.formula_testo ?? "",
      base_asta: g?.base_asta ?? g?.scheda?.base_asta ?? "",
      criteri: (c.elenco || []).map((r) => ({
        nome: [r.codice, r.criterio, r.sub_criterio].filter(Boolean).join(" · ") || "criterio",
        tipo: r.tipo || "qualitativo",
        punti_max: n(r.punti_max) ?? 0,
      })),
    };
  }

  // ---- calcolo -----------------------------------------------------------
  async function calcola() {
    if (!par) return;
    setInCorso("calcolo"); setErrore(null);
    try {
      const resa = stime?.resa_tecnica?.disponibile ? stime.resa_tecnica.media / 100 : null;
      const corpo = {
        config: {
          nome: gara?.titolo || "gara",
          base_asta: n(par.base_asta) ?? 0,
          punti_tecnico: n(par.peso_tecnico) ?? 0,
          punti_economico: n(par.peso_economico) ?? 0,
          formula_prezzo: FORMULA_API[par.formula] || (par.formula ? "non_supportata" : "lineare"),
          coeff_bilineare: n(par.coefficiente) ?? 0.85,
          soglia_sbarramento: n(par.soglia),
          riparametrazione: !!par.riparametrazione,
          criteri: (par.criteri.length ? par.criteri : [{ nome: "Offerta tecnica", tipo: "qualitativo", punti_max: n(par.peso_tecnico) ?? 0 }])
            .map((c) => ({ ...c, resa_override: resa })),
        },
        concorrenti: rivali.filter((r) => r.nome).map((r) => ({
          nome: r.nome, livello_tecnico: n(r.livello) ?? 0.8, ribasso: n(r.ribasso) ?? 0,
        })),
        ribassi, delta_tecnici: deltaTecnici, formula_testo: par.formula_testo,
      };
      setRisultati(await api.simulaScenari(corpo));
    } catch (e) { setErrore(e.message); }
    finally { setInCorso(null); }
  }

  async function analisiCompleta() {
    if (!garaId) return;
    setInCorso("analisi"); setErrore(null);
    try {
      const v = await api.analizzaGara(garaId, { risultati: risultati || {}, archivio });
      setAnalisi((a) => [v, ...a]);
      setAnalisiAperta(v);
    } catch (e) { setErrore(e.message); }
    finally { setInCorso(null); }
  }

  async function cancellaAnalisi(id) {
    try { await api.eliminaAnalisi(garaId, id); setAnalisi((a) => a.filter((x) => x.id !== id)); setAnalisiAperta(null); }
    catch (e) { setErrore(e.message); }
  }

  const aggiungiRibasso = () => {
    const v = n(ribassoLibero);
    if (v !== null && !ribassi.includes(v)) setRibassi([...ribassi, v].sort((a, b) => a - b));
    setRibassoLibero("");
  };

  // ---- vista -------------------------------------------------------------
  if (!garaId) {
    return (
      <div className="riquadro compatto">
        <h2>Simulatore</h2>
        <label className="campo">
          <span>Scegli la gara</span>
          <select value="" onChange={(e) => onSelezionaGara?.(e.target.value)}>
            <option value="">— nessuna gara —</option>
            {elencoGare.map((g) => <option key={g.id} value={g.id}>{g.titolo}</option>)}
          </select>
        </label>
        <p className="nota">
          Il simulatore prende i parametri dalla scheda della gara: pesi, criteri,
          formula economica, soglia. Scegline una per cominciare.
        </p>
      </div>
    );
  }

  return (
    <div className="riquadro compatto">
      <h2>Simulatore<small>{gara?.titolo}</small></h2>

      <label className="campo">
        <span>Gara</span>
        <select value={garaId} onChange={(e) => onSelezionaGara?.(e.target.value)}>
          {elencoGare.map((g) => <option key={g.id} value={g.id}>{g.titolo}</option>)}
        </select>
      </label>

      {/* ---------- parametri ---------- */}
      {par && (
        <>
          <div className="riga">
            <label className="campo"><span>Punti tecnica</span>
              <input value={par.peso_tecnico} onChange={(e) => setPar({ ...par, peso_tecnico: e.target.value })} /></label>
            <label className="campo"><span>Punti prezzo</span>
              <input value={par.peso_economico} onChange={(e) => setPar({ ...par, peso_economico: e.target.value })} /></label>
            <label className="campo"><span>Sbarramento</span>
              <input value={par.soglia} onChange={(e) => setPar({ ...par, soglia: e.target.value })} /></label>
          </div>
          <label className="campo"><span>Base d'asta (€)</span>
            <input value={par.base_asta} onChange={(e) => setPar({ ...par, base_asta: e.target.value })} /></label>
          <label className="campo"><span>Formula del prezzo</span>
            <input value={par.formula || "non indicata"} readOnly title="Si cambia nella scheda della gara" /></label>
          <div className="azioni">
            <button className="btn piccolo" onClick={() => setPar(daScheda(gara))}>Ripristina dalla scheda</button>
          </div>
        </>
      )}

      {/* ---------- stime storiche ---------- */}
      {stime && (
        <div className="stime">
          <h3>Dalla nostra esperienza<small>archivio {archivio.replace("_", " ")}</small></h3>
          {stime.resa_tecnica.disponibile ? (
            <>
              <p>
                Prendiamo in media il <b>{stime.resa_tecnica.media}%</b> dei punti tecnici
                (mediana {stime.resa_tecnica.mediana}%, da {stime.resa_tecnica.minimo}% a {stime.resa_tecnica.massimo}%).
              </p>
              <p className={`nota affidabilita-${stime.resa_tecnica.affidabilita.replace(" ", "-")}`}>
                Affidabilità <b>{stime.resa_tecnica.affidabilita}</b> — {stime.resa_tecnica.nota}
              </p>
              <details>
                <summary>Le {stime.resa_tecnica.n} gare usate</summary>
                <ul className="gare-usate">
                  {stime.resa_tecnica.gare_usate.map((g) => (
                    <li key={g.id_gara}>
                      <label>
                        <input type="checkbox" checked={!escluse.includes(g.id_gara)}
                               onChange={(e) => setEscluse(e.target.checked
                                 ? escluse.filter((x) => x !== g.id_gara) : [...escluse, g.id_gara])} />
                        <b>{g.id_gara}</b> {g.valore}% — {g.ente?.slice(0, 40)} <i>({g.esito})</i>
                      </label>
                    </li>
                  ))}
                </ul>
                <p className="nota">Togli la spunta a una gara per escluderla dalla media.</p>
              </details>
            </>
          ) : (
            <p className="nota">Nessuna gara in archivio ha i punteggi tecnici: nessuna stima possibile.</p>
          )}
          {stime.avvisi?.map((a, i) => <div key={i} className="avviso attenzione">{a}</div>)}
        </div>
      )}

      {/* ---------- concorrenti ---------- */}
      <h3>Concorrenti ipotizzati</h3>
      {rivali.map((r, i) => (
        <div className="riga" key={i}>
          <input placeholder="nome" value={r.nome}
                 onChange={(e) => setRivali(rivali.map((x, j) => j === i ? { ...x, nome: e.target.value } : x))} />
          <input placeholder="livello 0-1" value={r.livello}
                 onChange={(e) => setRivali(rivali.map((x, j) => j === i ? { ...x, livello: e.target.value } : x))} />
          <input placeholder="ribasso %" value={r.ribasso}
                 onChange={(e) => setRivali(rivali.map((x, j) => j === i ? { ...x, ribasso: e.target.value } : x))} />
          <button className="btn piccolo" onClick={() => setRivali(rivali.filter((_, j) => j !== i))}>×</button>
        </div>
      ))}
      <div className="azioni">
        <button className="btn piccolo" onClick={() => setRivali([...rivali, { nome: "", livello: "0.8", ribasso: "5" }])}>
          + Concorrente
        </button>
        {stime?.n_concorrenti?.disponibile && (
          <span className="nota">di solito se ne presentano {stime.n_concorrenti.media}</span>
        )}
      </div>

      {/* ---------- scenari da calcolare ---------- */}
      <h3>Scenari</h3>
      <div className="filtri">
        {ribassi.map((r) => (
          <button key={r} onClick={() => setRibassi(ribassi.filter((x) => x !== r))} title="togli">
            {r}% ×
          </button>
        ))}
        <input style={{ width: "5rem" }} placeholder="altro %" value={ribassoLibero}
               onChange={(e) => setRibassoLibero(e.target.value)}
               onKeyDown={(e) => e.key === "Enter" && aggiungiRibasso()} />
        <button className="btn piccolo" onClick={aggiungiRibasso}>+</button>
      </div>

      <div className="azioni">
        <button className="btn primario" disabled={inCorso === "calcolo"} onClick={calcola}>
          {inCorso === "calcolo" ? "Calcolo…" : "Calcola gli scenari"}
        </button>
      </div>

      {errore && <div className="avviso errore">{errore}</div>}

      {/* ---------- risultati ---------- */}
      {risultati && (
        <>
          <div className="tabella-scorrevole">
            <table className="tabella-archivio">
              <thead>
                <tr><th>Scenario</th><th>Tecnica</th><th>Prezzo</th><th>Totale</th><th>Pos.</th><th>Esito</th></tr>
              </thead>
              <tbody>
                {risultati.scenari.map((s, i) => (
                  <tr key={i} className={s.vinciamo ? "aperta" : ""}>
                    <td>{s.etichetta}</td>
                    {s.calcolabile ? (
                      <>
                        <td>{s.nostro_tecnico}</td><td>{s.nostro_economico}</td>
                        <td><b>{s.nostro_totale}</b></td><td>{s.posizione}</td>
                        <td>{s.vinciamo ? "vince" : `vince ${s.vincitore}`}</td>
                      </>
                    ) : (
                      <td colSpan={5} className="mancante">non calcolabile</td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {risultati.scenari.some((s) => !s.calcolabile) && (
            <div className="avviso attenzione">
              <b>La formula del disciplinare non è fra quelle che il simulatore sa calcolare.</b>
              <p>{risultati.scenari.find((s) => !s.calcolabile)?.motivo}</p>
              {par?.formula_testo && (
                <p>Testo del disciplinare: <i>{par.formula_testo}</i></p>
              )}
            </div>
          )}

          {risultati.scenari[0]?.calcolabile && (
            <p className="nota">
              Ribasso minimo per vincere, a tecnica invariata:{" "}
              <b>{risultati.scenari[0].ribasso_minimo_vittoria ?? "non raggiungibile"}%</b>
              {risultati.scenari[0].punti_tecnici_mancanti > 0 &&
                <> · oppure {risultati.scenari[0].punti_tecnici_mancanti} punti tecnici in più.</>}
            </p>
          )}

          <div className="azioni">
            <button className="btn primario" disabled={inCorso === "analisi"} onClick={analisiCompleta}>
              {inCorso === "analisi" ? "Analizzo…" : "Analisi completa"}
            </button>
            <span className="nota">l'unica parte affidata all'AI: commenta questi numeri, non li rifà</span>
          </div>
        </>
      )}

      {/* ---------- analisi salvate ---------- */}
      {analisi.length > 0 && (
        <>
          <h3>Analisi salvate</h3>
          <ul className="scad-lista">
            {analisi.map((a) => (
              <li key={a.id}>
                <div className="scad-testo">
                  <b>{a.quando.replace("T", " ").slice(0, 16)}</b>
                  <div className="nota">{(a.testo || "").slice(0, 110)}…</div>
                </div>
                <div className="scad-azioni">
                  <button className="btn piccolo" onClick={async () => setAnalisiAperta(await api.leggiAnalisi(garaId, a.id))}>Leggi</button>
                  <button className="btn piccolo pericolo" onClick={() => cancellaAnalisi(a.id)}>×</button>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}

      {analisiAperta && (
        <div className="modale-sfondo" onClick={() => setAnalisiAperta(null)}>
          <div className="modale largo" onClick={(e) => e.stopPropagation()}>
            <h3>Analisi del {analisiAperta.quando.replace("T", " ").slice(0, 16)}</h3>
            <div className="md">{analisiAperta.testo}</div>
            <div className="azioni"><button className="btn" onClick={() => setAnalisiAperta(null)}>Chiudi</button></div>
          </div>
        </div>
      )}
    </div>
  );
}
