// Tabella modificabile generica: colonne {key, label, type: "text"|"number"|"select", options, min, max, step, width}
export default function GrigliaEdit({ colonne, righe, onChange, nuovaRiga, etichettaAggiungi = "Aggiungi riga" }) {
  const aggiorna = (i, key, val) => {
    const copia = righe.map((r, j) => (j === i ? { ...r, [key]: val } : r));
    onChange(copia);
  };
  const elimina = (i) => onChange(righe.filter((_, j) => j !== i));

  return (
    <div>
      <table className="griglia-edit">
        <thead>
          <tr>
            {colonne.map((c) => <th key={c.key} style={{ width: c.width }}>{c.label}</th>)}
            <th style={{ width: 32 }} />
          </tr>
        </thead>
        <tbody>
          {righe.map((r, i) => (
            <tr key={i}>
              {colonne.map((c) => (
                <td key={c.key}>
                  {c.type === "select" ? (
                    <select value={r[c.key] ?? ""} onChange={(e) => aggiorna(i, c.key, e.target.value)}>
                      {c.options.map((o) => <option key={o} value={o}>{o}</option>)}
                    </select>
                  ) : c.type === "number" ? (
                    <input
                      type="number" min={c.min} max={c.max} step={c.step ?? "any"}
                      value={r[c.key] ?? ""}
                      onChange={(e) => aggiorna(i, c.key, e.target.value === "" ? null : Number(e.target.value))}
                    />
                  ) : (
                    <input type="text" value={r[c.key] ?? ""} onChange={(e) => aggiorna(i, c.key, e.target.value)} />
                  )}
                </td>
              ))}
              <td><button type="button" className="elimina" title="Elimina riga" onClick={() => elimina(i)}>×</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <button type="button" className="btn piccolo" style={{ marginTop: ".4rem" }} onClick={() => onChange([...righe, nuovaRiga()])}>
        {etichettaAggiungi}
      </button>
    </div>
  );
}
