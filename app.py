"""
Stratega Gare — app con tre aree:
  1. Simulatore deterministico (legge il tracker)
  2. Tracker per criterio (compilato a mano, CSV)
  3. Archivio storico (schede gara)
  4. Assistente AI (prompt placeholder, contesto = archivio + tracker)

Avvio:  streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

import archive
import chatbot
import tracker as trk
from simulator import ConfigGara, Concorrente, Criterio, simula

# ---------------------------------------------------------------------------
# Tema e stile
# ---------------------------------------------------------------------------

LIME = "#9FD32B"
LIME_SCURO = "#6E9A12"
BLU = "#1B3F8F"
BLU_SCURO = "#12233F"
BLU_CHIARO = "#EEF3FA"

st.set_page_config(page_title="Stratega Gare", page_icon="📊", layout="wide")

st.markdown(
    f"""
<style>
  .sg-testata {{
    background: {BLU};
    color: white;
    padding: 1.4rem 1.8rem 1.2rem;
    border-radius: 14px;
    border-left: 12px solid {LIME};
    margin-bottom: 1.2rem;
  }}
  .sg-testata h1 {{ margin: 0; font-size: 1.9rem; color: white; letter-spacing: -0.01em; }}
  .sg-testata p  {{ margin: .3rem 0 0; opacity: .85; font-size: .95rem; }}

  .stTabs [data-baseweb="tab-list"] {{ gap: .4rem; }}
  .stTabs [data-baseweb="tab"] {{
    background: {BLU_CHIARO}; border-radius: 10px 10px 0 0;
    padding: .55rem 1.1rem; color: {BLU_SCURO}; font-weight: 600;
  }}
  .stTabs [aria-selected="true"] {{ background: {LIME} !important; color: {BLU_SCURO} !important; }}

  div[data-testid="stMetric"] {{
    background: {BLU_CHIARO}; border-radius: 12px; padding: .8rem 1rem;
    border-top: 5px solid {LIME};
  }}
  div[data-testid="stMetric"] label {{ color: {BLU}; font-weight: 600; }}

  .stButton > button[kind="primary"] {{
    background: {BLU}; color: white; border: 0; border-radius: 10px; font-weight: 600;
  }}
  .stButton > button[kind="primary"]:hover {{ background: {BLU_SCURO}; color: {LIME}; }}
  .stButton > button[kind="secondary"] {{ border: 2px solid {LIME}; border-radius: 10px; color: {BLU_SCURO}; }}

  .sg-esito-vinta {{ background: {LIME}; color: {BLU_SCURO}; padding:.4rem .8rem; border-radius:8px; font-weight:700; display:inline-block; }}
  .sg-esito-persa {{ background: {BLU}; color: white; padding:.4rem .8rem; border-radius:8px; font-weight:700; display:inline-block; }}
  .sg-nota {{ color:{LIME_SCURO}; font-size:.85rem; }}
</style>
<div class="sg-testata">
  <h1>Stratega Gare</h1>
  <p>Simula il punteggio, tieni l'archivio delle gare passate, chiedi consiglio all'assistente.</p>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Stato
# ---------------------------------------------------------------------------

if "tracker" not in st.session_state:
    st.session_state.tracker = trk.carica()
if "chat" not in st.session_state:
    st.session_state.chat = []

tab_sim, tab_trk, tab_arch, tab_chat = st.tabs(["Simulatore", "Tracker", "Archivio storico", "Assistente"])

