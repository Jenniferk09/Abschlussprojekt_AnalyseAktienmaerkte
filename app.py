# -*- coding: utf-8 -*-
"""Streamlit-App: Kombinierte Risikoampel für vier US-Aktienindizes.

Zeigt pro Index die tagesaktuelle Ampel (Grün/Gelb/Rot), den Kursverlauf mit
Ampel-Hintergrund und eine Was-wäre-wenn-Simulation (Buy & Hold vs. Ausstieg
bei Rot). Die Ampel-Logik steckt vollständig in ``ampel_core.py``; die App ist
nur die Oberfläche.

Zusätzlich gibt es einen optionalen "Dashboard anpassen"-Modus (Sidebar): Dort
lassen sich Reihenfolge, Sichtbarkeit, Spaltenbreiten, Größen, Schriftgröße und
Farben beider Ansichten live einstellen. Ein Klick auf "Speichern & einfrieren"
schreibt die Auswahl in ``layout_config.json`` und sperrt den Editor danach
dauerhaft (auch über einen Neustart hinweg) — die App zeigt ab dann nur noch
das fest eingestellte Layout, ohne Bearbeitungsmöglichkeit.
"""
from __future__ import annotations

import json
from pathlib import Path
from string import Template

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ampel_core as ac

st.set_page_config(page_title="Risikoampel", page_icon="🚦", layout="wide")

# ============================================================================
# 1. Layout-/Design-Konfiguration: Standardwerte, Laden, Speichern, Zugriff
# ============================================================================
KONFIG_PFAD = Path(__file__).parent / "layout_config.json"

STANDARD_CFG = {
    "schrift_basis": 12,
    "farbe_hintergrund": "#000000",
    "farbe_karte_hg": "#15181d",
    "farbe_karte_rand": "#2a2f37",
    "farbe_text": "#e6e8eb",
    "farbe_muted": "#9aa3af",
    "farbe_akzent": "#3b8bed",
    "farbe_gruen": "#0ca30c",
    "farbe_gelb": "#e0a72c",
    "farbe_rot": "#d03b3b",
    "ez_reihenfolge": ["status", "chart", "kpi", "www"],
    "ez_sicht_status": True, "ez_sicht_chart": True, "ez_sicht_kpi": True, "ez_sicht_www": True,
    "ez_spalte_banner": 1.2, "ez_spalte_gauge": 1.0, "ez_spalte_chips": 1.3,
    "ez_hoehe_gauge": 180, "ez_hoehe_chart": 430, "ez_hoehe_www": 380,
    "ue_reihenfolge": ["ampel", "kurse", "tabelle", "maxdd"],
    "ue_sicht_ampel": True, "ue_sicht_kurse": True, "ue_sicht_tabelle": True, "ue_sicht_maxdd": True,
    "ue_hoehe_kurs": 300, "ue_hoehe_maxdd": 380,
}

BLOCK_LABEL_EZ = {"status": "Ampel · Gauge · Signal-Lage", "chart": "Kurschart",
                  "kpi": "Kennzahlen-Kacheln", "www": "Was-wäre-wenn-Chart"}
BLOCK_LABEL_UE = {"ampel": "Ampel-Karten (4 Indizes)", "kurse": "Kursverläufe (2×2)",
                  "tabelle": "Kennzahlen-Tabelle", "maxdd": "Max-Drawdown-Vergleich"}


