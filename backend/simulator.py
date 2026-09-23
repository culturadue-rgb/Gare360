"""
Simulatore deterministico di gara (OEPV).

Nessuna casualità: dati gli stessi input (configurazione di gara, rese storiche,
ribassi dei concorrenti) restituisce sempre lo stesso risultato.

Flusso:
  1. Per ogni criterio tecnico, il punteggio atteso = punti max × resa storica
     letta dallo storico (se il criterio non c'è si usa una resa di default).
     NOTA: la fonte delle rese diventeranno gli archivi nella Fase 4; qui la
     struttura è già quella, basta passarle.
  2. Il punteggio economico si calcola con la formula scelta (interpolazione lineare,
     proporzionale inversa, o bilineare con soglia — le tre più diffuse nei disciplinari).
  3. I concorrenti sono "profili" deterministici: livello tecnico (frazione del max)
     + ribasso offerto.
  4. Output: graduatoria, distacchi, e analisi di sensibilità (ribasso minimo per
     vincere, punti tecnici mancanti).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Modelli
# ---------------------------------------------------------------------------

@dataclass
class Criterio:
    nome: str
    tipo: str              # "tabellare" | "qualitativo"
    punti_max: float
    resa_override: Optional[float] = None  # 0..1, se impostata scavalca lo storico


@dataclass
class Concorrente:
    nome: str
    livello_tecnico: float   # 0..1 frazione dei punti tecnici massimi
    ribasso: float           # percentuale, es. 12.5


@dataclass
class ConfigGara:
    nome: str
    base_asta: float
    punti_tecnico: float
    punti_economico: float
    criteri: list[Criterio]
    formula_prezzo: str = "lineare"     # "lineare" | "proporzionale" | "bilineare"
    coeff_bilineare: float = 0.85       # X della formula bilineare (0.80 / 0.85 / 0.90)
    soglia_sbarramento: Optional[float] = None  # punti tecnici minimi, None = assente
    riparametrazione: bool = False      # riporta il miglior tecnico al max
    formula_testo: str = ""             # la formula come scritta nel disciplinare


@dataclass
class RisultatoOfferente:
    nome: str
    tecnico: float
    economico: float
    ribasso: float
    escluso: bool = False
    dettaglio_criteri: dict = field(default_factory=dict)

    @property
    def totale(self) -> float:
        return 0.0 if self.escluso else round(self.tecnico + self.economico, 3)


# ---------------------------------------------------------------------------
# Punteggio tecnico
# ---------------------------------------------------------------------------

RESA_DEFAULT = {"tabellare": 0.80, "qualitativo": 0.65}


def punteggio_tecnico_nostro(cfg: ConfigGara, resa_storica: dict) -> tuple[float, dict]:
    """Somma dei punti attesi per criterio. Restituisce (totale, dettaglio)."""
    dettaglio = {}
    totale = 0.0
    stats = resa_storica.get("criteri", {})
    for c in cfg.criteri:
        if c.resa_override is not None:
            resa, fonte = c.resa_override, "manuale"
        else:
            key = normalizza(c.nome)
            if key in stats and stats[key].get("n", 0) > 0:
                resa, fonte = stats[key]["resa_media"], f"storico (n={stats[key]['n']})"
            else:
                resa, fonte = RESA_DEFAULT.get(c.tipo, 0.7), "default"
        punti = round(c.punti_max * resa, 3)
        dettaglio[c.nome] = {"punti_max": c.punti_max, "resa": resa, "punti": punti, "fonte": fonte}
        totale += punti
    return round(totale, 3), dettaglio


def normalizza(s: str) -> str:
    return " ".join(s.lower().strip().split())


# ---------------------------------------------------------------------------
# Punteggio economico
# ---------------------------------------------------------------------------

FORMULE_SUPPORTATE = {"lineare", "proporzionale", "bilineare"}


class FormulaNonSupportata(Exception):
    """
    La formula del disciplinare non e' fra quelle che sappiamo calcolare.

    Si solleva invece di approssimare: un punteggio economico sbagliato porta a
    consigliare il ribasso sbagliato, che e' il danno peggiore che questo
    strumento possa fare.
    """

    def __init__(self, formula: str, testo: str = ""):
        self.formula = formula
        self.testo = testo
        super().__init__(
            f"La formula «{formula}» non e' fra quelle calcolabili "
            f"({', '.join(sorted(FORMULE_SUPPORTATE))}). Il punteggio economico non viene "
            "calcolato: va letto il testo del disciplinare e deciso a mano."
        )


def punteggio_economico(ribasso: float, ribassi_tutti: list[float], cfg: ConfigGara) -> float:
    """Punti prezzo per un singolo ribasso, dato l'insieme dei ribassi in gara."""
    pmax = cfg.punti_economico

    # Gara a sola offerta tecnica (capita: il Salzano vale 100 punti di tecnica
    # e zero di prezzo). Non e' un errore, e' un caso da gestire.
    if pmax <= 0:
        return 0.0

    if cfg.formula_prezzo not in FORMULE_SUPPORTATE:
        raise FormulaNonSupportata(cfg.formula_prezzo, getattr(cfg, "formula_testo", ""))

    r_max = max(ribassi_tutti) if ribassi_tutti else 0.0
    if r_max <= 0:
        return 0.0

    if cfg.formula_prezzo == "proporzionale":
        # Interpolazione lineare semplice: P = Pmax × R / Rmax
        return round(pmax * ribasso / r_max, 3)

    if cfg.formula_prezzo == "bilineare":
        # Formula "a due rette" (ANAC): soglia = media dei ribassi × X
        media = sum(ribassi_tutti) / len(ribassi_tutti)
        soglia = cfg.coeff_bilineare * media
        if soglia <= 0:
            return 0.0
        if ribasso <= soglia:
            return round(pmax * ribasso / soglia, 3)
        return round(pmax * (1 + (ribasso - soglia) / (r_max - soglia)) / 2, 3) if r_max > soglia else pmax

    # Default "lineare": interpolazione fra prezzo base (0 punti) e miglior ribasso (max)
    # matematicamente coincide con la proporzionale sul ribasso; tenuta distinta per chiarezza
    return round(pmax * ribasso / r_max, 3)