# ===========================================================================
# 1. SIMULATORE
# ===========================================================================
with tab_sim:
    col_cfg, col_out = st.columns([1, 1.35], gap="large")

    with col_cfg:
        st.subheader("Configurazione gara")
        nome_gara = st.text_input("Nome gara", "Nuova gara")
        base = st.number_input("Importo a base d'asta (€)", min_value=0.0, value=500_000.0, step=10_000.0)
        c1, c2 = st.columns(2)
        p_tec = c1.number_input("Punti tecnico", 0.0, 100.0, 70.0, step=5.0)
        p_eco = c2.number_input("Punti economico", 0.0, 100.0, 30.0, step=5.0)
        if abs(p_tec + p_eco - 100) > 1e-6:
            st.warning("Tecnico + economico dovrebbero fare 100.")

        formula = st.selectbox(
            "Formula punteggio prezzo",
            ["lineare", "proporzionale", "bilineare"],
            format_func=lambda x: {
                "lineare": "Interpolazione lineare sul ribasso",
                "proporzionale": "Proporzionale al ribasso (R / Rmax)",
                "bilineare": "Bilineare con soglia (a due rette)",
            }[x],
        )
        coeff = 0.85
        if formula == "bilineare":
            coeff = st.select_slider("Coefficiente X", [0.80, 0.85, 0.90], value=0.85)

        c3, c4 = st.columns(2)
        usa_soglia = c3.checkbox("Soglia di sbarramento")
        soglia = c3.number_input("Punti tecnici minimi", 0.0, 100.0, 40.0, disabled=not usa_soglia)
        riparam = c4.checkbox("Riparametrazione tecnica")

        st.markdown("**Criteri tecnici**")
        st.caption("Lascia vuota la resa per usare la tab Tracker (stesso nome di criterio); 0–1 per forzarla qui.")
        df_criteri = st.data_editor(
            pd.DataFrame(
                {
                    "criterio": ["Progetto tecnico", "Migliorie", "Certificazioni", "Esperienza analoga"],
                    "tipo": ["qualitativo", "qualitativo", "tabellare", "tabellare"],
                    "punti_max": [30.0, 20.0, 10.0, 10.0],
                    "resa_manuale": [None, None, None, None],
                }
            ),
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "tipo": st.column_config.SelectboxColumn(options=["tabellare", "qualitativo"]),
                "punti_max": st.column_config.NumberColumn(min_value=0.0, step=1.0),
                "resa_manuale": st.column_config.NumberColumn(min_value=0.0, max_value=1.0, step=0.05),
            },
            key="ed_criteri",
        )

        st.markdown("**Offerta economica**")
        ribasso_nostro = st.slider("Nostro ribasso (%)", 0.0, 60.0, 12.0, 0.5)

        st.markdown("**Concorrenti (profili ipotizzati)**")
        df_conc = st.data_editor(
            pd.DataFrame(
                {
                    "nome": ["Concorrente A", "Concorrente B"],
                    "livello_tecnico": [0.85, 0.70],
                    "ribasso": [15.0, 22.0],
                }
            ),
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "livello_tecnico": st.column_config.NumberColumn("livello tecnico (0–1)", min_value=0.0, max_value=1.0, step=0.05),
                "ribasso": st.column_config.NumberColumn("ribasso %", min_value=0.0, max_value=100.0, step=0.5),
            },
            key="ed_conc",
        )

        avvia = st.button("Simula", type="primary", use_container_width=True)

    with col_out:
        st.subheader("Risultato")
        if avvia:
            criteri = [
                Criterio(
                    nome=str(r.criterio),
                    tipo=str(r.tipo),
                    punti_max=float(r.punti_max),
                    resa_override=None if pd.isna(r.resa_manuale) else float(r.resa_manuale),
                )
                for r in df_criteri.itertuples()
                if isinstance(r.criterio, str) and r.criterio.strip() and not pd.isna(r.punti_max)
            ]
            somma = sum(c.punti_max for c in criteri)
            if abs(somma - p_tec) > 1e-6:
                st.warning(f"I criteri sommano {somma:g} punti ma il tecnico vale {p_tec:g}.")

            concorrenti = [
                Concorrente(str(r.nome), float(r.livello_tecnico), float(r.ribasso))
                for r in df_conc.itertuples()
                if isinstance(r.nome, str) and r.nome.strip()
            ]
            cfg = ConfigGara(
                nome=nome_gara, base_asta=base, punti_tecnico=p_tec, punti_economico=p_eco,
                criteri=criteri, formula_prezzo=formula, coeff_bilineare=coeff,
                soglia_sbarramento=soglia if usa_soglia else None, riparametrazione=riparam,
            )
            res = simula(cfg, st.session_state.tracker, ribasso_nostro, concorrenti)
            st.session_state.ultimo_risultato = res

        res = st.session_state.get("ultimo_risultato")
        if not res:
            st.info("Compila la configurazione a sinistra e premi **Simula**.")
        else:
            noi = res["noi"]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Posizione", f"{res['posizione']}°")
            m2.metric("Totale", f"{noi.totale:.2f}")
            m3.metric("Tecnico", f"{noi.tecnico:.2f}")
            m4.metric("Economico", f"{noi.economico:.2f}")

            if noi.escluso:
                st.error(f"Esclusi: tecnico sotto la soglia di {res['sensibilita']['punti_tecnici_mancanti']:.2f} punti.")
            elif res["posizione"] == 1:
                st.markdown('<span class="sg-esito-vinta">Gara vinta nella simulazione</span>', unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<span class="sg-esito-persa">Distacco dal primo: {res["distacco"]:.2f} punti</span>',
                    unsafe_allow_html=True,
                )

            st.markdown("**Graduatoria**")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Offerente": o.nome, "Tecnico": round(o.tecnico, 2),
                            "Economico": round(o.economico, 2), "Totale": o.totale,
                            "Ribasso %": o.ribasso, "Escluso": "sì" if o.escluso else "",
                        }
                        for o in res["graduatoria"]
                    ]
                ),
                hide_index=True, use_container_width=True,
            )

            s = res["sensibilita"]
            st.markdown("**Cosa serve per vincere**")
            if noi.escluso:
                st.write(f"Servono almeno **{s['punti_tecnici_mancanti']:.2f} punti tecnici** in più per superare lo sbarramento.")
            elif res["posizione"] == 1:
                st.write("Con questi profili di concorrenti la nostra offerta è già prima.")
            else:
                if s["ribasso_minimo_vittoria"] is not None:
                    st.write(f"A tecnico invariato, il ribasso minimo per vincere è **{s['ribasso_minimo_vittoria']:.1f}%** "
                             f"(oggi {noi.ribasso:.1f}%).")
                else:
                    st.write("Nessun ribasso fino al 100% basta da solo: bisogna recuperare sul tecnico.")
                st.write(f"A ribasso invariato, servono **{s['punti_tecnici_mancanti']:.2f} punti tecnici** in più.")

            st.markdown("**Dettaglio criteri (da dove viene il tecnico)**")
            st.dataframe(
                pd.DataFrame(
                    [
                        {"Criterio": k, "Punti max": v["punti_max"], "Resa": f"{v['resa']:.0%}",
                         "Punti attesi": v["punti"], "Fonte resa": v["fonte"]}
                        for k, v in noi.dettaglio_criteri.items()
                    ]
                ),
                hide_index=True, use_container_width=True,
            )

