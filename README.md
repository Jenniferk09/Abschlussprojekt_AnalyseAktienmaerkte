# 🚦 Risikoampel – Streamlit-App

Interaktive Oberfläche zur kombinierten Risikoampel für vier US-Aktienindizes
(S&P 500, Dow Jones, NASDAQ 100, Russell 2000). Die App zeigt je Index die
**tagesaktuelle Ampel** (Grün/Gelb/Rot), den Kursverlauf mit Ampel-Hintergrund
und eine **Was-wäre-wenn-Simulation** (Buy & Hold vs. Ausstieg bei Rot) mit
CAGR, Max Drawdown und Calmar.

## Starten

```bash
cd streamlit_app
pip install -r requirements.txt
streamlit run app.py
```

Die App öffnet sich im Browser (Standard: http://localhost:8501).

## Aufbau

| Datei | Zweck |
|---|---|
| `app.py` | Streamlit-Oberfläche (Ansichten, Diagramme) |
| `ampel_core.py` | Kernlogik: Kurse/Marktbreite/Volatilität/PCR laden, Signale, Ampel, Was-wäre-wenn – reproduziert `Risikoampel Kombiniert.ipynb` exakt |
| `configs/*_ampel_konfiguration.json` | die im Notebook per Suche (mit Train/Test-Split) bestimmte Ampel-Definition (Signale + Schwellen), je Index |
| `marktbreite_daten/*.csv` | Marktbreite je Index (Anteil Mitglieder über SMA20), gebündelt statt live – siehe "Daten aktuell halten" |
| `pcr_daten.csv` | marktweite Put/Call-Ratio, gebündelt statt live – siehe "Daten aktuell halten" |
| `_referenz/*_Ampel_Zeitreihe.csv` | Referenz-Zeitreihen zur Validierung (aus `ampel_core` selbst erzeugt, da das Notebook keinen fertigen Export mehr bereitstellt) |
| `layout_config.json` | Dashboard-Layout/Design (entsteht erst beim Einfrieren, siehe unten) |
| `requirements.txt` | Abhängigkeiten |

## Dashboard anpassen & einfrieren

In der Sidebar gibt es „🔧 Dashboard anpassen" (nur solange das Layout nicht
eingefroren ist). Dort lassen sich für **beide Ansichten** einstellen:

- **Reihenfolge** der Bausteine (▲/▼) und **Ein-/Ausblenden** einzelner Bausteine
- **Spaltenbreiten** (Einzelindex: Ampel-Banner/Gauge/Signal-Chips) und **Höhen**
  aller Diagramme
- **Schriftgröße**
- **Farben** (Hintergrund, Karten, Text, Akzent, sowie Grün/Gelb/Rot der Ampel)

Alle Änderungen wirken **sofort** (Live-Vorschau). Mit „💾 Speichern & einfrieren"
wird die aktuelle Einstellung in `layout_config.json` geschrieben und der Editor
**dauerhaft** ausgeblendet — auch nach einem Neustart der App. Ein Reset ist dann
nur noch möglich, indem man `layout_config.json` löscht oder das Feld
`"gesperrt": false` darin setzt (bewusst nicht über die Oberfläche zugänglich).
„↩️ Auf Standard zurücksetzen" setzt vor dem Einfrieren alle Werte auf die
Vorgabe zurück (wirkt nur auf die noch nicht gespeicherte Live-Vorschau).

## Methodik (Kurzfassung)

Die Ampel kombiniert **vier Indikator-Familien**: Trend (SMA20/100/200-Regeln
plus Death-Cross-Regime), Marktbreite (Anteil Indexmitglieder über SMA20),
Volatilität (index-eigener Vol-Index über seiner Rot-Schwelle) und Sentiment
(marktweite Put/Call-Ratio im obersten Dezil). Aus den neun gewählten Signalen
wird der **Belastungsgrad** gebildet (Anteil "schlechter" Signale, 0–1). Daraus
die Ampel: **Grün** bei 0 % belastet, **Rot** ab 75 % belastet, **Gelb**
dazwischen. Dieselbe Kombination gilt für alle vier Indizes – im Notebook per
Brute-Force-Suche mit **Train/Test-Split** bestimmt (Suche nur auf Daten bis
2019, unabhängige Validierung ab 2020) und pro Index über ein eigenes
Bewertungsfenster geprüft (erst ab dem Tag, an dem alle Signale für diesen
Index verfügbar sind).

Kurse und die Volatilitätsindizes (VIX/VXD/VXN live über Yahoo Finance, RVX für
Russell 2000 über einen CBOE-Fallback) sind **live** abrufbar und werden je
Index bis zu 6 Stunden gecached. Marktbreite und Put/Call-Ratio sind dagegen
**nicht live verfügbar** (siehe unten) und liegen als mit der App gebündelte
Dateien vor.

## Daten aktuell halten

`marktbreite_daten/*.csv` (je Index) und `pcr_daten.csv` sind TradingView-
Exporte ohne bekannte Live-API und werden **nicht** bei jedem Aufruf neu
geladen. Das hat eine sichtbare Folge: Der "aktuelle Tag" der Ampel fällt
automatisch auf den letzten Tag zurück, an dem alle neun Pflichtsignale
auswertbar sind – bleiben Marktbreite/PCR tagelang unaktualisiert, hinkt die
Ampel entsprechend hinterher (in der App als Datenstand-Hinweis sichtbar).

Zum Aktualisieren: neue Exporte besorgen (je Index die "20 SMA"-Marktbreite-
Datei bzw. die marktweite PCR-Datei), die bestehenden Dateien in
`marktbreite_daten/` bzw. `pcr_daten.csv` ersetzen, committen und auf den
`risikoampel-dashboard`-Branch pushen – Streamlit Cloud deployt automatisch
neu.

## Validierung

`ampel_core` reproduziert die Ampel des Notebooks (Abgleich der Fenster-
Startdaten, Anteil-Rot und Calmar-Größenordnung je Index gegen die
Notebook-Ausgabe). `_referenz/*_Ampel_Zeitreihe.csv` wird direkt aus
`ampel_core` selbst erzeugt (das Notebook liefert seit dem Umbau auf vier
Indikator-Familien keinen fertigen CSV-Export mehr) und dient als
Regressionsbasis für künftige Änderungen.

> Explorative Analyse historischer Daten – keine Anlageberatung.
