/**
 * La memoria di riserva, nel browser.
 *
 * PERCHÉ ESISTE
 * Sul piano gratuito di Render il server non ha un disco: si spegne dopo un
 * quarto d'ora di inattività e riparte pulito. Chiudi l'app, torni il giorno
 * dopo, e l'archivio che avevi caricato non c'è più.
 *
 * Finché è così, la copia deve stare da qualche parte che non si svuota. Il
 * browser è l'unico posto disponibile senza chiedere all'utente di configurare
 * niente e senza far pagare niente.
 *
 * COSA TIENE E COSA NO
 * Tiene archivio, gare, schede, analisi, calendario, indice dei CCNL e il testo
 * già estratto dai PDF. NON tiene i PDF originali: sono troppo grandi per il
 * browser. Si perde la possibilità di riscaricare l'originale, non il suo
 * contenuto — la consultazione dei CCNL e il contesto delle gare continuano a
 * funzionare.
 *
 * LIMITI, DETTI CHIARAMENTE
 * È legata a QUESTO browser su QUESTO computer: da un altro non si vede. E se
 * si cancellano i dati di navigazione sparisce. Per una copia che non dipende da
 * niente c'è «Salva tutto» in Impostazioni, che scarica un file.
 */

const CHIAVE = "gare360_memoria";

export function leggi() {
  try {
    const grezzo = localStorage.getItem(CHIAVE);
    return grezzo ? JSON.parse(grezzo) : null;
  } catch {
    // Spazio pieno, modalità in incognito, dati bloccati: non è un motivo per
    // impedire di usare l'app, solo per non avere la rete di sicurezza.
    return null;
  }
}

export function scrivi(salvataggio) {
  try {
    localStorage.setItem(CHIAVE, JSON.stringify(salvataggio));
    return { ok: true, byte: salvataggio?.byte || 0, quando: salvataggio?.quando };
  } catch (e) {
    return { ok: false, motivo: e?.name === "QuotaExceededError"
      ? "Non c'è più spazio nel browser per la copia di sicurezza: usa «Salva tutto» e scarica il file."
      : "Il browser non permette di tenere la copia di sicurezza (navigazione in incognito?): usa «Salva tutto»." };
  }
}

export function cancella() {
  try { localStorage.removeItem(CHIAVE); } catch { /* niente da fare */ }
}

export function quando() {
  return leggi()?.quando || null;
}