# ===========================================================================
# 2. TRACKER (lo compili tu)
# ===========================================================================
with tab_trk:
    st.subheader("Tracker prestazioni per criterio")
    st.caption("Il simulatore legge da qui la resa attesa di ogni criterio. Il file è `data/tracker.csv`: "
               "modificalo nella griglia, nell'editor testo, o direttamente in Excel.")

    t1, t2 = st.columns([1.7, 1], gap="large")

    with t1:
        st.markdown("**Griglia** — aggiungi righe, modifica valori, cancella con l'icona del cestino")
        righe = trk.leggi_righe()
        df_trk = pd.DataFrame(righe, columns=trk.COLONNE) if righe else pd.DataFrame(columns=trk.COLONNE)
        df_edit = st.data_editor(
            df_trk, num_rows="dynamic", use_container_width=True, key="ed_tracker",
            column_config={
                "criterio": st.column_config.TextColumn("Criterio", required=True),
                "tipo": st.column_config.SelectboxColumn("Tipo", options=["tabellare", "qualitativo"], default="qualitativo"),
                "resa": st.column_config.NumberColumn("Resa (0–1)", min_value=0.0, max_value=1.0, step=0.05, format="%.2f"),
                "n": st.column_config.NumberColumn("Gare (n)", min_value=0, step=1),
                "note": st.column_config.TextColumn("Note"),
            },
        )
        if st.button("Salva tracker", type="primary", use_container_width=True):
            pulite = []
            for r in df_edit.itertuples():
                if not isinstance(r.criterio, str) or not r.criterio.strip() or pd.isna(r.resa):
                    continue
                pulite.append({"criterio": r.criterio.strip(),
                               "tipo": r.tipo if isinstance(r.tipo, str) else "qualitativo",
                               "resa": round(float(r.resa), 3),
                               "n": 0 if pd.isna(r.n) else int(r.n),
                               "note": "" if pd.isna(r.note) else str(r.note)})
            trk.scrivi_righe(pulite)
            st.session_state.tracker = trk.carica()
            st.success(f"Tracker salvato: {len(pulite)} criteri.")
            st.rerun()

        with st.expander("Editor testo del file CSV"):
            testo_trk = st.text_area("tracker.csv", trk.leggi_testo(), height=220, label_visibility="collapsed")
            if st.button("Salva CSV"):
                err = trk.valida_testo(testo_trk)
                if err:
                    st.error(err)
                else:
                    trk.salva_testo(testo_trk)
                    st.session_state.tracker = trk.carica()
                    st.success("CSV salvato.")
                    st.rerun()

    with t2:
        st.markdown("**Come compilarlo**")
        st.write("Una riga per criterio. Usa lo stesso nome che scriverai nel simulatore: "
                 "l'abbinamento ignora maiuscole e spazi.")
        st.write("- **resa**: frazione dei punti massimi che prendete di solito (0,70 = 70%)")
        st.write("- **tipo**: tabellare o qualitativo")
        st.write("- **n**: su quante gare si basa il valore (solo informativo)")
        st.write("- **note**: libere")
        st.caption("Se nel simulatore inserisci un criterio che qui non c'è, viene usata una resa di default "
                   "(80% tabellare, 65% qualitativo) e il dettaglio lo segnala come «default».")

