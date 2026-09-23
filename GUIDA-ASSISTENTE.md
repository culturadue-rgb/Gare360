# Guida rapida: assistente AI di Gare360

Promemoria per usare e rimettere in funzione l'assistente. La chiave API non va mai scritta qui né in nessun file del repository.

## Dove sta l'assistente nell'app

- **Creare una gara dai documenti:** menu a sinistra → **+ Nuova gara** → **Compila leggendo bando o disciplinare** → scegli il PDF o il Word. I campi della scheda si compilano da soli.
- **Fare domande su una gara:** menu a sinistra → **Da decidere** o **In lavorazione** → clicca la gara. L'assistente è al centro, con la casella «Domanda su …» in basso. Nello stesso riquadro, in «Documenti della gara», si caricano altri documenti.
- In alto a destra deve comparire «assistente **pronto**».

## Come funziona

| Pezzo | Dove sta | A cosa serve |
|---|---|---|
| Frontend (pagine e pulsanti) | Vercel | Quello che si vede. Il piano gratuito ha un limite di pubblicazioni al giorno. |
| Backend (server) | Render, servizio **Gare360** | Parla con Claude. La chiave va messa qui. |
| Chiave API e credito | console.anthropic.com | Si paga a consumo: circa 0,10–0,25 $ per scheda gara. |

Il limite giornaliero di Vercel blocca solo le modifiche nuove all'app. Non spegne l'assistente.

## Se compare «L'assistente AI è spento» o la chiave viene rifiutata

1. **console.anthropic.com → Billing:** controlla che ci sia credito, altrimenti ricarica.
2. **console.anthropic.com → API Keys → Create Key:** copia la chiave (inizia con `sk-ant-`). Non incollarla in chat, email o file.
3. **dashboard.render.com → Gare360 → Environment → Edit:**
   - KEY: `ANTHROPIC_API_KEY`
   - VALUE: la chiave
   - poi **Save Changes**
4. Se Render non riparte da solo: **Manual Deploy → Deploy latest commit**. Aspetta che compaia «Live».
5. Ricarica l'app e controlla che compaia «assistente pronto».

Per spendere meno, su Render aggiungi `STRATEGA_MODEL` = `claude-sonnet-5`. Il valore predefinito è `claude-opus-5`, più caro.

## Se Vercel dice «Deployment rate limited»

Aspetta 24 ore, poi su vercel.com apri il progetto frontend → **Deployments** → **⋯** sull'ultima riga → **Redeploy**.

## Alternativa senza chiave API

L'**Assistente Gare** su claude.ai usa l'abbonamento Claude, senza chiave e senza costi in più: https://claude.ai/artifact/Lt2Y4Zuu1NsRhLmmSsC6Wm

Carichi i documenti, premi **Compila scheda**, poi **Copia scheda** e incolli il risultato nell'app. Nell'app c'è anche il pulsante **Assistente Gare ↗** nel menu a sinistra.