# ---------------------------------------------------------------------------
# Simulazione
# ---------------------------------------------------------------------------

def simula(cfg: ConfigGara, resa_storica: dict, ribasso_nostro: float,
           concorrenti: list[Concorrente]) -> dict:
    tec_max = cfg.punti_tecnico

    nostro_tec, dettaglio = punteggio_tecnico_nostro(cfg, resa_storica)
    offerenti = [RisultatoOfferente("Noi", nostro_tec, 0.0, ribasso_nostro, dettaglio_criteri=dettaglio)]
    for c in concorrenti:
        offerenti.append(RisultatoOfferente(c.nome, round(tec_max * c.livello_tecnico, 3), 0.0, c.ribasso))

    # Sbarramento tecnico
    if cfg.soglia_sbarramento is not None:
        for o in offerenti:
            if o.tecnico < cfg.soglia_sbarramento:
                o.escluso = True

    ammessi = [o for o in offerenti if not o.escluso]

    # Riparametrazione (opzionale): il miglior tecnico viene portato al massimo
    if cfg.riparametrazione and ammessi:
        best = max(o.tecnico for o in ammessi)
        if best > 0:
            for o in ammessi:
                o.tecnico = round(o.tecnico * tec_max / best, 3)

    # Punteggio economico calcolato sui soli ammessi
    ribassi = [o.ribasso for o in ammessi]
    for o in ammessi:
        o.economico = punteggio_economico(o.ribasso, ribassi, cfg)

    graduatoria = sorted(offerenti, key=lambda o: (o.escluso, -o.totale))
    noi = next(o for o in offerenti if o.nome == "Noi")
    posizione = next(i for i, o in enumerate(graduatoria, 1) if o.nome == "Noi")
    vincitore = graduatoria[0]

    sens = sensibilita(cfg, resa_storica, nostro_tec, concorrenti, noi, vincitore)

    return {
        "graduatoria": graduatoria,
        "noi": noi,
        "posizione": posizione,
        "vincitore": vincitore,
        "distacco": round(vincitore.totale - noi.totale, 3),
        "sensibilita": sens,
    }


def sensibilita(cfg, resa_storica, nostro_tec, concorrenti, noi, vincitore) -> dict:
    """Quanto ribasso serve per vincere a tecnico invariato (ricerca deterministica
    a passi di 0.1) e quanti punti tecnici servono a ribasso invariato."""
    out = {"ribasso_minimo_vittoria": None, "punti_tecnici_mancanti": 0.0}

    if noi.escluso:
        out["punti_tecnici_mancanti"] = round(cfg.soglia_sbarramento - nostro_tec, 3)
        return out

    if noi.nome == vincitore.nome:
        out["ribasso_minimo_vittoria"] = noi.ribasso
        return out

    # Ribasso minimo: scansione da 0 a 100 a passi di 0.1
    r = 0.0
    while r <= 100.0:
        res = _totale_con_ribasso(cfg, resa_storica, r, concorrenti)
        if res["noi_vince"]:
            out["ribasso_minimo_vittoria"] = round(r, 1)
            break
        r = round(r + 0.1, 1)

    # Punti tecnici mancanti a ribasso invariato
    gap = vincitore.totale - noi.totale
    out["punti_tecnici_mancanti"] = round(max(gap, 0.0), 3)
    return out


