import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api.js";

/**
 * Calendario delle scadenze: vista mese e prossime scadenze.
 *
 * Le voci nascono da sole quando una gara entra in lavorazione, ma qui si
 * possono correggere (data, ora, descrizione, tipo), cancellare e aggiungere a
 * mano. Una voce automatica che viene corretta diventa "manuale" e non verrà
 * più sovrascritta.
 *
 * Le scadenze già passate restano visibili: una scadenza scaduta è la cosa più
 * urgente da vedere, non la prima da nascondere.
 */

const MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
              "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];
const GIORNI = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"];

const meseDi = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
const oggiISO = () => new Date().toISOString().slice(0, 10);

function etichettaGiorni(g) {
  if (g === null || g === undefined) return "";
  if (g < 0) return `scaduta da ${-g} ${-g === 1 ? "giorno" : "giorni"}`;
  if (g === 0) return "oggi";
  if (g === 1) return "domani";
  return `fra ${g} giorni`;
}

export default function Calendario({ onApri, versione }) {
  const [mese, setMese] = useState(() => meseDi(new Date()));
  const [dati, setDati] = useState({ voci: [], tipi: [] });
  const [prossime, setProssime] = useState([]);
  const [inModifica, setInModifica] = useState(null);
  const [bozza, setBozza] = useState(null);
  const [daCancellare, setDaCancellare] = useState(null);
  const [nuova, setNuova] = useState(null);
  const [errore, setErrore] = useState(null);

  const carica = useCallback(async () => {
    setErrore(null);
    try {
      const [m, p] = await Promise.all([
        api.calendario({ mese }),
        api.calendario({ giorni: 30 }),
      ]);
      setDati(m); setProssime(p.voci);
    } catch (e) { setErrore(e.message); }
  }, [mese]);

  useEffect(() => { carica(); }, [carica, versione]);

  const [anno, mm] = mese.split("-").map(Number);
  const primo = new Date(anno, mm - 1, 1);
  // In Italia la settimana comincia di lunedì: getDay() dà 0 alla domenica.
  const scarto = (primo.getDay() + 6) % 7;
  const giorniNelMese = new Date(anno, mm, 0).getDate();

  const perGiorno = {};
  for (const v of dati.voci) {
    const g = Number(v.data.slice(8, 10));
    (perGiorno[g] = perGiorno[g] || []).push(v);
  }

  function cambiaMese(delta) {
    const d = new Date(anno, mm - 1 + delta, 1);
    setMese(meseDi(d));
  }

  async function salva() {
    setErrore(null);
    try {
      if (inModifica === "nuova") await api.aggiungiVoceCalendario(bozza);
      else await api.aggiornaVoceCalendario(inModifica, bozza);
      setInModifica(null); setBozza(null); setNuova(null);
      await carica();
    } catch (e) { setErrore(e.message); }
  }

  async function cancella(id) {
    setErrore(null);
    try { await api.eliminaVoceCalendario(id); setDaCancellare(null); await carica(); }
    catch (e) { setErrore(e.message); setDaCancellare(null); }
  }

  const modulo = (
    <div className="voce-modifica">
      <div className="riga">
        <label className="campo"><span>Data</span>
          <input type="date" value={bozza?.data || ""} onChange={(e) => setBozza({ ...bozza, data: e.target.value })} />
        </label>
        <label className="campo"><span>Ora</span>
          <input type="time" value={bozza?.ora || ""} onChange={(e) => setBozza({ ...bozza, ora: e.target.value })} />
        </label>
      </div>
      <label className="campo"><span>Tipo</span>
        <select value={bozza?.tipo || "altro"} onChange={(e) => setBozza({ ...bozza, tipo: e.target.value })}>
          {(dati.tipi || []).map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </label>
      <label className="campo"><span>Descrizione</span>
        <input type="text" value={bozza?.descrizione || ""}
               onChange={(e) => setBozza({ ...bozza, descrizione: e.target.value })} />
      </label>
      <div className="azioni">
        <button className="btn primario piccolo" onClick={salva}>Salva</button>
        <button className="btn piccolo" onClick={() => { setInModifica(null); setBozza(null); setNuova(null); }}>Annulla</button>
      </div>
    </div>
  );

  return (
    <div className="riquadro compatto">
      <h2>Calendario<small>{MESI[mm - 1]} {anno}</small></h2>

      <div className="cal-testa">
        <button className="btn piccolo" onClick={() => cambiaMese(-1)}>‹</button>
        <button className="btn piccolo" onClick={() => setMese(meseDi(new Date()))}>oggi</button>
        <button className="btn piccolo" onClick={() => cambiaMese(1)}>›</button>
      </div>

      <div className="cal">
        {GIORNI.map((g) => <div key={g} className="cal-intestazione">{g}</div>)}
        {Array.from({ length: scarto }).map((_, i) => <div key={`v${i}`} className="cal-vuoto" />)}
        {Array.from({ length: giorniNelMese }).map((_, i) => {
          const giorno = i + 1;
          const voci = perGiorno[giorno] || [];
          const iso = `${mese}-${String(giorno).padStart(2, "0")}`;
          return (
            <div key={giorno} className={`cal-giorno ${iso === oggiISO() ? "oggi" : ""} ${voci.length ? "con-voci" : ""}`}
                 title={voci.map((v) => `${v.tipo}: ${v.descrizione}`).join("\n")}>
              <span className="numero">{giorno}</span>
              {voci.slice(0, 3).map((v) => (
                <span key={v.id_evento} className={`pallino ${v.urgenza}`} />
              ))}
            </div>
          );
        })}
      </div>

      <h3>Prossime scadenze</h3>
      {errore && <div className="avviso errore">{errore}</div>}
      {prossime.length === 0 && <div className="scad-vuoto">Nessuna scadenza nei prossimi 30 giorni.</div>}

      <ul className="scad-lista">
        {prossime.map((v) => (
          <li key={v.id_evento} className={v.urgenza}>
            {inModifica === v.id_evento ? modulo : (
              <>
                <div className="scad-testo">
                  <b>{v.data.slice(8, 10)}/{v.data.slice(5, 7)}{v.ora && ` · ${v.ora}`}</b>{" "}
                  <span className="tipo">{v.tipo}</span>
                  <div className="nota">
                    {v.descrizione || "senza descrizione"}
                    {v.origine === "automatica" && " · dalla scheda"}
                  </div>
                  <div className={`urg ${v.urgenza}`}>{etichettaGiorni(v.giorni_mancanti)}</div>
                </div>
                <div className="scad-azioni">
                  {v.id_gara && onApri && (
                    <button className="btn piccolo" onClick={() => onApri(v.id_gara)}>Apri gara</button>
                  )}
                  <button className="btn piccolo" onClick={() => { setInModifica(v.id_evento); setBozza({ ...v }); }}>Modifica</button>
                  <button className="btn piccolo pericolo" onClick={() => setDaCancellare(v)}>×</button>
                </div>
              </>
            )}
          </li>
        ))}
      </ul>

      {inModifica === "nuova" ? modulo : (
        <div className="azioni">
          <button className="btn piccolo" onClick={() => {
            setInModifica("nuova");
            setBozza({ data: oggiISO(), ora: "", tipo: "altro", descrizione: "", id_gara: "" });
          }}>+ Aggiungi una scadenza</button>
        </div>
      )}

      {daCancellare && (
        <div className="modale-sfondo" onClick={() => setDaCancellare(null)}>
          <div className="modale" onClick={(e) => e.stopPropagation()}>
            <h3>Eliminare questa scadenza?</h3>
            <p>
              <b>{daCancellare.data}</b> — {daCancellare.tipo}
              {daCancellare.descrizione && <>: {daCancellare.descrizione}</>}.
              {daCancellare.origine === "automatica" &&
                " Viene dalla scheda della gara: tornerà se rigeneri le scadenze."}
            </p>
            <div className="azioni">
              <button className="btn pericolo" onClick={() => cancella(daCancellare.id_evento)}>Sì, elimina</button>
              <button className="btn" onClick={() => setDaCancellare(null)}>Annulla</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