def _lade_konfiguration() -> dict:
    if KONFIG_PFAD.exists():
        try:
            with open(KONFIG_PFAD, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _speichere_konfiguration(cfg: dict):
    with open(KONFIG_PFAD, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


GELADENE_CFG = _lade_konfiguration()
GESPERRT = bool(GELADENE_CFG.get("gesperrt", False))


def feld_key(name: str) -> str:
    """Session-State-Key eines Konfigurationsfeldes; beim ersten Zugriff aus
    der geladenen (oder sonst der Standard-)Konfiguration vorbelegt."""
    key = f"cfg__{name}"
    if key not in st.session_state:
        wert = GELADENE_CFG.get(name, STANDARD_CFG[name])
        if name.endswith("_reihenfolge") and isinstance(wert, list):
            standard_ids = STANDARD_CFG[name]
            wert = [b for b in wert if b in standard_ids] + [b for b in standard_ids if b not in wert]
        st.session_state[key] = wert
    return key


def V(name: str):
    """Aktueller (Live-)Wert eines Konfigurationsfeldes."""
    return st.session_state[feld_key(name)]


def _einfrieren():
    aktuell = {name: st.session_state[feld_key(name)] for name in STANDARD_CFG}
    aktuell["gesperrt"] = True
    _speichere_konfiguration(aktuell)


def _zuruecksetzen():
    for name, standard in STANDARD_CFG.items():
        st.session_state[feld_key(name)] = standard


def _verschiebe(session_key: str, i: int, delta: int):
    liste = st.session_state[session_key]
    j = i + delta
    if 0 <= j < len(liste):
        neu = list(liste)
        neu[i], neu[j] = neu[j], neu[i]
        st.session_state[session_key] = neu


# ============================================================================
# 2. Design-Konstanten aus der Konfiguration (live, bis eingefroren wird)
# ============================================================================
FONT = "Segoe UI, Helvetica, Arial, sans-serif"
SCHRIFT_BASIS = V("schrift_basis")
COL_ACCENT = V("farbe_akzent")
COL_TEXT = V("farbe_text")
COL_MUTED = V("farbe_muted")
COL_GRID = V("farbe_karte_rand")
COL_PRICE = V("farbe_text")
CARD_BG = V("farbe_karte_hg")
CARD_BORDER = V("farbe_karte_rand")
HINTERGRUND = V("farbe_hintergrund")
AMPEL_FARBCODES = {"Grün": V("farbe_gruen"), "Gelb": V("farbe_gelb"), "Rot": V("farbe_rot")}
_AMPEL_EMOJI = {"Grün": "🟢", "Gelb": "🟡", "Rot": "🔴"}


def _hex_zu_rgba(hex_code: str, alpha: float) -> str:
    h = hex_code.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


BG_GOOD = _hex_zu_rgba(AMPEL_FARBCODES["Grün"], 0.22)
BG_BAD = _hex_zu_rgba(AMPEL_FARBCODES["Rot"], 0.24)
BG_NEUTRAL = "rgba(255,255,255,0.07)"

st.markdown(
    Template(
        "<style>"
        "html, body { font-size: ${basis}px; }"
        ".block-container { padding-top: 2.2rem; }"
        '[data-testid="stAppViewContainer"] { background: $bg; }'
        '[data-testid="stSidebar"] { background: $karte; }'
        '[data-testid="stHeader"] { background: rgba(0,0,0,0); }'
        'div[data-testid="stMetricValue"] { font-weight: 700; }'
        ".stButton>button { border-color: $rand; }"
        ".stButton>button:hover { border-color: $akzent; color: $akzent; }"
        "</style>"
    ).substitute(basis=SCHRIFT_BASIS, bg=HINTERGRUND, karte=CARD_BG, rand=CARD_BORDER, akzent=COL_ACCENT),
    unsafe_allow_html=True,
)


# ============================================================================
# 3. Daten (gecached – Kursdaten werden je Index max. alle 6 Stunden neu geladen)
# ============================================================================
@st.cache_data(ttl=60 * 60 * 6, show_spinner="Lade aktuelle Kursdaten …")
def lade_index(index_key: str) -> dict:
    return ac.analysiere_index(index_key)


def de_pct(x: float, stellen: int = 1, signed: bool = False) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    fmt = f"{{:+.{stellen}f}}" if signed else f"{{:.{stellen}f}}"
    return fmt.format(x * 100).replace(".", ",") + " %"


def de_num(x: float, stellen: int = 2, signed: bool = False) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    fmt = f"{{:+.{stellen}f}}" if signed else f"{{:.{stellen}f}}"
    return fmt.format(x).replace(".", ",")


# ============================================================================
# 4. HTML-Bausteine (Kartenfarben/Textfarbe fließen live aus der Konfiguration)
# ============================================================================
def _ampellicht_html(active: str, dot: int = 20, gap: str = "8px", pad: str = "10px 9px") -> str:
    dots = ""
    for name in ["Rot", "Gelb", "Grün"]:
        color = AMPEL_FARBCODES[name]
        if name == active:
            extra = f"background:{color};box-shadow:0 0 12px 3px {color}bb;"
        else:
            extra = f"background:{color};opacity:0.18;"
        dots += f'<div style="width:{dot}px;height:{dot}px;border-radius:50%;{extra}"></div>'
    return (f'<div style="display:inline-flex;flex-direction:column;gap:{gap};align-items:center;'
            f'background:#0a0c10;border:1px solid {CARD_BORDER};padding:{pad};border-radius:12px;">{dots}</div>')


def ampel_banner(res: dict, kompakt: bool = False):
    status = res["status"]
    color = AMPEL_FARBCODES.get(status["ampel"], COL_MUTED)
    licht = _ampellicht_html(status["ampel"], dot=15 if kompakt else 20,
                             gap="6px" if kompakt else "8px", pad="8px 7px" if kompakt else "10px 9px")
    groesse = "1.25rem" if kompakt else "1.7rem"
    html = (f'<div style="display:flex;gap:14px;align-items:center;background:{CARD_BG};'
            f'border:1px solid {CARD_BORDER};border-left:5px solid {color};border-radius:14px;'
            f'padding:14px 16px;box-shadow:0 1px 4px rgba(0,0,0,0.5);">{licht}'
            f'<div><div style="font-size:0.82rem;color:{COL_MUTED};">{res["name"]}</div>'
            f'<div style="font-size:{groesse};font-weight:700;color:{color};line-height:1.15;">{status["ampel"]}</div>'
            f'<div style="font-size:0.8rem;color:{COL_MUTED};">Stand {status["datum"].strftime("%d.%m.%Y")} · '
            f'{status["n_schlecht"]}/{status["n_signale"]} Signale belastet</div></div></div>')
    st.markdown(html, unsafe_allow_html=True)


def signal_chips(res: dict):
    chips = ""
    for s in res["status"]["signale"]:
        if s["schlecht"] is None:
            bg, dot, label = BG_NEUTRAL, COL_MUTED, f'{s["label"]} (n/a)'
        elif s["schlecht"]:
            bg, dot, label = BG_BAD, AMPEL_FARBCODES["Rot"], s["label"]
        else:
            bg, dot, label = BG_GOOD, AMPEL_FARBCODES["Grün"], s["label"]
        chips += (f'<span style="display:inline-flex;align-items:center;gap:6px;background:{bg};'
                  f'border-radius:999px;padding:5px 11px;margin:3px 4px 3px 0;font-size:0.83rem;'
                  f'color:{COL_TEXT};"><span style="width:9px;height:9px;border-radius:50%;'
                  f'background:{dot};"></span>{label}</span>')
    st.markdown(f'<div style="display:flex;flex-wrap:wrap;">{chips}</div>', unsafe_allow_html=True)


def kpi_karte(spalte, label: str, value: str, delta: str, sub: str, gut: bool | None = None):
    dcolor = COL_MUTED if gut is None else (AMPEL_FARBCODES["Grün"] if gut else AMPEL_FARBCODES["Rot"])
    html = (f'<div style="background:{CARD_BG};border:1px solid {CARD_BORDER};border-radius:14px;'
            f'padding:13px 15px;box-shadow:0 1px 4px rgba(0,0,0,0.5);height:100%;">'
            f'<div style="font-size:0.78rem;color:{COL_MUTED};">{label}</div>'
            f'<div style="font-size:1.45rem;font-weight:700;color:{COL_TEXT};line-height:1.3;">{value}</div>'
            f'<div style="font-size:0.8rem;color:{dcolor};font-weight:600;min-height:1.1rem;">{delta or "&nbsp;"}</div>'
            f'<div style="font-size:0.74rem;color:{COL_MUTED};">{sub}</div></div>')
    spalte.markdown(html, unsafe_allow_html=True)


# ============================================================================
# 5. Diagramme (einheitlicher Stil, Farben/Schriftgröße aus der Konfiguration)
# ============================================================================
def _stil(fig: go.Figure, **layout) -> go.Figure:
    titel = layout.pop("title", None)
    titel_dict = dict(font=dict(family=FONT, size=SCHRIFT_BASIS + 3, color=COL_TEXT), x=0.01, xanchor="left")
    if isinstance(titel, str):
        titel_dict["text"] = titel
    elif isinstance(titel, dict):
        titel_dict.update(titel)
    fig.update_layout(
        font=dict(family=FONT, color=COL_TEXT, size=SCHRIFT_BASIS),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=44, b=10),
        title=titel_dict,
        hoverlabel=dict(bgcolor=CARD_BG, font_size=SCHRIFT_BASIS, font_family=FONT, bordercolor=COL_GRID),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=max(SCHRIFT_BASIS - 1, 8))),
        **layout,
    )
    fig.update_xaxes(showgrid=False, showline=True, linecolor=COL_GRID,
                     ticks="outside", tickcolor=COL_GRID, tickfont=dict(color=COL_MUTED))
    fig.update_yaxes(showgrid=True, gridcolor=COL_GRID, zeroline=False, showline=False,
                     tickfont=dict(color=COL_MUTED))
    return fig


