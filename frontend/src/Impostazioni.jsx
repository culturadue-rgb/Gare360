import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

export default function Impostazioni({ salute, modello, setModello, costanti }) {
  const [prompt, setPrompt] = useState("");
  const [msg, setMsg] = useState(null);
  const [errore, setErrore] = useState(null);
  useEffect(() => { api.prompt().then((p) => setPrompt(p.testo)).catch(() => {}); }, []);
  async function salva() { setMsg(null); setErrore(null); try { await api.salvaPrompt(prompt); setMsg("Prompt salvato."); } catch (e) { setErrore(e.message); } }
  return (
    <div className="riquadro">
      <h2>Impostazioni</h2>
      <p>Backend: {salute ? "attivo" : "non raggiungibile"} · assistente AI: <b>{salute?.chiave_api_configurata ? "pronto" : "senza chiave (imposta ANTHROPIC_API_KEY sul server)"}</b> · memoria delle gare: {costanti?.memoria_giorni || 15} giorni dall'ultima attività.</p>
      <label className="campo"><span>Modello (vuoto = {salute?.modello_default || "default del server"})</span><input type="text" value={modello} onChange={(e) => setModello(e.target.value)} placeholder={salute?.modello_default || ""} /></label>
      <h3>Prompt di sistema dell'assistente</h3>
      <p className="nota">È la base di ogni risposta; alla gara aperta vengono aggiunti automaticamente tracker, archivio storico e documenti.</p>
      <textarea rows={14} value={prompt} onChange={(e) => setPrompt(e.target.value)} />
      <div className="azioni"><button className="btn primario" onClick={salva}>Salva prompt</button></div>
      {msg && <div className="avviso">{msg}</div>}
      {errore && <div className="avviso errore">{errore}</div>}
    </div>
  );
}
