import { useEffect, useState } from "react";
import { auth, verificaPassword } from "../lib/api.js";

/**
 * Schermata di accesso.
 *
 * L'app è protetta da un'unica password condivisa, impostata sul server nella
 * variabile d'ambiente APP_PASSWORD. Qui la si inserisce una volta: resta nella
 * scheda del browser finché non la si chiude, e viaggia a ogni richiesta.
 *
 * `onEntrato` viene chiamata quando la password è stata accettata dal backend.
 */
export default function Accesso({ onEntrato }) {
  const [password, setPassword] = useState("");
  const [errore, setErrore] = useState(null);
  const [verificaInCorso, setVerificaInCorso] = useState(false);

  // Se la password è già in sessione (es. dopo un ricaricamento della pagina)
  // la riproviamo da soli, senza far ridigitare nulla.
  useEffect(() => {
    const salvata = auth.leggi();
    if (!salvata) return;
    let annullato = false;
    verificaPassword(salvata).then((r) => {
      if (annullato) return;
      if (r.ok) onEntrato();
      else auth.cancella();
    });
    return () => { annullato = true; };
  }, [onEntrato]);

  async function invia(e) {
    e.preventDefault();
    const pw = password.trim();
    if (!pw) { setErrore("Inserisci la password."); return; }

    setVerificaInCorso(true);
    setErrore(null);
    try {
      const esito = await verificaPassword(pw);
      if (esito.ok) {
        auth.salva(pw);
        onEntrato();
      } else {
        setErrore(esito.messaggio);
      }
    } catch (err) {
      setErrore(
        "Non riesco a contattare il server. Controlla che sia acceso e che " +
        "l'indirizzo configurato in VITE_API_URL sia quello giusto. (" + err.message + ")"
      );
    } finally {
      setVerificaInCorso(false);
    }
  }

  return (
    <div className="accesso">
      <form className="accesso-riquadro" onSubmit={invia}>
        <h1>Gare360</h1>
        <p className="nota">
          Gare Cultura e Sociale a 360 gradi. Per entrare serve la password condivisa.
        </p>

        <label className="campo">
          <span>Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoFocus
            autoComplete="current-password"
            disabled={verificaInCorso}
          />
        </label>

        {errore && <div className="avviso errore">{errore}</div>}

        <button className="btn primario" type="submit" disabled={verificaInCorso}>
          {verificaInCorso ? "Verifica…" : "Entra"}
        </button>

        <p className="nota piccola">
          La password resta in questa scheda del browser e si cancella quando la chiudi.
        </p>
      </form>
    </div>
  );
}