def chart_gauge(status: dict, hoehe: int | None = None) -> go.Figure:
    color = AMPEL_FARBCODES.get(status["ampel"], COL_MUTED)
    val = status["belastungsgrad"]
    if val is None or (isinstance(val, float) and np.isnan(val)):
        val = 0.0
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=val,
        number={"valueformat": ".0%", "font": {"family": FONT, "size": SCHRIFT_BASIS + 14, "color": COL_TEXT}},
        gauge={
            "axis": {"range": [0, 1], "tickformat": ".0%", "tickvals": [0, 0.25, 0.5, 0.75, 1],
                     "tickfont": {"size": max(SCHRIFT_BASIS - 3, 7), "color": COL_MUTED}},
            "bar": {"color": color, "thickness": 0.34},
            "bgcolor": "#0a0c10", "bordercolor": COL_GRID, "borderwidth": 1,
        },
        domain={"x": [0, 1], "y": [0, 1]},
    ))
    fig.update_layout(
        height=hoehe or 180, margin=dict(l=18, r=18, t=14, b=6), paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _ampel_hintergrund(fig: go.Figure, df: pd.DataFrame, boost: float = 0.0):
    """Zeichnet die Ampel-Phasen als je EINE Füllfläche pro Farbe (drei Traces
    statt tausender Einzel-Shapes – deutlich performanter)."""
    close = df["Close"].dropna()
    if close.empty:
        return
    ymin, ymax = float(close.min()), float(close.max())
    pad = (ymax - ymin) * 0.03
    alpha = {"Grün": 0.12 + boost, "Gelb": 0.14 + boost, "Rot": 0.16 + boost}
    puffer = {f: ([], []) for f in AMPEL_FARBCODES}
    for phase in ac.ampel_phasen(df):
        xs, ys = puffer[phase["farbe"]]
        xs += [phase["start"], phase["start"], phase["ende"], phase["ende"], None]
        ys += [ymin - pad, ymax + pad, ymax + pad, ymin - pad, None]
    for farbe, (xs, ys) in puffer.items():
        if not xs:
            continue
        fig.add_trace(go.Scatter(x=xs, y=ys, fill="toself",
                                 fillcolor=_hex_zu_rgba(AMPEL_FARBCODES[farbe], alpha[farbe]),
                                 line=dict(width=0), mode="lines", hoverinfo="skip", showlegend=False))


def _hover_daten(res: dict) -> np.ndarray:
    """Baut je Handelstag Zusatzinfos für den Tooltip: Ampel, Belastungsgrad,
    Anzahl belasteter Signale."""
    df = res["df"]
    n_sig = len(res["konfiguration"]["signale"])
    ampel, bel = df["Ampel"], df["Belastungsgrad"]
    sp_ampel = [f"{_AMPEL_EMOJI.get(a, '')} {a}" if isinstance(a, str) else "— (Anlaufphase)"
                for a in ampel]
    sp_bel = [f"{b * 100:.0f} %".replace(".", ",") if pd.notna(b) else "—" for b in bel]
    sp_sig = [f"{int(round(b * n_sig))}/{n_sig} belastet" if pd.notna(b) else "—" for b in bel]
    return np.array(list(zip(sp_ampel, sp_bel, sp_sig)), dtype=object)


def chart_kurs_mit_ampel(res: dict, kompakt: bool = False, mark_ts=None, hoehe: int | None = None) -> go.Figure:
    df = res["df"]
    fig = go.Figure()
    _ampel_hintergrund(fig, df, boost=0.03 if kompakt else 0.0)
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Close"], mode="lines", name=res["name"],
        line=dict(color=COL_PRICE, width=1.1), customdata=_hover_daten(res),
        hovertemplate=("<b>%{x|%d.%m.%Y}</b><br>Kurs: %{y:.0f}"
                       "<br>Ampel: %{customdata[0]}"
                       "<br>Belastungsgrad: %{customdata[1]} (%{customdata[2]})<extra></extra>")))
    if mark_ts is not None:  # gewählten Tag markieren
        pos = df.index.get_indexer([pd.Timestamp(mark_ts)], method="nearest")[0]
        d, y = df.index[pos], float(df["Close"].iloc[pos])
        fig.add_vline(x=d, line=dict(color=COL_ACCENT, width=1, dash="dot"))
        fig.add_trace(go.Scatter(
            x=[d], y=[y], mode="markers", name="Ausgewählt", hoverinfo="skip", showlegend=False,
            marker=dict(size=12, color=COL_ACCENT, line=dict(color=COL_TEXT, width=1.6))))
    if not kompakt:
        for farbe in ac.AMPEL_FARBEN:  # Farb-Legende (unsichtbare Platzhalter)
            fig.add_trace(go.Scatter(
                x=[df.index[0]], y=[None], mode="markers",
                marker=dict(size=11, color=AMPEL_FARBCODES[farbe], symbol="square"), name=farbe))
    titel = res["name"] if kompakt else f'{res["name"]} – Kursverlauf mit Ampel-Hintergrund'
    _stil(fig, height=hoehe or (300 if kompakt else 430), title=titel,
          yaxis_title=None if kompakt else "Kurs (Punkte)", hovermode="x unified", showlegend=not kompakt)
    if not kompakt:
        fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.06),
                         rangeselector=dict(
                             buttons=[dict(count=1, label="1J", step="year", stepmode="backward"),
                                      dict(count=5, label="5J", step="year", stepmode="backward"),
                                      dict(step="all", label="Alles")],
                             bgcolor=CARD_BG, activecolor=COL_ACCENT,
                             font=dict(size=max(SCHRIFT_BASIS - 2, 8), color=COL_TEXT)))
        # mehr Luft zwischen Titel und 1J/5J/Alles-Auswahl (sonst wirkt es gequetscht)
        fig.update_layout(margin=dict(t=70))
    return fig