# ===========================================================================
# 3. ARCHIVIO STORICO
# ===========================================================================
with tab_arch:
    schede = archive.leggi_schede()
    a1, a2 = st.columns([1.2, 1], gap="large")

    with a1:
        st.subheader("Schede gara")
        st.caption("Questo è lo spazio che alimenta il tracker. Le schede vivono in `data/storico-gare.md`.")
        if not schede:
            st.info("Nessuna scheda ancora. Aggiungine una dal modulo a destra o incolla il verbale qui sotto.")
        for s in schede:
            esito = s["risultato"].lower()
            badge = "vinta" if esito.startswith("vint") else "persa"
            with st.expander(f"{s['titolo']} — {s['risultato'] or 'esito n.d.'} ({s['anno'] or 'anno n.d.'})"):
                st.markdown(f'<span class="sg-esito-{badge}">{s["risultato"] or "esito n.d."}</span>', unsafe_allow_html=True)
                st.write(f"Ente: {s['ente'] or '—'} · Base d'asta: {s['base_asta'] or '—'} · "
                         f"Nostro ribasso: {s['ribasso_nostro'] or '—'}% · Ribasso vincitore: {s['ribasso_vincitore'] or '—'}%")
                if s["criteri"]:
                    st.dataframe(pd.DataFrame(s["criteri"]), hide_index=True, use_container_width=True)
                st.markdown(s["blocco"])

        st.divider()
        st.markdown("**Editor del file completo**")
        testo = st.text_area("storico-gare.md", archive.leggi_testo(), height=320, label_visibility="collapsed")
        if st.button("Salva file", type="primary", use_container_width=True):
            archive.salva_testo(testo)
            st.success("Archivio salvato.")
            st.rerun()

    with a2:
        st.subheader("Nuova scheda")
        with st.form("nuova_scheda", clear_on_submit=True):
            titolo = st.text_input("Nome / oggetto della gara *")
            ente = st.text_input("Ente / stazione appaltante")
            n1, n2 = st.columns(2)
            anno = n1.text_input("Anno")
            base_asta = n2.number_input("Base d'asta (€)", min_value=0.0, value=0.0, step=10_000.0)
            n3, n4 = st.columns(2)
            pt = n3.number_input("Punti tecnico", 0.0, 100.0, 70.0)
            pe = n4.number_input("Punti economico", 0.0, 100.0, 30.0)
            risultato = st.selectbox("Risultato", ["vinta", "persa", "esclusa", "ritirata"])
            n5, n6 = st.columns(2)
            pn = n5.number_input("Nostro punteggio totale", 0.0, 100.0, 0.0)
            pv = n6.number_input("Punteggio vincitore", 0.0, 100.0, 0.0)
            n7, n8 = st.columns(2)
            rn = n7.number_input("Nostro ribasso %", 0.0, 100.0, 0.0, 0.5)
            rv = n8.number_input("Ribasso vincitore %", 0.0, 100.0, 0.0, 0.5)
            formula_prezzo = st.text_input("Meccanismo punti prezzo", "")
            st.markdown("Punteggi voce per voce (dal verbale)")
            df_new = st.data_editor(
                pd.DataFrame({"criterio": [""], "tipo": ["qualitativo"], "punti_max": [0.0], "punti_presi": [0.0], "note": [""]}),
                num_rows="dynamic", use_container_width=True,
                column_config={"tipo": st.column_config.SelectboxColumn(options=["tabellare", "qualitativo"])},
            )
            funzionato = st.text_area("Cosa ha funzionato", height=70)
            persi = st.text_area("Dove abbiamo lasciato punti e perché", height=70)
            riutil = st.text_area("Contenuti riutilizzabili", height=70)
            note_ente = st.text_area("Note su commissione / ente", height=70)
            ok = st.form_submit_button("Aggiungi all'archivio", type="primary", use_container_width=True)

        if ok:
            if not titolo.strip():
                st.error("Il nome della gara è obbligatorio.")
            else:
                criteri = [
                    {"criterio": str(r.criterio), "tipo": str(r.tipo), "punti_max": float(r.punti_max),
                     "punti_presi": float(r.punti_presi), "note": "" if pd.isna(r.note) else str(r.note)}
                    for r in df_new.itertuples()
                    if isinstance(r.criterio, str) and r.criterio.strip()
                ]
                archive.aggiungi_scheda({
                    "titolo": titolo, "ente": ente, "anno": anno, "base_asta": base_asta or "",
                    "punti_tecnico": pt, "punti_economico": pe, "risultato": risultato,
                    "punteggio_nostro": pn or "", "punteggio_vincitore": pv or "",
                    "ribasso_nostro": rn or "", "ribasso_vincitore": rv or "", "formula_prezzo": formula_prezzo,
                    "criteri": criteri, "funzionato": funzionato, "persi": persi,
                    "riutilizzabili": riutil, "note_ente": note_ente,
                })
                st.success(f"Scheda «{titolo}» aggiunta.")
                st.rerun()

