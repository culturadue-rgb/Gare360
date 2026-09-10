export default function Modale({ titolo, onClose, children }) {
  return (
    <div className="modale-sfondo" onClick={onClose}>
      <div className="modale" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <h2>{titolo}<button className="chiudi" aria-label="Chiudi" onClick={onClose}>×</button></h2>
        {children}
      </div>
    </div>
  );
}
