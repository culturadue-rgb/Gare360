import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { classeSettore, fmtDataOra } from "../lib/util.js";

export default function Documenti({ onApri, versione }) {
  const [docs, setDocs] = useState([]);
  const [filtro, setFiltro] = useState("");
  useEffect(() => { api.documenti().then((r) => setDocs(r.documenti)); }, [versione]);
  const mostrati = docs.filter((d) => !filtro || d.settore === filtro);
  return (
    <div className="riquadro">
      <h2>Archivio documenti<small>{docs.length} file in {new Set(docs.map((d) => d.gara_id)).size} gare</small></h2>
      <div className="filtri">{[["", "Tutti"], ["Cultura", "Cultura"], ["Sociale", "Sociale"]].map(([v, l]) => <button key={v} aria-pressed={filtro === v} onClick={() => setFiltro(v)}>{l}</button>)}</div>
      {mostrati.length === 0 ? <div className="vuoto">Nessun documento. Si caricano dalla scheda di ogni gara.</div> : (
        <table>
          <thead><tr><th>Documento</th><th>Categoria</th><th>Gara</th><th>Caricato</th></tr></thead>
          <tbody>
            {mostrati.map((d) => (
              <tr key={d.id}>
                <td>{d.nome}</td><td>{d.categoria}</td>
                <td><button className="link" onClick={() => onApri(d.gara_id)}><span className={`settore ${classeSettore(d.settore)}`}>{d.settore}</span> {d.gara_titolo}</button></td>
                <td>{fmtDataOra(d.caricato)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
