# -*- coding: utf-8 -*-
"""Kernlogik der kombinierten Risikoampel.

Diese Funktionen reproduzieren exakt die Methodik aus dem Notebook
``Risikoampel Kombiniert.ipynb`` (Stand nach dem Umbau auf vier
Indikator-Familien, siehe unten): Aus den Kursdaten eines Index werden die
gleitenden Durchschnitte (SMA) und daraus die Ampel-Kandidatensignale
berechnet. Die gewählte, für alle vier Indizes identische Signal-Kombination
und die Ampel-Schwellen stehen in den Konfigurationsdateien unter ``configs/``
(im Notebook per Brute-Force-Suche mit Train/Test-Split bestimmt und
exportiert).

Die gewählte Kombination kombiniert vier Indikator-Familien – Trend (SMA),
Marktbreite, Volatilität und Sentiment (Put/Call-Ratio) – und benötigt daher
zur Laufzeit mehr als nur Kursdaten:
- Kurse und die index-eigenen Volatilitätsindizes (VIX/VXD/VXN live über
  Yahoo Finance, RVX über einen CBOE-CDN-Fallback) werden **live** geladen.
- Marktbreite (Anteil Indexmitglieder über eigenem SMA20) und die
  marktweite Put/Call-Ratio liegen als mit der App gebündelte Dateien vor
  (``marktbreite_daten/``, ``pcr_daten.csv``) – siehe README, Abschnitt
  "Daten aktuell halten". Ohne aktuelle Marktbreite-/PCR-Daten fällt der
  auswertbare "aktuelle Tag" automatisch auf den letzten Tag zurück, an dem
  alle neun Pflichtsignale vorliegen (keine Sonderlogik nötig – NaN
  propagiert bereits durch ``berechne_ampel``/``aktueller_status``).
"""
from __future__ import annotations

import json
import re
import urllib.request
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

CONFIG_DIR = Path(__file__).parent / "configs"
MARKTBREITE_DIR = Path(__file__).parent / "marktbreite_daten"
PCR_DATEI = Path(__file__).parent / "pcr_daten.csv"
START_DATE_ANALYSE = "2007-01-01"
START_DATE_DOWNLOAD = "1900-01-01"

PCR_MA_FENSTER = 10
PCR_MIN_HISTORIE = 252  # ~1 Handelsjahr Vorlauf für ein stabiles Perzentil (expanding window)

# CBOE stellt die offizielle RVX-Tageshistorie bereit, da ^RVX bei Yahoo
# Finance nicht abrufbar ist (siehe Volatilitätsindizes/RVX-Notebook).
RVX_CBOE_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/RVX_History.csv"

AMPEL_FARBEN = ["Grün", "Gelb", "Rot"]
AMPEL_FARBCODES = {"Grün": "#0ca30c", "Gelb": "#e0a72c", "Rot": "#d03b3b"}

# Reihenfolge der Indizes für Überblicksdarstellungen. vol_ticker/vol_local:
# index-eigener Volatilitätsindex (live via Yahoo Finance bzw. CBOE-Fallback
# für RVX); vol_schwelle: datenbasiert hergeleitete Rot-Schwelle je Vol-Index
# (siehe Volatilitätsindizes/*.ipynb).
INDICES = {
    "SP500":       {"name": "S&P 500",      "ticker": "^GSPC",
                    "vol_ticker": "^VIX", "vol_local": False, "vol_schwelle": 30},
    "DowJones":    {"name": "Dow Jones",    "ticker": "^DJI",
                    "vol_ticker": "^VXD", "vol_local": False, "vol_schwelle": 27},
    "NASDAQ100":   {"name": "NASDAQ 100",   "ticker": "^NDX",
                    "vol_ticker": "^VXN", "vol_local": False, "vol_schwelle": 33},
    "Russell2000": {"name": "Russell 2000", "ticker": "^RUT",
                    "vol_ticker": None, "vol_local": True, "vol_schwelle": 34},
}