def chart_was_waere_wenn(res: dict, hoehe: int | None = None) -> go.Figure:
    www, df = res["was_waere_wenn"], res["df"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=www["equity_buy_hold"], mode="lines", name="Buy & Hold",
        line=dict(color=COL_MUTED, width=1.5),
        hovertemplate="%{x|%d.%m.%Y}<br>Buy & Hold: %{y:.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=df.index, y=www["equity_strategie"], mode="lines",
        name="Ampel-Strategie (Ausstieg bei Rot)",
        line=dict(color=COL_ACCENT, width=1.8),
        hovertemplate="%{x|%d.%m.%Y}<br>Ampel: %{y:.2f}<extra></extra>"))
    _stil(fig, height=hoehe or 380, title="Was-wäre-wenn: Wertentwicklung (Start = 1, logarithmisch)",
          yaxis=dict(title="Vielfaches des Startkapitals", type="log", tickmode="array",
                     tickvals=[1, 2, 3, 5, 10, 20, 30],
                     ticktext=["1×", "2×", "3×", "5×", "10×", "20×", "30×"]),
          hovermode="x unified")
    return fig


def chart_maxdd_vergleich(ergebnisse: dict, hoehe: int | None = None) -> go.Figure:
    namen = [r["name"] for r in ergebnisse.values()]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=namen, name="Buy & Hold", marker_color=COL_MUTED,
                         y=[r["was_waere_wenn"]["buy_hold"]["max_drawdown"] * 100 for r in ergebnisse.values()],
                         hovertemplate="%{x}<br>Buy & Hold: %{y:.1f}%<extra></extra>"))
    fig.add_trace(go.Bar(x=namen, name="Ampel-Strategie", marker_color=COL_ACCENT,
                         y=[r["was_waere_wenn"]["strategie"]["max_drawdown"] * 100 for r in ergebnisse.values()],
                         hovertemplate="%{x}<br>Ampel: %{y:.1f}%<extra></extra>"))
    _stil(fig, height=hoehe or 380, barmode="group",
          title="Max Drawdown je Index: Buy & Hold vs. Ampel-Strategie", yaxis_title="Max Drawdown (%)")
    return fig


