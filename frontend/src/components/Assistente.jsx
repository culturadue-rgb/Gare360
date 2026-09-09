import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api.js";

export default function Assistente({ salute }) {
  const [chat, setChat] = useState([]);
  const [domanda, setDomanda] = useState("");
  const [attesa, setAttesa] = useState(false);
  const [includi, setIncludi] = useState(true);
  const [modello, setModello] = useState("");
  const [prompt, setPrompt] = useState("");
  const [msg, setMsg] = useState(null);
  const [errore, setErrore] = useState(null);
  const fine = useRef(null);

  useEffect(() => { api.prompt().then((p) => setPrompt(p.testo)).catch(() => {}); }, []);
  useEffect(() => { fine.current?.scrollIntoView({ block: "end" }); }, [chat, attesa]);

  async function invia() {
    const q = domanda.trim();
    if (!q || attesa) return;
    const messaggi = [...chat, { role: "user", content: q }];
    setChat(messaggi); setDomanda(""); setAttesa(true); setErrore(null);
    try {
      const r = await api.chat({ messaggi, includi_contesto: includi, modello: modello || null });
      setChat([...messaggi, { role: "assistant", content: r.risposta }]);
    } catch (e) { setErrore(e.message); setChat(chat); setDomanda(q); }
    finally { setAttesa(false); }
  }

  async function salvaPrompt() {
    setMsg(null); setErrore(null);
    try { await api.salvaPrompt(prompt); setMsg("Prompt salvato."); } catch (e) { setErrore(e.message); }
  }

  return (
    <div>
      <h2>Assistente</h2>
      {salute && !salute.chiave_api_configurata && (
        <div className="avviso info">La chiave API non è configurata sul server: imposta la variabile d'ambiente <code>ANTHROPIC_API_KEY</code> nel backend. Il resto dell'app funziona comunque.</div>
      )}
      <div className="barra-chat">
        <label className="spunta"><input type="checkbox" checked={includi} onChange={(e) => setIncludi(e.target.checked)} /> Passa archivio e tracker come contesto</label>
        <label className="campo"><span>Modello (vuoto = {salute?.modello_default || "default del server"})</span><input type="text" value={modello} onChange={(e) => setModello(e.target.value)} placeholder={salute?.modello_default || ""} /></label>
        <button className="btn piccolo" onClick={() => setChat([])}>Svuota conversazione</button>
      </div>

      <details>
        <summary>Prompt di sistema (placeholder, da completare)</summary>
        <div>
          <textarea rows={10} value={prompt} onChange={(e) => setPrompt(e.target.value)} />
          <div className="azioni"><button className="btn contorno" onClick={salvaPrompt}>Salva prompt</button></div>
          {msg && <div className="avviso">{msg}</div>}
        </div>
      </details>

      <div className="chat" style={{ marginTop: ".8rem" }}>
        {chat.length === 0 && <div className="vuoto">Chiedi allo stratega-gare come impostare la prossima offerta.</div>}
        {chat.map((m, i) => <div key={i} className={`bolla ${m.role}`}>{m.content}</div>)}
        {attesa && <div className="bolla assistant attesa">Sto ragionando…</div>}
        <div ref={fine} />
      </div>
      <div className="chat-input">
        <input type="text" placeholder="Chiedi allo stratega-gare…" value={domanda} onChange={(e) => setDomanda(e.target.value)} onKeyDown={(e) => e.key === "Enter" && invia()} />
        <button className="btn primario" onClick={invia} disabled={attesa || !domanda.trim()}>Invia</button>
      </div>
      {errore && <div className="avviso errore">{errore}</div>}
    </div>
  );
}