def _totale_con_ribasso(cfg, resa_storica, ribasso, concorrenti) -> dict:
    """Ricalcolo leggero senza sensibilità (evita ricorsione)."""
    tec_max = cfg.punti_tecnico
    nostro_tec, _ = punteggio_tecnico_nostro(cfg, resa_storica)
    tecs = {"Noi": nostro_tec}
    for c in concorrenti:
        tecs[c.nome] = round(tec_max * c.livello_tecnico, 3)
    if cfg.soglia_sbarramento is not None:
        tecs = {k: v for k, v in tecs.items() if v >= cfg.soglia_sbarramento}
    if "Noi" not in tecs:
        return {"noi_vince": False}
    if cfg.riparametrazione:
        best = max(tecs.values())
        if best > 0:
            tecs = {k: round(v * tec_max / best, 3) for k, v in tecs.items()}
    ribassi_map = {"Noi": ribasso, **{c.nome: c.ribasso for c in concorrenti if c.nome in tecs}}
    ribassi = list(ribassi_map.values())
    totali = {k: tecs[k] + punteggio_economico(ribassi_map[k], ribassi, cfg) for k in tecs}
    best_tot = max(totali.values())
    return {"noi_vince": totali["Noi"] >= best_tot - 1e-9}


# ---------------------------------------------------------------------------
# Scenari multipli
# ---------------------------------------------------------------------------

def scenario(cfg: ConfigGara, resa_storica: dict, ribasso: float,
             concorrenti: list[Concorrente], delta_tecnico: float = 0.0,
             etichetta: str = "") -> dict:
    """
    Un singolo scenario: il nostro ribasso, i concorrenti ipotizzati, e quanti
    punti tecnici in più o in meno rispetto alla resa storica.

    Restituisce sempre un dizionario: se la formula non è calcolabile lo dice
    invece di sollevare, così gli altri scenari della stessa tabella non saltano.
    """
    try:
        res = simula(cfg, resa_storica, ribasso, concorrenti)
    except FormulaNonSupportata as e:
        return {"etichetta": etichetta, "ribasso": ribasso, "calcolabile": False,
                "motivo": str(e), "formula_testo": e.testo}

    noi = res["noi"]
    # Il delta tecnico si applica dopo il calcolo: è un "cosa succede se".
    if delta_tecnico:
        noi_tec = round(noi.tecnico + delta_tecnico, 3)
        totale_noi = round(noi_tec + noi.economico, 3)
        migliori = [o.totale for o in res["graduatoria"] if o.nome != "Noi" and not o.escluso]
        vinciamo = not migliori or totale_noi >= max(migliori) - 1e-9
    else:
        noi_tec, totale_noi = noi.tecnico, noi.totale
        vinciamo = res["vincitore"].nome == "Noi"

    return {
        "etichetta": etichetta or f"ribasso {ribasso:g}%",
        "ribasso": ribasso,
        "delta_tecnico": delta_tecnico,
        "calcolabile": True,
        "nostro_tecnico": noi_tec,
        "nostro_economico": noi.economico,
        "nostro_totale": totale_noi,
        "vincitore": res["vincitore"].nome,
        "distacco": res["distacco"],
        "posizione": res["posizione"],
        "vinciamo": vinciamo,
        "graduatoria": [{"nome": o.nome, "tecnico": o.tecnico, "economico": o.economico,
                         "totale": o.totale, "ribasso": o.ribasso, "escluso": o.escluso}
                        for o in res["graduatoria"]],
        "ribasso_minimo_vittoria": res["sensibilita"]["ribasso_minimo_vittoria"],
        "punti_tecnici_mancanti": res["sensibilita"]["punti_tecnici_mancanti"],
        "dettaglio_criteri": noi.dettaglio_criteri,
    }


RIBASSI_RAPIDI = [3.0, 5.0, 7.0]


def confronto(cfg: ConfigGara, resa_storica: dict, concorrenti: list[Concorrente],
              ribassi: list[float] | None = None,
              delta_tecnici: list[float] | None = None) -> dict:
    """
    Più scenari affiancati: un ribasso per colonna, più le varianti sui punti
    tecnici. Tutto deterministico: stessi ingressi, stessa tabella.
    """
    ribassi = ribassi if ribassi is not None else RIBASSI_RAPIDI
    scenari = [scenario(cfg, resa_storica, r, concorrenti, etichetta=f"ribasso {r:g}%")
               for r in ribassi]

    for d in (delta_tecnici or []):
        if not d:
            continue
        base = ribassi[0] if ribassi else 0.0
        segno = "+" if d > 0 else ""
        scenari.append(scenario(cfg, resa_storica, base, concorrenti, delta_tecnico=d,
                                etichetta=f"ribasso {base:g}% con {segno}{d:g} punti tecnici"))

    calcolabili = [s for s in scenari if s["calcolabile"]]
    return {
        "scenari": scenari,
        "formula": cfg.formula_prezzo,
        "formula_calcolabile": bool(calcolabili) or cfg.punti_economico <= 0,
        "somma_criteri": sum(c.punti_max for c in cfg.criteri),
        "vincenti": [s["etichetta"] for s in calcolabili if s["vinciamo"]],
    }
