# Stratega Gare

App in Python (Streamlit) con tre aree:

1. **Simulatore deterministico** — configuri la gara (ripartizione tecnico/economico, criteri, formula prezzo, sbarramento, riparametrazione), il tuo ribasso e i profili dei concorrenti. Il punteggio tecnico atteso viene letto dal **tracker** (resa storica per criterio). Output: graduatoria, distacco, ribasso minimo per vincere e punti tecnici mancanti. Stessi input → stesso risultato, sempre.
2. **Tracker** — `data/tracker.csv`, una riga per criterio (`criterio,tipo,resa,n,note`), **compilato da te**: griglia modificabile nell'app, editor testo, oppure Excel. La resa (0–1) è la frazione dei punti massimi che prendete di solito su quel criterio. L'archivio storico non lo modifica.
3. **Archivio storico** — le schede gara in `data/storico-gare.md` (stesso formato del template del progetto). Puoi aggiungere schede dal modulo o modificare il file a mano.
4. **Assistente AI** — chat con prompt di sistema in `prompts/stratega_gare.md` (per ora placeholder, modificabile dall'app). Archivio e tracker vengono passati come contesto.

## Avvio

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...   # solo per l'assistente; in alternativa inseriscila nella sidebar
streamlit run app.py
```

## Struttura

```
app.py            interfaccia (tab: Simulatore / Tracker / Archivio / Assistente)
simulator.py      motore deterministico
tracker.py        lettura/scrittura di tracker.csv
archive.py        lettura/scrittura schede markdown
chatbot.py        chiamata al modello + composizione del contesto
prompts/          prompt di sistema (placeholder)
data/             storico-gare.md, tracker.csv
.streamlit/       tema (verde lime + blu)
```

## Formule prezzo supportate
- **Lineare / proporzionale**: P = Pmax × R / Rmax
- **Bilineare** (a due rette, coefficiente X 0,80/0,85/0,90): soglia = X × media ribassi; sotto soglia proporzionale, sopra soglia interpolazione fino a Pmax.

Se una gara usa una formula diversa, aggiungila in `simulator.punteggio_economico`.
