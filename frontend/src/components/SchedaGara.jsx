import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api.js";
import PonteManuale from "./PonteManuale.jsx";

/**
 * Scheda di rilevazione di una nuova gara.
 *
 * Due modi di compilarla, e si possono mescolare:
 *   - a mano, campo per campo;
 *   - caricando bando o disciplinare e lasciando che l'AI proponga i valori,
 *     che restano tutti correggibili prima di salvare.
 *
 * Il modulo non è scritto qui: arriva da /api/scheda/campi, così aggiungere un
 * campo significa toccare solo il backend.
 *
 * Salvando, la gara nasce nello stato "Da decidere".
 */

const RIGA_CRITERIO = () => ({ codice: "", criterio: "", sub_criterio: "", tipo: "qualitativo", punti_max: "", note: "" });

function Campo({ campo, valore, onChange }) {
  const comune = {
    value: valore ?? "",
    onChange: (e) => onChange(campo.id, e.target.value),
  };
  return (
    <label className="campo">
      <span>
        {campo.etichetta}{campo.obbligatorio && " *"}
        {campo.aiuto && <em className="nota piccola"> · {campo.aiuto}</em>}
      </span>
      {campo.tipo === "testo_lungo" ? <textarea rows={3} {...comune} />
        : campo.tipo === "scelta" ? (
          <select {...comune}>
            <option value="">—</option>
            {campo.opzioni.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        )
        : <input type={campo.tipo === "data" ? "date" : campo.tipo === "ora" ? "time" : campo.tipo === "numero" ? "number" : "text"} {...comune} />}
    </label>
  );
}

export default function SchedaGara({ onCreata, salute }) {
  // Senza chiave valida il pulsante automatico non puo' funzionare: spegnerlo e
  // dire dove andare vale piu' che lasciarlo premere per vederlo fallire.
  const senzaChiave = !salute?.chiave_api_configurata;
  const [def, setDef] = useState(null);
  const [titolo, setTitolo] = useState("");
  const [scheda, setScheda] = useState({});
  const [criteri, setCriteri] = useState({ elenco: [RIGA_CRITERIO()] });
  const [avvisi, setAvvisi] = useState([]);
  const [somma, setSomma] = useState(0);
  const [origine, setOrigine] = useState(null);
  const [estraendo, setEstraendo] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [errore, setErrore] = useState(null);
  const fileRef = useRef(null);
  const filePonteRef = useRef(null);
  const [filePonte, setFilePonte] = useState(null);

  useEffect(() => { api.schedaCampi().then(setDef).catch((e) => setErrore(e.message)); }, []);

  // Gli avvisi sui punteggi si aggiornano mentre si scrive, senza tempestare
  // il server: si aspetta mezzo secondo di pausa.
  useEffect(() => {
    const t = setTimeout(() => {
      api.controllaCriteri(criteri)
        .then((r) => { setAvvisi(r.avvisi); setSomma(r.somma_criteri); })
        .catch(() => {});
    }, 500);
    return () => clearTimeout(t);
  }, [criteri]);

  const setCampo = (id, v) => setScheda((s) => ({ ...s, [id]: v }));
  const setCriterio = (id, v) => setCriteri((c) => ({ ...c, [id]: v }));

  function setRiga(i, chiave, valore) {
    setCriteri((c) => {
      const elenco = c.elenco.map((r, j) => (j === i ? { ...r, [chiave]: valore } : r));
      return { ...c, elenco };
    });
  }

  async function estrai(file) {
    if (!file) return;
    setEstraendo(true); setErrore(null);
    try {
      const r = await api.estraiScheda(file);
      setTitolo(r.titolo || titolo);
      setScheda((s) => ({ ...s, ...r.scheda }));
      setCriteri({ ...r.criteri, elenco: r.criteri.elenco?.length ? r.criteri.elenco : [RIGA_CRITERIO()] });
      setOrigine({ file: r.nome_file, caratteri: r.caratteri_letti });
    } catch (e) { setErrore(e.message); }
    finally { setEstraendo(false); if (fileRef.current) fileRef.current.value = ""; }
  }

  async function salva() {
    if (!titolo.trim()) { setErrore("Serve almeno il nome della gara."); return; }
    setSalvando(true); setErrore(null);
    try {
      const data = scheda.scadenza_offerte;
      const ora = scheda.ora_scadenza_offerte || "23:59";
      const creata = await api.creaGara({
        titolo: titolo.trim(),
        ente: scheda.ente || "",
        settore: scheda.settore || "Altro",
        scadenza: data ? `${data}T${ora}` : null,
        note: scheda.note || "",
        base_asta: scheda.base_asta ? Number(String(scheda.base_asta).replace(",", ".")) : null,
        scheda, criteri,
      });
      setTitolo(""); setScheda({}); setCriteri({ elenco: [RIGA_CRITERIO()] }); setOrigine(null);
      onCreata?.(creata);
    } catch (e) { setErrore(e.message); }
    finally { setSalvando(false); }
  }

  if (!def) return <div className="riquadro"><h2>Scheda nuova gara</h2><p className="nota">Carico il modulo…</p></div>;

  return (
    <div className="riquadro">
      <h2>Scheda nuova gara</h2>

      <div className="estrazione">
        <input ref={fileRef} type="file" accept=".pdf,.docx,.doc" style={{ display: "none" }}
               onChange={(e) => estrai(e.target.files?.[0])} />
        <button className="btn" disabled={estraendo || senzaChiave} onClick={() => fileRef.current?.click()}>
          {estraendo ? "Leggo il documento…" : "Compila leggendo bando o disciplinare"}
        </button>
        <span className="nota">
          {senzaChiave
            ? "il server non ha una chiave API valida: compila a mano qui sotto, o usa il riquadro tratteggiato"
            : "oppure compila a mano qui sotto"}
        </span>
      </div>

      {/* Senza chiave API il pulsante qui sopra non funziona. Il documento però
          l'app lo sa leggere lo stesso: prepara istruzioni e testo, si incollano
          su claude.ai e si riporta indietro l'elenco «campo: valore». */}
      <p className="nota">
        Documento da leggere:{" "}
        <input ref={filePonteRef} type="file" accept=".pdf,.docx,.doc,.txt"
               onChange={(e) => setFilePonte(e.target.files?.[0] || null)} />
      </p>
      <PonteManuale
        titolo="Oppure: fatti compilare la scheda a mano su claude.ai"
        descrizione="Serve se il server non ha una chiave API a pagamento. Scegli il documento: l'app ne estrae il testo e prepara la richiesta con l'elenco esatto dei campi. Incollala su claude.ai, poi riporta qui la risposta. I campi arrivano nel modulo qui sotto, sempre correggibili."
        etichettaPrepara={filePonte ? `Prepara il testo da «${filePonte.name}»` : "Scegli prima un documento"}
        attivo={!!filePonte}
        carica={() => api.testoScheda(filePonte)}
        salva={async (testo) => {
          const r = await api.incollaScheda(testo);
          setTitolo(r.titolo || titolo);
          setScheda((s2) => ({ ...s2, ...r.scheda }));
          if (r.criteri?.elenco?.length) setCriteri({ ...r.criteri, elenco: r.criteri.elenco });
          setOrigine({ file: filePonte?.name || "risposta incollata", caratteri: r.campi_compilati,
                       manuale: true, scartate: r.non_riconosciute || [] });
        }}
        etichettaSalva="Metti i campi nel modulo"
      />

      {origine && (
        <div className="avviso">
          {origine.manuale ? (
            <>
              Dalla risposta incollata sono stati riconosciuti <b>{origine.caratteri}</b> campi.
              <b> Controllali tutti prima di salvare</b>: quello che non è stato trovato è rimasto
              vuoto, non indovinato.
              {origine.scartate?.length > 0 && (
                <>
                  {" "}Queste righe non corrispondono a nessun campo e sono state lasciate fuori —
                  se servono, riportale a mano:
                  <ul>{origine.scartate.map((r, i) => <li key={i}><code>{r}</code></li>)}</ul>
                </>
              )}
            </>
          ) : (
            <>
              Campi proposti leggendo <b>{origine.file}</b> ({origine.caratteri.toLocaleString("it-IT")} caratteri).
              <b> Controllali tutti prima di salvare</b>: quello che l'AI non ha trovato è rimasto vuoto,
              non indovinato.
            </>
          )}
        </div>
      )}

      <label className="campo">
        <span>Nome della gara *</span>
        <input type="text" value={titolo} onChange={(e) => setTitolo(e.target.value)}
               placeholder="es. Biblioteca comunale di Salzano" />
      </label>

      {def.sezioni.map((s) => (
        <details key={s.id} className="sezione-scheda" open={s.id === "anagrafica"}>
          <summary>{s.titolo}</summary>
          {s.aiuto && <p className="nota">{s.aiuto}</p>}
          <div className="griglia-campi">
            {s.campi.map((c) => <Campo key={c.id} campo={c} valore={scheda[c.id]} onChange={setCampo} />)}
          </div>
        </details>
      ))}

      <details className="sezione-scheda" open>
        <summary>Come si assegnano i punteggi</summary>
        <p className="nota">
          È la parte che alimenta il simulatore. Se la formula del disciplinare non
          rientra fra quelle previste, scegli «Altra formula» e trascrivila:
          il simulatore non la approssima, te lo segnala.
        </p>
        <div className="griglia-campi">
          {def.campi_criteri.map((c) => (
            <Campo key={c.id} campo={c} valore={criteri[c.id]} onChange={setCriterio} />
          ))}
        </div>

        <h4>Criteri e sub-criteri <small>{somma ? `${somma} punti in totale` : ""}</small></h4>
        <div className="tabella-scorrevole">
          <table className="tabella-archivio">
            <thead>
              <tr><th>Cod.</th><th>Criterio</th><th>Sub-criterio</th><th>Tipo</th><th>Punti max</th><th>Note</th><th /></tr>
            </thead>
            <tbody>
              {criteri.elenco.map((r, i) => (
                <tr key={i}>
                  <td><input style={{ width: "3.5rem" }} value={r.codice} onChange={(e) => setRiga(i, "codice", e.target.value)} /></td>
                  <td><input value={r.criterio} onChange={(e) => setRiga(i, "criterio", e.target.value)} /></td>
                  <td><input value={r.sub_criterio} onChange={(e) => setRiga(i, "sub_criterio", e.target.value)} /></td>
                  <td>
                    <select value={r.tipo} onChange={(e) => setRiga(i, "tipo", e.target.value)}>
                      {def.tipi_criterio.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </td>
                  <td><input style={{ width: "5rem" }} value={r.punti_max} onChange={(e) => setRiga(i, "punti_max", e.target.value)} /></td>
                  <td><input value={r.note} onChange={(e) => setRiga(i, "note", e.target.value)} /></td>
                  <td>
                    <button className="btn piccolo" title="Togli questa riga"
                            onClick={() => setCriteri((c) => ({ ...c, elenco: c.elenco.filter((_, j) => j !== i) }))}>×</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="azioni">
          <button className="btn" onClick={() => setCriteri((c) => ({ ...c, elenco: [...c.elenco, RIGA_CRITERIO()] }))}>
            Aggiungi criterio
          </button>
        </div>
      </details>

      {avvisi.map((a, i) => <div key={i} className="avviso attenzione">{a}</div>)}
      {errore && <div className="avviso errore">{errore}</div>}

      <div className="azioni">
        <button className="btn primario" disabled={salvando} onClick={salva}>
          {salvando ? "Salvo…" : "Salva la gara"}
        </button>
        <span className="nota">nascerà nello stato «Da decidere»</span>
      </div>
    </div>
  );
}
