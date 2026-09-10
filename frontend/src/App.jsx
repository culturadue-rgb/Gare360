import { useCallback, useEffect, useState } from "react";
import { api } from "./lib/api.js";
import AssistenteGara from "./components/AssistenteGara.jsx";
import GareInLavorazione from "./components/GareInLavorazione.jsx";
import Scadenze, { VistaMese } from "./components/Scadenze.jsx";
import Simulatore from "./components/Simulatore.jsx";
import Tracker from "./components/Tracker.jsx";
import Archivio from "./components/Archivio.jsx";
import Documenti from "./components/Documenti.jsx";
import Impostazioni from "./components/Impostazioni.jsx";

const SEZIONI = [
  { id: "home", label: "Home" },
  { id: "lavorazione", label: "Gare in lavorazione" },
  { id: "concluse", label: "Gare concluse" },
  { id: "calendario", label: "Calendario" },
  { gruppo: "Archivi" },
  { id: "archivio", label: "Archivio gare" },
  { id: "documenti", label: "Archivio documenti" },
  { gruppo: "Strumenti" },
  { id: "simulatore", label: "Simulatore" },
  { id: "tracker", label: "Tracker rese" },
  { id: "impostazioni", label: "Impostazioni" },
];

export default function App() {
  const [sezione, setSezione] = useState("home");
  const [salute, setSalute] = useState(null);
  const [errore, setErrore] = useState(null);
  const [costanti, setCostanti] = useState(null);
  const [garaId, setGaraId] = useState(null);
  const [elencoGare, setElencoGare] = useState([]);
  const [versione, setVersione] = useState(0);       // incrementa per far ricaricare elenchi e scadenze
  const [modello, setModello] = useState("");
  const [prefill, setPrefill] = useState(null);      // dati per il simulatore dalla gara
  const [apriNuova, setApriNuova] = useState(false);

  useEffect(() => {
    api.health().then(setSalute).catch((e) => setErrore(e.message));
    api.costanti().then(setCostanti).catch(() => {});
  }, []);
  useEffect(() => { api.gare({ concluse: false }).then((r) => setElencoGare(r.gare)).catch(() => {}); }, [versione]);

  const ricarica = useCallback(() => setVersione((v) => v + 1), []);
  const apriGara = useCallback((id) => { setGaraId(id); setSezione("home"); window.scrollTo({ top: 0 }); }, []);
  const garaCorrente = elencoGare.find((g) => g.id === garaId);

  const onSimula = (dati) => { setPrefill({ ...dati }); setSezione("home"); setTimeout(() => document.getElementById("simulatore")?.scrollIntoView({ behavior: "smooth" }), 50); };

  const assistente = (
    <AssistenteGara
      garaId={garaId} onSelezionaGara={setGaraId} elencoGare={elencoGare} costanti={costanti} salute={salute}
      modello={modello} onGaraAggiornata={ricarica} onSimula={onSimula} apriNuova={apriNuova} setApriNuova={setApriNuova}
    />
  );

  const centro = {
    home: (
      <>
        {assistente}
        <GareInLavorazione garaCorrente={garaId} onApri={apriGara} versione={versione} limite={8} />
      </>
    ),
    lavorazione: <GareInLavorazione garaCorrente={garaId} onApri={apriGara} versione={versione} />,
    concluse: <GareInLavorazione concluse garaCorrente={garaId} onApri={apriGara} versione={versione} titolo="Gare concluse" />,
    calendario: <div className="riquadro"><h2>Calendario scadenze</h2><VistaMese onApri={apriGara} /></div>,
    archivio: <Archivio />,
    documenti: <Documenti onApri={apriGara} versione={versione} />,
    simulatore: <Simulatore prefill={prefill} garaTitolo={garaCorrente?.titolo} />,
    tracker: <Tracker />,
    impostazioni: <Impostazioni salute={salute} modello={modello} setModello={setModello} costanti={costanti} />,
  }[sezione];

  return (
    <div className="app">
      <header className="testata">
        <div>
          <h1>Gare360</h1>
          <p>Gare Cultura e Sociale a 360 gradi: documenti, valutazione, scadenze, simulatore.</p>
        </div>
        <div className="stato">
          {errore ? <>Backend non raggiungibile</> : salute ? <>Backend attivo · assistente <b>{salute.chiave_api_configurata ? "pronto" : "senza chiave API"}</b></> : <>Connessione al backend…</>}
        </div>
      </header>

      {errore && <div className="avviso errore">Il backend non risponde ({errore}). Controlla che sia avviato e che <code>VITE_API_URL</code> punti all'indirizzo giusto.</div>}

      <div className="dashboard">
        <nav className="nav" aria-label="Sezioni">
          <button className="btn primario nuova" onClick={() => { setSezione("home"); setApriNuova(true); }}>+ Nuova gara</button>
          {SEZIONI.map((s, i) => s.gruppo
            ? <div key={i} className="gruppo">{s.gruppo}</div>
            : <button key={s.id} aria-current={sezione === s.id} onClick={() => setSezione(s.id)}>{s.label}</button>)}
          {garaCorrente && sezione !== "home" && (
            <>
              <div className="gruppo">Gara aperta</div>
              <button onClick={() => setSezione("home")}>↩ {garaCorrente.titolo}</button>
            </>
          )}
        </nav>

        <main className="col-centro">{centro}</main>

        <aside className="col-destra">
          <Scadenze onApri={apriGara} versione={versione} costanti={costanti} onCreata={(g) => { ricarica(); apriGara(g.id); }} />
          {sezione !== "simulatore" && (
            <div className="riquadro compatto" id="simulatore">
              <h2>Simulatore<small>{garaCorrente ? `gara: ${garaCorrente.titolo}` : "nessuna gara aperta"}</small></h2>
              <Simulatore prefill={prefill} garaTitolo={garaCorrente?.titolo} />
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