# ===========================================================================
# 4. ASSISTENTE
# ===========================================================================
with tab_chat:
    with st.sidebar:
        st.markdown("### Assistente")
        api_key = st.text_input("Chiave API Anthropic", type="password", help="In alternativa imposta ANTHROPIC_API_KEY.")
        modello = st.text_input("Modello", chatbot.MODELLO_DEFAULT)
        includi_ctx = st.toggle("Passa archivio e tracker come contesto", value=True)
        if st.button("Svuota conversazione", use_container_width=True):
            st.session_state.chat = []
            st.rerun()

    with st.expander("Prompt di sistema (placeholder, da completare)"):
        nuovo_prompt = st.text_area("prompt", chatbot.carica_prompt(), height=220, label_visibility="collapsed")
        if st.button("Salva prompt"):
            chatbot.salva_prompt(nuovo_prompt)
            st.success("Prompt salvato in prompts/stratega_gare.md")

    for m in st.session_state.chat:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    domanda = st.chat_input("Chiedi allo stratega-gare…")
    if domanda:
        st.session_state.chat.append({"role": "user", "content": domanda})
        with st.chat_message("user"):
            st.markdown(domanda)
        system = chatbot.costruisci_system(archive.leggi_testo(), st.session_state.tracker, includi_ctx)
        with st.chat_message("assistant"):
            with st.spinner("Sto ragionando…"):
                risposta = chatbot.rispondi(st.session_state.chat, system, api_key or None, modello)
            st.markdown(risposta)
        st.session_state.chat.append({"role": "assistant", "content": risposta})
