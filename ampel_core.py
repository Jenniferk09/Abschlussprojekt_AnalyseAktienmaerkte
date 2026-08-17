# -*- coding: utf-8 -*-
"""Kernlogik der kombinierten Risikoampel.

Diese Funktionen reproduzieren exakt die Methodik aus dem Notebook
``Risikoampel Kombiniert.ipynb``: Aus den Kursdaten eines Index werden die
gleitenden Durchschnitte (SMA) und daraus die Ampel-Kandidatensignale
berechnet. Die gewählte, für alle vier Indizes identische Signal-Kombination
und die Ampel-Schwellen stehen in den Konfigurationsdateien unter ``configs/``
(im Notebook per Brute-Force-Suche bestimmt und exportiert).

Die gewählte Kombination ist rein kursbasiert (H1_20/H1_100/H1_200/H2_20),
daher benötigt die Ampel zur Laufzeit **nur Kursdaten** (yfinance) – keine
Marktbreite- oder Put/Call-Daten.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

CONFIG_DIR = Path(__file__).parent / "configs"
START_DATE_ANALYSE = "2007-01-01"
START_DATE_DOWNLOAD = "1900-01-01"

AMPEL_FARBEN = ["Grün", "Gelb", "Rot"]
AMPEL_FARBCODES = {"Grün": "#0ca30c", "Gelb": "#e0a72c", "Rot": "#d03b3b"}

# Reihenfolge der Indizes für Überblicksdarstellungen
INDICES = {
    "SP500":       {"name": "S&P 500",      "ticker": "^GSPC"},
    "DowJones":    {"name": "Dow Jones",    "ticker": "^DJI"},
    "NASDAQ100":   {"name": "NASDAQ 100",   "ticker": "^NDX"},
    "Russell2000": {"name": "Russell 2000", "ticker": "^RUT"},
}

# Verständliche Beschriftung der Kandidatensignale (Zustand "schlecht", wenn …)
SIGNAL_LABELS = {
    "H1_20":  "Kurs unter SMA20",
    "H1_100": "Kurs unter SMA100",
    "H1_200": "Kurs unter SMA200",
    "H2_20":  "SMA20 fällt",
    "H2_100": "SMA100 fällt",
    "H2_200": "SMA200 fällt",
}


# --------------------------------------------------------------------------- #
# Konfiguration
# --------------------------------------------------------------------------- #
def lade_konfiguration(index_key: str) -> dict:
    """Lädt die im Notebook exportierte Ampel-Konfiguration eines Index."""
    pfad = CONFIG_DIR / f"{index_key}_ampel_konfiguration.json"
    with open(pfad, encoding="utf-8") as f:
        return json.load(f)


def benoetigte_sma_fenster(signale: list[str]) -> list[int]:
    """Ermittelt aus den Signalnamen (H1_x / H2_x) die nötigen SMA-Fenster."""
    fenster = set()
    for name in signale:
        m = re.match(r"H[12]_(\d+)$", name)
        if m:
            fenster.add(int(m.group(1)))
    return sorted(fenster)


# --------------------------------------------------------------------------- #
# Kursdaten
# --------------------------------------------------------------------------- #
def lade_kurse(ticker: str, start: str = START_DATE_DOWNLOAD) -> pd.DataFrame:
    """Lädt Tages-Kursdaten von Yahoo Finance (wie im Notebook:
    auto_adjust=False), bereinigt Duplikate und schließt kleine Lücken."""
    raw = yf.download(ticker, start=start, auto_adjust=False, actions=False,
                      progress=False)
    if raw.empty:
        raise ValueError(f"Keine Daten für '{ticker}' erhalten – Internetverbindung prüfen.")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw.columns.name = None
    raw.index.name = "Date"

    df = raw[~raw.index.duplicated(keep="first")].sort_index()
    letzter_valider = df["Close"].last_valid_index()
    if letzter_valider is not None:
        df = df.loc[:letzter_valider]
    df["Close"] = df["Close"].interpolate(method="time", limit=2)
    return df


# --------------------------------------------------------------------------- #
# Signale, Belastungsgrad, Ampel
# --------------------------------------------------------------------------- #
def berechne_signal_matrix(df: pd.DataFrame, signale: list[str]) -> pd.DataFrame:
    """Berechnet je gewähltem Kandidatensignal eine Spalte: 1.0 = "schlecht",
    0.0 = "gut", NaN = an diesem Tag nicht auswertbar (SMA-Anlaufzeit).

    H1_w: Schlusskurs liegt unter dem SMA_w.
    H2_w: SMA_w fällt gegenüber dem Vortag.
    """
    sig = {}
    for w in benoetigte_sma_fenster(signale):
        sma = df[f"SMA{w}_d"]
        if f"H1_{w}" in signale:
            sig[f"H1_{w}"] = (df["Close"] <= sma).astype(float).where(sma.notna())
        if f"H2_{w}" in signale:
            diff_w = sma.diff()
            sig[f"H2_{w}"] = (diff_w <= 0).astype(float).where(diff_w.notna())
    return pd.DataFrame({name: sig[name] for name in signale if name in sig}, index=df.index)


def ampel_aus_belastungsgrad(grad: pd.Series, gruen_max: float, rot_min: float) -> pd.Series:
    ampel = pd.Series(np.nan, index=grad.index, dtype=object)
    v = grad.notna()
    ampel[v & (grad <= gruen_max)] = "Grün"
    ampel[v & (grad >= rot_min)] = "Rot"
    ampel[v & (grad > gruen_max) & (grad < rot_min)] = "Gelb"
    return ampel


def berechne_ampel(df_kurse: pd.DataFrame, konfiguration: dict) -> pd.DataFrame:
    """Wendet die Ampel-Konfiguration auf die Kursdaten an und liefert einen
    DataFrame ab 2007 mit Close, SMA-Spalten, den Signalen, Belastungsgrad und
    Ampel. Reproduziert die Reihenfolge des Notebooks: erst auf 2007 schneiden,
    dann die SMAs berechnen."""
    signale = konfiguration["signale"]
    df = df_kurse.loc[START_DATE_ANALYSE:].copy()

    for w in benoetigte_sma_fenster(signale):
        df[f"SMA{w}_d"] = df["Close"].rolling(window=w, min_periods=w).mean()

    sig_df = berechne_signal_matrix(df, signale)
    df = df.join(sig_df)

    valide = sig_df.notna().all(axis=1)
    grad = sig_df.mean(axis=1).where(valide)
    df["Belastungsgrad"] = grad
    df["Ampel"] = ampel_aus_belastungsgrad(
        grad, konfiguration["gruen_max"], konfiguration["rot_min"]
    )
    return df


# --------------------------------------------------------------------------- #
# Was-wäre-wenn-Simulation
# --------------------------------------------------------------------------- #
def _historischer_max_drawdown(werte: np.ndarray) -> float:
    laufendes_hoch = np.maximum.accumulate(werte)
    return float((werte / laufendes_hoch - 1).min())


def was_waere_wenn(df: pd.DataFrame) -> dict:
    """Simuliert die Ampel-Strategie: An Rot-Tagen wird das Kapital aus dem
    Markt genommen (Cash, ohne Verzinsung/Kosten), sonst voll investiert. Das
    Signal wird um einen Handelstag verzögert angewendet (Entscheidung am
    Vortagsschluss → kein Blick-in-die-Zukunft-Fehler). Vergleich mit Buy & Hold.
    """
    tagesrendite = df["Close"].pct_change().fillna(0)
    schlecht = (df["Ampel"] == "Rot").reindex(df.index).fillna(False)
    schlecht_ausfuehrbar = schlecht.shift(1).fillna(False).astype(bool)

    strategie_rendite = tagesrendite.where(~schlecht_ausfuehrbar, 0.0)
    equity_bh = (1 + tagesrendite).cumprod()
    equity_st = (1 + strategie_rendite).cumprod()

    jahre = (df.index[-1] - df.index[0]).days / 365.25

    def kennzahlen(equity: pd.Series) -> dict:
        werte = equity.values
        gesamt = float(werte[-1] - 1)
        cagr = float(werte[-1] ** (1 / jahre) - 1)
        mdd = _historischer_max_drawdown(werte)
        return {"gesamtrendite": gesamt, "cagr": cagr, "max_drawdown": mdd,
                "calmar": (cagr / abs(mdd) if mdd != 0 else float("nan"))}

    return {
        "anteil_rot": float(schlecht.mean()),
        "equity_buy_hold": equity_bh,
        "equity_strategie": equity_st,
        "buy_hold": kennzahlen(equity_bh),
        "strategie": kennzahlen(equity_st),
    }


# --------------------------------------------------------------------------- #
# Aktueller Status
# --------------------------------------------------------------------------- #
def aktueller_status(df: pd.DataFrame, signale: list[str]) -> dict:
    """Liefert den jüngsten auswertbaren Ampeltag samt Signal-Aufschlüsselung."""
    auswertbar = df["Ampel"].notna()
    if not auswertbar.any():
        raise ValueError("Keine auswertbaren Ampeltage vorhanden.")
    letzter = df.index[auswertbar][-1]
    zeile = df.loc[letzter]
    signal_status = []
    for name in signale:
        wert = zeile.get(name, np.nan)
        signal_status.append({
            "signal": name,
            "label": SIGNAL_LABELS.get(name, name),
            "schlecht": bool(wert == 1.0) if pd.notna(wert) else None,
        })
    return {
        "datum": letzter,
        "ampel": zeile["Ampel"],
        "belastungsgrad": float(zeile["Belastungsgrad"]),
        "close": float(zeile["Close"]),
        "signale": signal_status,
        "n_schlecht": int(sum(1 for s in signal_status if s["schlecht"])),
        "n_signale": len(signale),
    }


def status_fuer_tag(df: pd.DataFrame, signale: list[str], ts) -> dict:
    """Wie ``aktueller_status``, aber für einen frei wählbaren Tag (z. B. den im
    Chart angeklickten). Der nächstgelegene vorhandene Handelstag wird verwendet."""
    ts = pd.Timestamp(ts)
    if ts in df.index:
        idx = ts
    else:
        pos = df.index.get_indexer([ts], method="nearest")[0]
        idx = df.index[pos]
    zeile = df.loc[idx]
    signal_status = []
    for name in signale:
        wert = zeile.get(name, np.nan)
        signal_status.append({
            "signal": name, "label": SIGNAL_LABELS.get(name, name),
            "schlecht": bool(wert == 1.0) if pd.notna(wert) else None,
        })
    bel = zeile["Belastungsgrad"]
    ampel = zeile["Ampel"] if isinstance(zeile["Ampel"], str) else "—"
    return {
        "datum": idx, "ampel": ampel,
        "belastungsgrad": float(bel) if pd.notna(bel) else float("nan"),
        "close": float(zeile["Close"]), "signale": signal_status,
        "n_schlecht": int(sum(1 for s in signal_status if s["schlecht"])),
        "n_signale": len(signale),
    }


def ampel_phasen(df: pd.DataFrame) -> list[dict]:
    """Fasst aufeinanderfolgende Tage gleicher Ampelfarbe zu Phasen zusammen
    (für die Hintergrundflächen im Chart). Nicht auswertbare Tage werden
    übersprungen."""
    a = df["Ampel"].dropna()
    if a.empty:
        return []
    wechsel = (a != a.shift()).cumsum()
    phasen = []
    for _, gruppe in a.groupby(wechsel):
        phasen.append({"farbe": gruppe.iloc[0],
                       "start": gruppe.index[0], "ende": gruppe.index[-1]})
    return phasen


# --------------------------------------------------------------------------- #
# Komfort: alles für einen Index in einem Aufruf
# --------------------------------------------------------------------------- #
def analysiere_index(index_key: str) -> dict:
    """Lädt Kurse, berechnet Ampel und Was-wäre-wenn und liefert alles gebündelt."""
    cfg = lade_konfiguration(index_key)
    meta = INDICES[index_key]
    kurse = lade_kurse(meta["ticker"])
    df = berechne_ampel(kurse, cfg)
    www = was_waere_wenn(df)
    status = aktueller_status(df, cfg["signale"])
    return {"index_key": index_key, "name": meta["name"], "ticker": meta["ticker"],
            "konfiguration": cfg, "df": df, "was_waere_wenn": www, "status": status}