# ============================================================================
# 6. Ansichten
# ============================================================================
def ansicht_einzelindex(index_key: str):
    res = lade_index(index_key)
    www = res["was_waere_wenn"]
    bh, st_ = www["buy_hold"], www["strategie"]
    df, signale = res["df"], res["konfiguration"]["signale"]

    # --- Tag-Auswahl: Kalenderfeld + Handelstag-Buttons -----------------------
    gueltig = df.index[df["Ampel"].notna()]
    min_d, max_d = gueltig[0].to_pydatetime(), gueltig[-1].to_pydatetime()
    tag_key = f"tag_{index_key}"
    if tag_key not in st.session_state:
        st.session_state[tag_key] = max_d.date()

    def _naechster_handelstag(datum):
        pos = gueltig.get_indexer([pd.Timestamp(datum)], method="nearest")[0]
        return gueltig[pos].date()

    def _schritt(delta):
        pos = gueltig.get_indexer([pd.Timestamp(st.session_state[tag_key])], method="nearest")[0]
        pos = min(max(pos + delta, 0), len(gueltig) - 1)
        st.session_state[tag_key] = gueltig[pos].date()

    def _heute():
        st.session_state[tag_key] = max_d.date()

    def _snap():
        st.session_state[tag_key] = _naechster_handelstag(st.session_state[tag_key])

    c_date, c_prev, c_next, c_today, _ = st.columns([2.1, 0.6, 0.6, 1, 3.7],
                                                     gap="small", vertical_alignment="bottom")
    with c_date:
        gewaehlt = st.date_input("📅 Tag wählen", min_value=min_d.date(), max_value=max_d.date(),
                                 key=tag_key, format="DD.MM.YYYY", on_change=_snap)
    c_prev.button("◀", on_click=_schritt, args=(-1,), help="Vorheriger Handelstag", width="stretch")
    c_next.button("▶", on_click=_schritt, args=(1,), help="Nächster Handelstag", width="stretch")
    c_today.button("Heute", on_click=_heute, help="Zurück zum aktuellsten Tag", width="stretch")

    ist_heute = gewaehlt >= max_d.date()
    status = res["status"] if ist_heute else ac.status_fuer_tag(df, signale, gewaehlt)
    res_tag = {**res, "status": status}

    titel_tag = "Aktueller Tag" if ist_heute else f'Ausgewählter Tag: {status["datum"].strftime("%d.%m.%Y")}'

    # --- Bausteine (Reihenfolge/Sichtbarkeit/Größen aus der Konfiguration) ---
    # Alle drei Spaltenüberschriften nutzen dieselbe Markdown-Formatierung
    # (Schriftart/-größe/Ausrichtung) und stehen als erstes Element ihrer
    # Spalte, damit sie in derselben Zeile auf gleicher Höhe liegen.
    def _b_status():
        c1, c2, c3 = st.columns([V("ez_spalte_banner"), V("ez_spalte_gauge"), V("ez_spalte_chips")], gap="large")
        with c1:
            st.markdown(f"**{titel_tag}**")
            ampel_banner(res_tag)
        with c2:
            st.markdown("**Belastungsgrad**")
            st.plotly_chart(chart_gauge(status, hoehe=V("ez_hoehe_gauge")), width="stretch")
        with c3:
            st.markdown("**Signal-Lage**")
            signal_chips(res_tag)

    def _b_chart():
        st.plotly_chart(chart_kurs_mit_ampel(res, mark_ts=status["datum"], hoehe=V("ez_hoehe_chart")),
                        width="stretch")
        st.caption("💡 Beim Zeigen auf die Kurve erscheint ein Info-Fenster mit Ampel, "
                   "Belastungsgrad und Datum für den jeweiligen Tag; der blaue Marker zeigt "
                   "den oben ausgewählten Tag.")

    def _b_kpi():
        st.markdown("**Kennzahlen seit 2007** – Ampel-Strategie im Vergleich zu Buy & Hold")
        k1, k2, k3, k4 = st.columns(4)
        kpi_karte(k1, "CAGR", de_pct(st_["cagr"]),
                  f'{de_pct(st_["cagr"] - bh["cagr"], signed=True)} ggü. B&H',
                  f'Buy & Hold: {de_pct(bh["cagr"])}', gut=st_["cagr"] >= bh["cagr"])
        kpi_karte(k2, "Max Drawdown", de_pct(st_["max_drawdown"]),
                  f'{de_pct(st_["max_drawdown"] - bh["max_drawdown"], signed=True)} ggü. B&H',
                  f'Buy & Hold: {de_pct(bh["max_drawdown"])}', gut=st_["max_drawdown"] > bh["max_drawdown"])
        kpi_karte(k3, "Calmar", de_num(st_["calmar"]),
                  f'{de_num(st_["calmar"] - bh["calmar"], signed=True)} ggü. B&H',
                  f'Buy & Hold: {de_num(bh["calmar"])}', gut=st_["calmar"] >= bh["calmar"])
        kpi_karte(k4, "Anteil Rot-Tage", de_pct(www["anteil_rot"]), "", "der Handelstage seit 2007", gut=None)

    def _b_www():
        st.plotly_chart(chart_was_waere_wenn(res, hoehe=V("ez_hoehe_www")), width="stretch")

    bloecke = {"status": _b_status, "chart": _b_chart, "kpi": _b_kpi, "www": _b_www}
    sichtbare = [b for b in V("ez_reihenfolge") if V(f"ez_sicht_{b}")]
    for i, block_id in enumerate(sichtbare):
        bloecke[block_id]()
        if i < len(sichtbare) - 1:
            st.divider()