# Verständliche Beschriftung der Kandidatensignale (Zustand "schlecht", wenn …)
SIGNAL_LABELS = {
    "H1_20":  "Kurs unter SMA20",
    "H1_100": "Kurs unter SMA100",
    "H1_200": "Kurs unter SMA200",
    "H2_20":  "SMA20 fällt",
    "H2_100": "SMA100 fällt",
    "H2_200": "SMA200 fällt",
    "H3_20_200": "Im Death-Cross-Regime (SMA20 < SMA200 seit Kreuzung)",
    "B1_20":  "Marktbreite: <50% der Mitglieder über SMA20",
    "V1_Rot": "Volatilitätsindex über Rot-Schwelle",
    "S1_PCR_Extrem": "Put/Call-Ratio im obersten Dezil (Angst)",
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
    """Ermittelt aus den Signalnamen (H1_x / H2_x / H3_20_200) die nötigen
    SMA-Fenster."""
    fenster = set()
    for name in signale:
        m = re.match(r"H[12]_(\d+)$", name)
        if m:
            fenster.add(int(m.group(1)))
    if "H3_20_200" in signale:
        fenster |= {20, 200}
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


def _fetch_rvx_cboe() -> pd.DataFrame:
    """Lädt die RVX-Tageshistorie von der CBOE (^RVX ist bei Yahoo Finance
    nicht abrufbar) und bringt sie auf dasselbe Schema wie yfinance-Daten."""
    req = urllib.request.Request(RVX_CBOE_URL, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    df = pd.read_csv(StringIO(raw))
    df.columns = [c.strip().title() for c in df.columns]
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    return df


def lade_vol_index(cfg: dict) -> pd.Series:
    """Lädt den index-eigenen Volatilitätsindex: live über Yahoo Finance,
    oder – für RVX (Russell 2000) – über den CBOE-CDN-Fallback."""
    if cfg["vol_local"]:
        v = _fetch_rvx_cboe()
    else:
        v = lade_kurse(cfg["vol_ticker"])
    reihe = v["Close"]
    reihe = reihe[~reihe.index.duplicated(keep="first")].sort_index()
    reihe.name = "vol_close"
    return reihe


def lade_marktbreite(index_key: str) -> pd.Series:
    """Lädt die gebündelte Marktbreite-Datei (Anteil Indexmitglieder über
    eigenem SMA20, TradingView-Export, Stand siehe Dateidatum) als Series."""
    pfad = MARKTBREITE_DIR / f"{index_key}.csv"
    rohdaten = pd.read_csv(pfad, parse_dates=["time"])
    reihe = rohdaten.set_index("time")["close"]
    reihe.index.name = "Date"
    reihe.name = "breite_sma20"
    reihe = reihe[~reihe.index.duplicated(keep="first")].sort_index()
    return reihe


def _expanding_quantil(serie: pd.Series, q: float, min_periods: int = PCR_MIN_HISTORIE) -> pd.Series:
    """Perzentil an Tag T, berechnet ausschließlich aus der bis inklusive T
    bekannten Historie (expanding window) – vermeidet den Rückschaufehler
    eines einmalig über die gesamte Zeitreihe berechneten Quantils."""
    return serie.expanding(min_periods=min_periods).quantile(q)


def lade_pcr_signal() -> pd.Series:
    """Lädt die (marktweite) Equity-Put/Call-Ratio und markiert Tage im
    obersten Dezil ihres gleitenden 10-Tage-Durchschnitts (expanding-
    Perzentil, kein Rückschaufehler) als "schlecht" (1.0)."""
    roh = pd.read_csv(PCR_DATEI, parse_dates=["time"])
    reihe = roh.set_index("time")["close"]
    reihe.index.name = "Date"
    reihe = reihe[~reihe.index.duplicated(keep="first")].sort_index()
    reihe = reihe.where(reihe > 0)
    ma = reihe.rolling(PCR_MA_FENSTER, min_periods=PCR_MA_FENSTER).mean()
    p90 = _expanding_quantil(ma, 0.90)
    signal = (ma >= p90).astype(float).where(p90.notna())
    signal.name = "pcr_signal"
    return signal


# --------------------------------------------------------------------------- #
# Signale, Belastungsgrad, Ampel
# --------------------------------------------------------------------------- #
def _finde_crossover(sma_kurz: pd.Series, sma_lang: pd.Series) -> tuple[pd.Series, pd.Series]:
    golden = (sma_kurz.shift(1) <= sma_lang.shift(1)) & (sma_kurz > sma_lang)
    death = (sma_kurz.shift(1) >= sma_lang.shift(1)) & (sma_kurz < sma_lang)
    return golden, death


def _crossover_regime_schlecht(golden: pd.Series, death: pd.Series) -> pd.Series:
    ereignis = pd.Series(np.nan, index=golden.index, dtype="object")
    ereignis[golden] = False
    ereignis[death] = True
    return ereignis.ffill().fillna(False).astype(bool)


def berechne_signal_matrix(df: pd.DataFrame, signale: list[str]) -> pd.DataFrame:
    """Berechnet je gewähltem Kandidatensignal eine Spalte: 1.0 = "schlecht",
    0.0 = "gut", NaN = an diesem Tag nicht auswertbar (z. B. SMA-Anlaufzeit,
    vor Beginn der Marktbreite-/Vol-Index-/PCR-Historie).

    H1_w: Schlusskurs liegt unter dem SMA_w.
    H2_w: SMA_w fällt gegenüber dem Vortag.
    H3_20_200: Kurs befindet sich seit dem letzten "Death Cross" (SMA20
        kreuzt SMA200 von oben nach unten) im ungünstigen Regime.
    B1_20: weniger als 50% der Indexmitglieder notieren über ihrem SMA20.
    V1_Rot: index-eigener Volatilitätsindex liegt über der Rot-Schwelle.
    S1_PCR_Extrem: Put/Call-Ratio liegt im obersten Dezil (vorberechnet in
        ``df["pcr_signal"]``, siehe ``lade_pcr_signal``).
    """
    sig = {}
    for w in benoetigte_sma_fenster(signale):
        sma = df[f"SMA{w}_d"]
        if f"H1_{w}" in signale:
            sig[f"H1_{w}"] = (df["Close"] <= sma).astype(float).where(sma.notna())
        if f"H2_{w}" in signale:
            diff_w = sma.diff()
            sig[f"H2_{w}"] = (diff_w <= 0).astype(float).where(diff_w.notna())

    if "H3_20_200" in signale and "SMA20_d" in df.columns and "SMA200_d" in df.columns:
        golden, death = _finde_crossover(df["SMA20_d"], df["SMA200_d"])
        sig["H3_20_200"] = _crossover_regime_schlecht(golden, death).astype(float)

    if "B1_20" in signale and "breite_sma20" in df.columns:
        roh = (df["breite_sma20"] <= 50).astype(float)
        sig["B1_20"] = roh.where(df["breite_sma20"].notna())

    if "V1_Rot" in signale and "vol_close" in df.columns:
        sig["V1_Rot"] = (df["vol_close"] >= df["vol_schwelle"]).astype(float).where(df["vol_close"].notna())

    if "S1_PCR_Extrem" in signale and "pcr_signal" in df.columns:
        sig["S1_PCR_Extrem"] = df["pcr_signal"]

    return pd.DataFrame({name: sig[name] for name in signale if name in sig}, index=df.index)


def ampel_aus_belastungsgrad(grad: pd.Series, gruen_max: float, rot_min: float) -> pd.Series:
    ampel = pd.Series(np.nan, index=grad.index, dtype=object)
    v = grad.notna()
    ampel[v & (grad <= gruen_max)] = "Grün"
    ampel[v & (grad >= rot_min)] = "Rot"
    ampel[v & (grad > gruen_max) & (grad < rot_min)] = "Gelb"
    return ampel


def berechne_ampel(df_kurse: pd.DataFrame, konfiguration: dict,
                   breite: pd.Series | None = None, vol: pd.Series | None = None,
                   vol_schwelle: float | None = None, pcr: pd.Series | None = None) -> pd.DataFrame:
    """Wendet die Ampel-Konfiguration auf die Kursdaten an und liefert einen
    DataFrame ab 2007 mit Close, SMA-Spalten, den Signalen, Belastungsgrad und
    Ampel. Reproduziert die Reihenfolge des Notebooks: erst auf 2007 schneiden,
    dann die SMAs berechnen, dann Marktbreite/Vol/PCR links joinen (volle
    Kurs-Historie bleibt erhalten, auch wenn eine Zusatzreihe erst später
    beginnt – die betroffenen Tage werden erst beim jeweiligen Signal NaN)."""
    signale = konfiguration["signale"]
    df = df_kurse.loc[START_DATE_ANALYSE:].copy()

    for w in benoetigte_sma_fenster(signale):
        df[f"SMA{w}_d"] = df["Close"].rolling(window=w, min_periods=w).mean()

    if breite is not None:
        df = df.join(breite.rename("breite_sma20"), how="left")
    if vol is not None:
        df = df.join(vol.rename("vol_close"), how="left")
        df["vol_schwelle"] = vol_schwelle
    if pcr is not None:
        df = df.join(pcr.rename("pcr_signal"), how="left")

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

    Getrenntes Bewertungsfenster: Gesamtrendite/CAGR/Max Drawdown werden nur
    ab dem ersten Tag berechnet, an dem die Ampel überhaupt auswertbar ist
    (nicht NaN) - sonst würde eine Kombination mit später startendem Signal
    (z. B. Marktbreite/Vol-Index beim Russell 2000) für die Vorperiode
    implizit als ungeschütztes Buy & Hold behandelt, was den Drawdown-
    Vergleich verzerrt (dieselbe Logik wie im Notebook).
    """
    schlecht_reindiziert = (df["Ampel"] == "Rot").reindex(df.index).where(df["Ampel"].notna())
    valide = schlecht_reindiziert.notna()
    start = valide.idxmax() if valide.any() else df.index[0]
    df = df.loc[start:]

    tagesrendite = df["Close"].pct_change().fillna(0)
    schlecht = schlecht_reindiziert.loc[start:].fillna(False).astype(bool)
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
    """Lädt Kurse, Marktbreite, Volatilitätsindex und PCR, berechnet Ampel und
    Was-wäre-wenn und liefert alles gebündelt (inkl. Datenstand der
    gebündelten, nicht-live nachgeladenen Marktbreite-/PCR-Dateien)."""
    cfg = lade_konfiguration(index_key)
    meta = INDICES[index_key]
    signale = cfg["signale"]

    kurse = lade_kurse(meta["ticker"])
    breite = lade_marktbreite(index_key) if "B1_20" in signale else None
    vol = lade_vol_index(meta) if "V1_Rot" in signale else None
    pcr = lade_pcr_signal() if "S1_PCR_Extrem" in signale else None

    df = berechne_ampel(kurse, cfg, breite=breite, vol=vol,
                        vol_schwelle=meta.get("vol_schwelle"), pcr=pcr)
    www = was_waere_wenn(df)
    status = aktueller_status(df, signale)
    return {"index_key": index_key, "name": meta["name"], "ticker": meta["ticker"],
            "konfiguration": cfg, "df": df, "was_waere_wenn": www, "status": status,
            "marktbreite_stand": breite.index.max() if breite is not None else None,
            "pcr_stand": pcr.index.max() if pcr is not None else None}
