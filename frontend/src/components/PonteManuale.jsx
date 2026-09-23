import { useState } from "react";

/**
 * Il ponte manuale: fare a mano quello che farebbe l'AI, senza chiave API.
 *
 * Le chiavi API si pagano a consumo. Chi non ne ha una resterebbe senza le
 * funzioni che usano l'AI — ma un abbonamento a Claude sul sito c'è già, e
 * l'unica differenza è chi preme il pulsante. Quindi: l'app prepara il testo,
 * la persona lo incolla su claude.ai, e riporta indietro la risposta. Il
 * risultato finisce esattamente dove sarebbe finito comunque.
 *
 * `carica`  → funzione che restituisce { testo, avviso }
 * `salva`   → funzione che riceve la risposta incollata
 * `esito`   → cosa mostrare dopo aver salvato (facoltativo)
 */
export default function PonteManuale({ titolo, descrizione, carica, salva,
                                      etichettaSalva = "Usa questa risposta",
                                      etichettaPrepara = "1. Prepara il testo da copiare",
                                      attivo = true }) {
  const [aperto, setAperto] = useState(false);
  const [testo, setTesto] = useState("");
  const [avviso, setAvviso] = useState("");
  const [risposta, setRisposta] = useState("");
  const [copiato, setCopiato] = useState(false);
  const [occupato, setOccupato] = useState(false);
  const [errore, setErrore] = useState("");

  async function prepara() {
    setOccupato(true); setErrore(""); setCopiato(false);
    try {
      const r = await carica();
      // Se non c'è niente da copiare non si aprono i passi 2 e 3: mostrerebbero
      // una casella vuota da incollare e un pulsante che non porta da nessuna
      // parte. Si dice solo cosa manca.
      if (!r.testo) {
        setErrore(r.avviso || "Non c'è niente da preparare.");
        setAperto(false);
        return;
      }
      setTesto(r.testo);
      setAvviso(r.avviso || "");
      setAperto(true);
    } catch (e) {
      setErrore(e.message);
    } finally {
      setOccupato(false);
    }
  }

  async function copia() {
    try {
      await navigator.clipboard.writeText(testo);
      setCopiato(true);
    } catch {
      // Alcuni browser non danno accesso agli appunti: si dice di copiare a mano
      // invece di fallire in silenzio.
      setErrore("Il browser non mi lascia copiare da solo: seleziona il testo qui sotto e copialo a mano (Ctrl+A, poi Ctrl+C).");
    }
  }

  async function usa() {
    if (!risposta.trim()) { setErrore("Incolla prima la risposta."); return; }
    setOccupato(true); setErrore("");
    try {
      await salva(risposta.trim());
      setRisposta(""); setAperto(false); setTesto("");
    } catch (e) {
      setErrore(e.message);
    } finally {
      setOccupato(false);
    }
  }

  return (
    <div className="ponte">
      <h4>{titolo}</h4>
      {descrizione && <p className="nota">{descrizione}</p>}

      {!aperto && (
        <button className="btn contorno" onClick={prepara} disabled={occupato || !attivo}>
          {occupato ? "Preparo…" : etichettaPrepara}
        </button>
      )}

      {aperto && (
        <>
          {avviso && <p className="avviso attenzione">{avviso}</p>}
          <p className="nota">
            <b>2.</b> Copia il testo qui sotto e incollalo in una nuova conversazione su{" "}
            <a href="https://claude.ai/new" target="_blank" rel="noreferrer">claude.ai</a>.
          </p>
          <p>
            <button className="btn primario piccolo" onClick={copia}>
              {copiato ? "Copiato ✓" : "Copia il testo"}
            </button>{" "}
            <span className="nota">{testo.length.toLocaleString("it-IT")} caratteri</span>
          </p>
          <textarea className="ponte-testo" value={testo} readOnly rows={8}
                    onFocus={(e) => e.target.select()} />

          <p className="nota"><b>3.</b> Incolla qui sotto la risposta di Claude.</p>
          <textarea rows={6} value={risposta} placeholder="Incolla qui la risposta…"
                    onChange={(e) => setRisposta(e.target.value)} />
          <p>
            <button className="btn primario" onClick={usa} disabled={occupato || !risposta.trim()}>
              {occupato ? "Salvo…" : etichettaSalva}
            </button>{" "}
            <button className="btn contorno piccolo" onClick={() => { setAperto(false); setErrore(""); }}>
              Annulla
            </button>
          </p>
        </>
      )}

      {errore && <p className="avviso errore">{errore}</p>}
    </div>
  );
}