def ansicht_ueberblick():
    ergebnisse = {key: lade_index(key) for key in ac.INDICES}

    def _b_ampel():
        st.subheader("Aktuelle Ampel – alle vier Indizes")
        for spalte, key in zip(st.columns(4, gap="medium"), ac.INDICES):
            with spalte:
                ampel_banner(ergebnisse[key], kompakt=True)

    def _b_kurse():
        st.subheader("Kursverläufe mit Ampel-Hintergrund")
        keys = list(ac.INDICES)
        reihe1, reihe2 = st.columns(2, gap="medium"), st.columns(2, gap="medium")
        for zelle, key in zip([reihe1[0], reihe1[1], reihe2[0], reihe2[1]], keys):
            with zelle:
                st.plotly_chart(chart_kurs_mit_ampel(ergebnisse[key], kompakt=True, hoehe=V("ue_hoehe_kurs")),
                                width="stretch")

    def _b_tabelle():
        st.subheader("Kennzahlen-Vergleich seit 2007")
        daten = {"Index": [], "CAGR B&H": [], "CAGR Ampel": [], "MaxDD B&H": [],
                 "MaxDD Ampel": [], "Calmar Ampel": [], "Anteil Rot": []}
        for res in ergebnisse.values():
            www = res["was_waere_wenn"]
            daten["Index"].append(res["name"])
            daten["CAGR B&H"].append(www["buy_hold"]["cagr"])
            daten["CAGR Ampel"].append(www["strategie"]["cagr"])
            daten["MaxDD B&H"].append(www["buy_hold"]["max_drawdown"])
            daten["MaxDD Ampel"].append(www["strategie"]["max_drawdown"])
            daten["Calmar Ampel"].append(www["strategie"]["calmar"])
            daten["Anteil Rot"].append(www["anteil_rot"])
        tab = pd.DataFrame(daten).set_index("Index")

        def farbe_ampel_spalten(spalte: pd.Series) -> list[str]:
            if spalte.name == "CAGR Ampel":
                return [f"background-color:{BG_GOOD};color:{COL_TEXT}" if a >= b
                        else f"background-color:{BG_BAD};color:{COL_TEXT}"
                        for a, b in zip(spalte, tab["CAGR B&H"])]
            if spalte.name == "MaxDD Ampel":
                return [f"background-color:{BG_GOOD};color:{COL_TEXT}" if a > b
                        else f"background-color:{BG_BAD};color:{COL_TEXT}"
                        for a, b in zip(spalte, tab["MaxDD B&H"])]
            return ["" for _ in spalte]

        styler = (tab.style
                  .format({c: (lambda v: de_num(v)) if c == "Calmar Ampel" else (lambda v: de_pct(v))
                           for c in tab.columns})
                  .apply(farbe_ampel_spalten, axis=0))
        st.dataframe(styler, width="stretch")
        st.caption("Grün = die Ampel-Strategie ist gegenüber Buy & Hold besser (höhere Rendite "
                   "bzw. geringerer Drawdown).")

    def _b_maxdd():
        st.plotly_chart(chart_maxdd_vergleich(ergebnisse, hoehe=V("ue_hoehe_maxdd")), width="stretch")

    bloecke = {"ampel": _b_ampel, "kurse": _b_kurse, "tabelle": _b_tabelle, "maxdd": _b_maxdd}
    sichtbare = [b for b in V("ue_reihenfolge") if V(f"ue_sicht_{b}")]
    for i, block_id in enumerate(sichtbare):
        bloecke[block_id]()
        if i < len(sichtbare) - 1:
            st.divider()


