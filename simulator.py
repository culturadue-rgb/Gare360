"""
Simulatore deterministico di gara (OEPV).

Nessuna casualità: dati gli stessi input (configurazione di gara, tracker,
ribassi dei concorrenti) restituisce sempre lo stesso risultato.

Flusso:
  1. Per ogni criterio tecnico, il punteggio atteso = punti max × resa storica
     letta dal tracker (se il criterio non è nel tracker si usa una resa di default).
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
    resa_override: Optional[float] = None  # 0..1, se impostata scavalca il tracker


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


def punteggio_tecnico_nostro(cfg: ConfigGara, tracker: dict) -> tuple[float, dict]:
    """Somma dei punti attesi per criterio. Restituisce (totale, dettaglio)."""
    dettaglio = {}
    totale = 0.0
    stats = tracker.get("criteri", {})
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

def punteggio_economico(ribasso: float, ribassi_tutti: list[float], cfg: ConfigGara) -> float:
    """Punti prezzo per un singolo ribasso, dato l'insieme dei ribassi in gara."""
    pmax = cfg.punti_economico
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

def simula(cfg: ConfigGara, tracker: dict, ribasso_nostro: float,
           concorrenti: list[Concorrente]) -> dict:
    tec_max = cfg.punti_tecnico

    nostro_tec, dettaglio = punteggio_tecnico_nostro(cfg, tracker)
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

    sens = sensibilita(cfg, tracker, nostro_tec, concorrenti, noi, vincitore)

    return {
        "graduatoria": graduatoria,
        "noi": noi,
        "posizione": posizione,
        "vincitore": vincitore,
        "distacco": round(vincitore.totale - noi.totale, 3),
        "sensibilita": sens,
    }


def sensibilita(cfg, tracker, nostro_tec, concorrenti, noi, vincitore) -> dict:
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
        res = _totale_con_ribasso(cfg, tracker, r, concorrenti)
        if res["noi_vince"]:
            out["ribasso_minimo_vittoria"] = round(r, 1)
            break
        r = round(r + 0.1, 1)

    # Punti tecnici mancanti a ribasso invariato
    gap = vincitore.totale - noi.totale
    out["punti_tecnici_mancanti"] = round(max(gap, 0.0), 3)
    return out


def _totale_con_ribasso(cfg, tracker, ribasso, concorrenti) -> dict:
    """Ricalcolo leggero senza sensibilità (evita ricorsione)."""
    tec_max = cfg.punti_tecnico
    nostro_tec, _ = punteggio_tecnico_nostro(cfg, tracker)
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
