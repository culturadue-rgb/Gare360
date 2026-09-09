import { useEffect, useState } from "react";
import { api } from "./lib/api.js";
import Simulatore from "./components/Simulatore.jsx";
import Tracker from "./components/Tracker.jsx";
import Archivio from "./components/Archivio.jsx";
import Assistente from "./components/Assistente.jsx";

const TABS = [
  { id: "sim", label: "Simulatore", el: Simulatore },
  { id: "trk", label: "Tracker", el: Tracker },
  { id: "arc", label: "Archivio storico", el: Archivio },
  { id: "ast", label: "Assistente", el: Assistente },
];

export default function App() {
  const [tab, setTab] = useState("sim");
  const [salute, setSalute] = useState(null);
  const [errore, setErrore] = useState(null);

  useEffect(() => {
    api.health().then(setSalute).catch((e) => setErrore(e.message));
  }, []);

  const Corrente = TABS.find((t) => t.id === tab).el;

  return (
    <div className="app">
      <header className="testata">
        <div>
          <h1>Alloro</h1>
          <p>Il verbale, prima del verbale. Simula il punteggio, tieni il tracker, archivia le gare, chiedi consiglio.</p>
        </div>
        <div className="stato">
          {errore
            ? <>Backend non raggiungibile</>
            : salute
              ? <>Backend attivo · assistente <b>{salute.chiave_api_configurata ? "pronto" : "senza chiave API"}</b></>
              : <>Connessione al backend…</>}
        </div>
      </header>

      {errore && (
        <div className="avviso errore">
          Il backend non risponde ({errore}). Controlla che sia avviato e che <code>VITE_API_URL</code> punti all'indirizzo giusto.
        </div>
      )}

      <nav className="tabs" role="tablist">
        {TABS.map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </nav>

      <section className="pannello" role="tabpanel">
        <Corrente salute={salute} />
      </section>
    </div>
  );
}