# ============================================================================
# 7. Dashboard-Editor (nur solange nicht eingefroren)
# ============================================================================
def _layout_editor_bloecke(prefix: str, labels: dict):
    reihenfolge_key = feld_key(f"{prefix}_reihenfolge")
    reihenfolge = st.session_state[reihenfolge_key]
    for i, block_id in enumerate(list(reihenfolge)):
        c_chk, c_up, c_down = st.columns([5, 1, 1])
        c_chk.checkbox(labels[block_id], key=feld_key(f"{prefix}_sicht_{block_id}"))
        c_up.button("▲", key=f"{prefix}_up_{block_id}", disabled=(i == 0),
                    on_click=_verschiebe, args=(reihenfolge_key, i, -1))
        c_down.button("▼", key=f"{prefix}_down_{block_id}", disabled=(i == len(reihenfolge) - 1),
                      on_click=_verschiebe, args=(reihenfolge_key, i, 1))


def _dashboard_editor():
    with st.sidebar.expander("🔤 Schrift", expanded=False):
        st.slider("Schriftgröße (px)", 10, 22, key=feld_key("schrift_basis"))
    with st.sidebar.expander("🎨 Farben", expanded=False):
        sp1, sp2 = st.columns(2)
        with sp1:
            st.color_picker("Hintergrund", key=feld_key("farbe_hintergrund"))
            st.color_picker("Kartenhintergrund", key=feld_key("farbe_karte_hg"))
            st.color_picker("Kartenrand", key=feld_key("farbe_karte_rand"))
            st.color_picker("Text", key=feld_key("farbe_text"))
        with sp2:
            st.color_picker("Akzent", key=feld_key("farbe_akzent"))
            st.color_picker("Ampel Grün", key=feld_key("farbe_gruen"))
            st.color_picker("Ampel Gelb", key=feld_key("farbe_gelb"))
            st.color_picker("Ampel Rot", key=feld_key("farbe_rot"))
    with st.sidebar.expander("📐 Layout – Einzelindex", expanded=False):
        _layout_editor_bloecke("ez", BLOCK_LABEL_EZ)
        st.caption("Spaltenbreiten (Ampel · Gauge · Signal-Chips)")
        st.slider("Breite Ampel-Banner", 0.5, 3.0, step=0.1, key=feld_key("ez_spalte_banner"))
        st.slider("Breite Gauge", 0.5, 3.0, step=0.1, key=feld_key("ez_spalte_gauge"))
        st.slider("Breite Signal-Chips", 0.5, 3.0, step=0.1, key=feld_key("ez_spalte_chips"))
        st.caption("Größen")
        st.slider("Höhe Gauge", 120, 260, step=10, key=feld_key("ez_hoehe_gauge"))
        st.slider("Höhe Kurschart", 300, 600, step=10, key=feld_key("ez_hoehe_chart"))
        st.slider("Höhe Was-wäre-wenn-Chart", 250, 550, step=10, key=feld_key("ez_hoehe_www"))
    with st.sidebar.expander("📐 Layout – Überblick", expanded=False):
        _layout_editor_bloecke("ue", BLOCK_LABEL_UE)
        st.caption("Größen")
        st.slider("Höhe Kursverläufe (kompakt)", 200, 400, step=10, key=feld_key("ue_hoehe_kurs"))
        st.slider("Höhe Max-Drawdown-Chart", 250, 500, step=10, key=feld_key("ue_hoehe_maxdd"))
    st.sidebar.button("↩️ Auf Standard zurücksetzen", on_click=_zuruecksetzen, width="stretch")
    st.sidebar.button("💾 Speichern & einfrieren", on_click=_einfrieren, type="primary", width="stretch")
    st.sidebar.caption("Nach dem Einfrieren verschwindet dieser Editor dauerhaft "
                       "(auch nach einem Neustart) und das Layout bleibt fest.")


