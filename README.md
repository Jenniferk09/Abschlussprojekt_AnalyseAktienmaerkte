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
| `ampel_core.py` | Kernlogik: Kurse laden, Signale, Ampel, Was-wäre-wenn – reproduziert `Risikoampel Kombiniert.ipynb` exakt |
| `configs/*_ampel_konfiguration.json` | die im Notebook per Suche bestimmte Ampel-Definition (Signale + Schwellen), je Index |
| `_referenz/*_Ampel_Zeitreihe.csv` | Referenz-Zeitreihen aus dem Notebook, nur zur Validierung |
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

Die Ampel ist **rein kursbasiert**. Aus vier Regeln – Kurs unter SMA20 / SMA100 /
SMA200 und fallender SMA20 – wird der **Belastungsgrad** gebildet (Anteil gerade
zutreffender Regeln, 0–1). Daraus die Ampel: **Grün** = 0 belastet, **Rot** =
alle 4 belastet, **Gelb** dazwischen. Dieselbe Kombination gilt für alle vier
Indizes (im Notebook per Brute-Force-Suche über das Calmar-Kriterium bestimmt).

Weil die Definition nur Kurse braucht (keine Marktbreite-/Put-Call-Daten), ist
die Ampel **live** aus Yahoo-Finance-Kursdaten berechenbar. Die Kurse werden je
Index bis zu 6 Stunden gecached.

## Validierung

`ampel_core` reproduziert die Ampel des Notebooks zu **100 %** (Abgleich gegen
`_referenz/*_Ampel_Zeitreihe.csv`, ~4.700 Handelstage je Index).

> Explorative Analyse historischer Daten – keine Anlageberatung.
