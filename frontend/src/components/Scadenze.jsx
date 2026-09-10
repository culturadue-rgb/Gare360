import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api.js";
import { classeSettore, fmtData, fmtDataOra, giorniLabel } from "../lib/util.js";
import Modale from "./Modale.jsx";
import NuovaGara from "./NuovaGara.jsx";

function Lista({ voci, onApri }) {
  if (!voci.length) return <div className="scad-vuoto">Nessuna scadenza nei prossimi 7 giorni.</div>;
  return (
    <ul className="scad-lista">
      {voci.map((g) => (
        <li key={g.id} onClick={() => onApri(g.id)}>
          <span className="nome">{g.titolo}</span>
          <span className={`quando urg ${g.urgenza}`}>{giorniLabel(g.giorni_mancanti)}</span>
          <span className="ente">{g.ente || "ente n.d."}</span>
          <span className="quando nota">{fmtDataOra(g.scadenza)}</span>
        </li>
      ))}
    </ul>
  );
}

function CalendarioMese({ mese, dati, onApri }) {
  const [anno, m] = mese.split("-").map(Number);
  const primo = new Date(anno, m - 1, 1);
  const giorniNelMese = new Date(anno, m, 0).getDate();
  const offset = (primo.getDay() + 6) % 7; // lunedì = 0
  const oggi = new Date().toISOString().slice(0, 10);
  const tutte = [...dati.cultura, ...dati.sociale, ...dati.altro];
  const perGiorno = {};
  tutte.forEach((g) => { const k = g.scadenza.slice(0, 10); (perGiorno[k] = perGiorno[k] || []).push(g); });
  const celle = [];
  for (let i = 0; i < offset; i++) celle.push(<div key={"v" + i} className="g vuoto" />);
  for (let d = 1; d <= giorniNelMese; d++) {
    const k = `${anno}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    celle.push(
      <div key={k} className={`g ${k === oggi ? "oggi" : ""}`}>
        <span className="n">{d}</span>
        {(perGiorno[k] || []).map((g) => <span key={g.id} className={`ev ${classeSettore(g.settore)}`} title={`${g.titolo} — ${g.ente}`} onClick={() => onApri(g.id)}>{g.titolo}</span>)}
      </div>
    );
  }
  return (
    <>
      <div className="cal-testa"><div className="dow" style={{ flex: 1 }}>{["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"].map((d) => <span key={d}>{d}</span>)}</div></div>
      <div className="cal">{celle}</div>
    </>
  );
}

export function VistaMese({ onApri, settoreIniziale = "" }) {
  const [mese, setMese] = useState(new Date().toISOString().slice(0, 7));
  const [dati, setDati] = useState(null);
  const [vista, setVista] = useState("entrambe");
  const [settore, setSettore] = useState(settoreIniziale);
  useEffect(() => { api.scadenze({ mese }).then(setDati); }, [mese]);
  const sposta = (n) => { const [a, m] = mese.split("-").map(Number); const d = new Date(a, m - 1 + n, 1); setMese(d.toISOString().slice(0, 7)); };
  const nome = new Date(mese + "-01").toLocaleDateString("it-IT", { month: "long", year: "numeric" });
  if (!dati) return <p className="nota">Carico…</p>;
  const filtrati = { cultura: settore && settore !== "Cultura" ? [] : dati.cultura, sociale: settore && settore !== "Sociale" ? [] : dati.sociale, altro: settore ? [] : dati.altro };
  const elenco = [...filtrati.cultura, ...filtrati.sociale, ...filtrati.altro].sort((a, b) => a.scadenza.localeCompare(b.scadenza));
  return (
    <div>
      <div className="cal-testa">
        <div className="azioni" style={{ margin: 0 }}>
          <button className="btn piccolo" onClick={() => sposta(-1)}>‹ mese prec.</button>
          <b style={{ alignSelf: "center", textTransform: "capitalize" }}>{nome}</b>
          <button className="btn piccolo" onClick={() => sposta(1)}>mese succ. ›</button>
        </div>
        <div className="filtri" style={{ margin: 0 }}>
          {[["", "Tutte"], ["Cultura", "Cultura"], ["Sociale", "Sociale"]].map(([v, l]) => <button key={v} aria-pressed={settore === v} onClick={() => setSettore(v)}>{l}</button>)}
          {[["entrambe", "Calendario + elenco"], ["cal", "Calendario"], ["elenco", "Elenco"]].map(([v, l]) => <button key={v} aria-pressed={vista === v} onClick={() => setVista(v)}>{l}</button>)}
        </div>
      </div>
      {vista !== "elenco" && <CalendarioMese mese={mese} dati={filtrati} onApri={onApri} />}
      {vista !== "cal" && (
        <div style={{ marginTop: "1rem" }}>
          {elenco.length === 0 ? <div className="scad-vuoto">Nessuna gara in scadenza in questo mese.</div> : (
            <ul className="scad-lista">
              {elenco.map((g) => (
                <li key={g.id} onClick={() => onApri(g.id)}>
                  <span className="nome"><span className={`settore ${classeSettore(g.settore)}`}>{g.settore}</span> {g.titolo}</span>
                  <span className={`quando urg ${g.urgenza}`}>{giorniLabel(g.giorni_mancanti)}</span>
                  <span className="ente">{g.ente || "ente n.d."}</span>
                  <span className="quando nota">{fmtDataOra(g.scadenza)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export default function Scadenze({ onApri, versione, onCreata, costanti }) {
  const [dati, setDati] = useState({ cultura: [], sociale: [], altro: [] });
  const [mese, setMese] = useState(null); // settore per cui è aperta la vista mensile
  const [over, setOver] = useState(false);
  const [proposta, setProposta] = useState(null);
  const [attesa, setAttesa] = useState(false);
  const [errore, setErrore] = useState(null);
  const inputRef = useRef(null);

  useEffect(() => { api.scadenze({ giorni: 7 }).then(setDati).catch((e) => setErrore(e.message)); }, [versione]);

  async function leggiFile(file) {
    if (!file) return;
    setAttesa(true); setErrore(null);
    try { setProposta(await api.estraiScadenza(file)); }
    catch (e) { setErrore(e.message); } finally { setAttesa(false); }
  }
  const onDrop = (e) => { e.preventDefault(); setOver(false); leggiFile(e.dataTransfer.files?.[0]); };

  return (
    <>
      <div className="riquadro">
        <h2>Gare Cultura in scadenza<button className="link" onClick={() => setMese("Cultura")}>Vedi mese</button></h2>
        <Lista voci={dati.cultura} onApri={onApri} />
      </div>
      <div className="riquadro">
        <h2>Gare Sociale in scadenza<button className="link" onClick={() => setMese("Sociale")}>Vedi mese</button></h2>
        <Lista voci={dati.sociale} onApri={onApri} />
        {dati.altro.length > 0 && <p className="nota" style={{ marginTop: ".5rem" }}>Altre {dati.altro.length} scadenze senza settore: assegna Cultura o Sociale dalla scheda gara.</p>}
      </div>
      <div
        className={`dropzone ${over ? "over" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input ref={inputRef} type="file" accept=".pdf,.docx,.txt" onChange={(e) => leggiFile(e.target.files?.[0])} />
        {attesa ? "Leggo il documento…" : "Trascina qui il PDF di un bando per aggiungerlo al calendario (o clicca per scegliere il file)"}
      </div>
      {errore && <div className="avviso errore">{errore}</div>}

      {mese && (
        <Modale titolo={`Scadenze del mese — ${mese}`} onClose={() => setMese(null)}>
          <VistaMese onApri={(id) => { setMese(null); onApri(id); }} settoreIniziale={mese} />
        </Modale>
      )}
      {proposta && (
        <Modale titolo="Controlla i dati estratti" onClose={() => setProposta(null)}>
          <NuovaGara iniziale={proposta} costanti={costanti} etichetta="Aggiungi al calendario"
            onAnnulla={() => setProposta(null)}
            onCreata={(g) => { setProposta(null); onCreata?.(g); }} />
        </Modale>
      )}
    </>
  );
}