# ============================================================================
# 8. Hauptprogramm
# ============================================================================
def main():
    st.title("🚦 Risikoampel für US-Aktienindizes")
    st.caption("Eine gemeinsame, indikatorübergreifende Ampel (Grün / Gelb / Rot) für "
               "S&P 500, Dow Jones, NASDAQ 100 und Russell 2000 – berechnet aus "
               "gleitenden Durchschnitten, tagesaktuell aus Kursdaten.")

    with st.sidebar:
        st.header("Ansicht")
        ansicht = st.radio("Auswahl", ["Überblick (alle 4)", "Einzelindex"], index=0,
                           label_visibility="collapsed")
        index_key = None
        if ansicht == "Einzelindex":
            namen = {v["name"]: k for k, v in ac.INDICES.items()}
            index_key = namen[st.selectbox("Index", list(namen.keys()))]

        with st.expander("Wie funktioniert die Ampel?"):
            beispiel = ac.lade_konfiguration("SP500")
            st.markdown(
                "Aus vier einfachen Kursregeln (Kurs unter SMA20/100/200, SMA20 fällt) "
                "wird der **Belastungsgrad** gebildet: der Anteil gerade zutreffender "
                "Regeln (0 bis 1).\n\n"
                f"- **Grün**: Belastungsgrad ≤ {de_num(beispiel['gruen_max'])} (keine Regel belastet)\n"
                f"- **Rot**: Belastungsgrad ≥ {de_num(beispiel['rot_min'])} (alle Regeln belastet)\n"
                "- **Gelb**: dazwischen\n\n"
                "Dieselbe Kombination gilt für alle vier Indizes. Die Was-wäre-wenn-"
                "Simulation steigt an Rot-Tagen aus (Cash, ohne Kosten) und sonst voll ein.")
        st.caption("Daten: Yahoo Finance. Explorativ, keine Anlageberatung.")

        st.divider()
        if not GESPERRT:
            editor_an = st.checkbox("🔧 Dashboard anpassen", key="editor_an_cb")
        else:
            editor_an = False
            st.caption("🔒 Layout ist eingefroren.")

    if editor_an:
        _dashboard_editor()

    if ansicht == "Einzelindex":
        ansicht_einzelindex(index_key)
    else:
        ansicht_ueberblick()


if __name__ == "__main__":
    main()
