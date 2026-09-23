import { useCallback, useEffect, useState } from "react";
import { api, auth } from "./lib/api.js";
import Accesso from "./components/Accesso.jsx";
import SchedaGara from "./components/SchedaGara.jsx";
import AssistenteGara from "./components/AssistenteGara.jsx";
import GareInLavorazione from "./components/GareInLavorazione.jsx";
import Calendario from "./components/Calendario.jsx";
import Simulatore from "./components/Simulatore.jsx";
import Archivio from "./components/Archivio.jsx";
import Impostazioni from "./components/Impostazioni.jsx";

// Il menu segue il flusso di una gara, dall'alto in basso:
//   Da decidere -> In lavorazione -> Conclusa -> Archiviata
// Gli archivi stanno sotto, le impostazioni in fondo.
// Il Tracker non c'e' piu'; i documenti stanno dentro la scheda di ogni gara,
// quindi non serve piu' nemmeno un "Archivio documenti" separato.
const SEZIONI = [
  { id: "home", label: "Home" },
  { id: "da-decidere", label: "Da decidere", stato: "Da decidere" },
  { id: "lavorazione", label: "In lavorazione", stato: "In lavorazione" },
  { id: "concluse", label: "Concluse", stato: "Conclusa" },
  { gruppo: "Archivio" },
  { id: "arch-sociale", label: "Sociale", archivio: "Sociale" },
  { id: "arch-cultura", label: "Cultura", archivio: "Cultura" },
  { id: "arch-educativi", label: "Servizi educativi", archivio: "Servizi_educativi" },
  { id: "arch-ccnl", label: "CCNL", archivio: "CCNL" },
  { id: "impostazioni", label: "Impostazioni", piccolo: true },
];

export default function App() {
  // Se il server non chiede la password (caso normale) si entra subito, senza
  // alcuna schermata. La richiesta compare solo quando APP_PASSWORD è
  // impostata su Render.
  const [entrato, setEntrato] = useState(false);
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

  // Se il backend rifiuta la password (scaduta, cambiata) si torna all'accesso.
  useEffect(() => {
    const suAccessoNegato = () => { setEntrato(false); setErrore(null); };
    window.addEventListener("gare360:accesso-negato", suAccessoNegato);
    return () => window.removeEventListener("gare360:accesso-negato", suAccessoNegato);
  }, []);

  // Primo contatto col backend: /api/health è sempre libera e dice anche se la
  // password è accesa. Se è spenta si entra dritti.
  useEffect(() => {
    api.health()
      .then((s) => { setSalute(s); if (!s.password_configurata) setEntrato(true); })
      .catch((e) => setErrore(e.message));
  }, []);

  useEffect(() => {
    if (!entrato) return;
    api.costanti().then(setCostanti).catch(() => {});
  }, [entrato]);
  useEffect(() => {
    if (!entrato) return;
    api.gare({ concluse: false }).then((r) => setElencoGare(r.gare)).catch(() => {});
  }, [versione, entrato]);

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

  const voce = SEZIONI.find((s) => s.id === sezione);

  const centro = voce?.stato ? (
    <GareInLavorazione
      stato={voce.stato} titolo={voce.label} garaCorrente={garaId}
      onApri={apriGara} versione={versione}
    />
  ) : voce?.archivio === "CCNL" ? (
    <div className="riquadro">
      <h2>Archivio CCNL</h2>
      <p className="nota">
        Qui andranno i contratti collettivi (Multiservizi, Cooperative sociali,
        Federculture) con la ricerca che cita documento e pagina. Non è ancora
        attivo.
      </p>
    </div>
  ) : voce?.archivio ? (
    <Archivio archivio={voce.archivio} />
  ) : sezione === "impostazioni" ? (
    <Impostazioni salute={salute} modello={modello} setModello={setModello} costanti={costanti} />
  ) : garaId ? (
    // Con una gara aperta la colonna centrale è il suo assistente.
    <>
      {assistente}
      <GareInLavorazione garaCorrente={garaId} onApri={apriGara} versione={versione} limite={6} />
    </>
  ) : (
    // Senza gara aperta la Home è il posto dove se ne crea una.
    <>
      <SchedaGara onCreata={(g) => { ricarica(); apriGara(g.id); }} />
      <GareInLavorazione garaCorrente={garaId} onApri={apriGara} versione={versione} limite={6} />
    </>
  );

  if (!entrato) {
    // Il backend non risponde: senza sapere se serve la password non si può
    // procedere, quindi si spiega il problema invece di mostrare un form inutile.
    if (errore && !salute) {
      return (
        <div className="accesso">
          <div className="accesso-riquadro">
            <h1>Gare360</h1>
            <div className="avviso errore">
              Il backend non risponde ({errore}). Controlla che il servizio su Render sia
              acceso e che <code>VITE_API_URL</code> punti al suo indirizzo.
            </div>
          </div>
        </div>
      );
    }
    if (!salute) return <div className="accesso"><div className="accesso-riquadro"><h1>Gare360</h1><p className="nota">Connessione al backend…</p></div></div>;
    return <Accesso onEntrato={() => setEntrato(true)} />;
  }

  return (
    <div className="app">
      <header className="testata">
        <div>
          <h1>Gare360</h1>
          <p>Gare Cultura e Sociale a 360 gradi: documenti, valutazione, scadenze, simulatore.</p>
        </div>
        <div className="stato">
          {errore ? <>Backend non raggiungibile</> : salute ? <>Backend attivo · assistente <b>{salute.chiave_api_configurata ? "pronto" : "senza chiave API"}</b></> : <>Connessione al backend…</>}
          {salute?.password_configurata && (
            <button className="btn esci" onClick={() => { auth.cancella(); setEntrato(false); }}>Esci</button>
          )}
        </div>
      </header>

      {errore && <div className="avviso errore">Il backend non risponde ({errore}). Controlla che sia avviato e che <code>VITE_API_URL</code> punti all'indirizzo giusto.</div>}

      <div className="dashboard">
        <nav className="nav" aria-label="Sezioni">
          <button className="btn primario nuova" onClick={() => { setGaraId(null); setSezione("home"); }}>+ Nuova gara</button>
          {SEZIONI.map((s, i) => s.gruppo
            ? <div key={i} className="gruppo">{s.gruppo}</div>
            : <button key={s.id} className={s.piccolo ? "voce-piccola" : undefined}
                      aria-current={sezione === s.id} onClick={() => setSezione(s.id)}>{s.label}</button>)}
          {garaCorrente && sezione !== "home" && (
            <>
              <div className="gruppo">Gara aperta</div>
              <button onClick={() => setSezione("home")}>↩ {garaCorrente.titolo}</button>
            </>
          )}
        </nav>

        <main className="col-centro">{centro}</main>

        <aside className="col-destra">
          <Calendario onApri={apriGara} versione={versione} />
          {(
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
