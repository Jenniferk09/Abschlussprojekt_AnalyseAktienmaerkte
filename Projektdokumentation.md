# Projektdokumentation — Claude-Code-Arbeitsprotokoll

Diese Datei protokolliert alle Erkenntnisse und Empfehlungen aus den
Claude-Code-Sessions zu diesem Projekt (automatisierte Morgen-Routine +
Opportunity Screener). Sie wird am Ende jeder Session um einen neuen
Abschnitt ergänzt, bestehende Abschnitte werden nicht rückwirkend verändert.

> **Hinweis zur Pflege:** Ich (Claude Code) aktualisiere diese Datei jeweils
> am Ende einer Session, in der ich an diesem Projekt arbeite — das
> funktioniert zuverlässig innerhalb einer laufenden Session, aber nicht
> vollautomatisch im Hintergrund zwischen Sessions (dafür bräuchte es einen
> separat einzurichtenden Hook). Falls eine Session ohne Update endet, bitte
> beim nächsten Mal kurz einfordern.

---

## Session 1 — 2026-08-04

### Ausgangslage
- `01_SP500_Blaupause.ipynb` wurde in einer Cloud-Sandbox ohne Internetzugriff
  erstellt und nur gegen synthetische Daten getestet.
- Aufgabe: gegen echte yfinance-Daten verifizieren, Fehler beheben, auf die
  übrigen 6 Indizes übertragen, Daten reproduzierbar exportieren.

### Arbeitsschritte
1. Python-3.13-venv angelegt (`.venv/`), Pakete installiert: yfinance,
   pandas, numpy, scipy, matplotlib, openpyxl, pyarrow, ipykernel, nbclient,
   nbformat, jupyter_client, notebook.
2. `01_SP500_Blaupause.ipynb` zellweise gegen echten yfinance-Download
   (`^GSPC`) ausgeführt und Fehler behoben (siehe Erkenntnisse unten).
3. Datenqualitätsprüfung (Duplikate, fehlende Werte, Handelstage-Lücken,
   Ausreißer) gegen echte Daten validiert.
4. Notebook für die übrigen 6 Indizes dupliziert: `02_DowJones.ipynb`,
   `03_NASDAQ100.ipynb`, `04_Russell2000.ipynb`, `05_Nikkei225.ipynb`,
   `06_EuroStoxx50.ipynb`, `07_DAX.ipynb`. Alle 7 Notebooks laufen
   end-to-end fehlerfrei.
5. Roh- und bereinigte Daten je Index als CSV + Parquet gespeichert
   (`data/`), inkl. Metadaten-JSON mit Abrufdatum.
6. Auf Nutzeranfrage: zusätzlich Excel-Export (`.xlsx`) für Roh- und
   bereinigte Daten in allen 7 Notebooks ergänzt (Grund: Trennzeichen-/
   Dezimaltrennzeichen-Probleme beim CSV-Import in landesspezifisch
   konfiguriertem Excel — `.xlsx` umgeht das komplett, da kein Textformat).
7. Gap-Analyse durchgeführt: eigenständig erstelltes Team-Notebook
   `01_sma_regime_analysis.ipynb` (SMA20/50-Regimeanalyse) gegen die
   Blaupause verglichen. Ergebnis als Artifact veröffentlicht (Link ggf. bei
   Bedarf erneut anfragen, da sessiongebunden).
8. Auf Nutzeranfrage: Ergebnistabellen der vier Hypothesentests (H1–H4) für
   S&P 500 als Export ergänzt — `S&P_500_hypothesentests.xlsx`
   (4 Tabellenblätter) + 4 Einzel-CSVs. Export enthält bewusst alle Spalten
   aus `vergleiche_gruppen()` (inkl. `n_a`/`n_b`, Median, Std), nicht nur die
   im Notebook zur Anzeige gewählte Teilmenge.
9. Auf Nutzeranfrage: `H1_Preis_vs_SMA`-Tabelle spaltenweise erklärt, inkl.
   vertiefter Erläuterung zu `std_a`/`std_b`.
10. Auf Nutzeranfrage: `H2_SMA_Richtung`-Tabelle erklärt, inkl. Vergleich zu
    H1 (überlappende, aber nicht identische Signale).
11. Auf Nutzeranfrage: Signifikanz-Herleitung insgesamt erklärt — einmal
    entlang des tatsächlichen Codes (`vergleiche_gruppen()`: Mindeststich-
    probe n≥10, Welch-t-Test, Mann-Whitney-U, UND-Verknüpfung, Autokorre-
    lations-Vorbehalt), einmal stark vereinfacht für fachfremdes Publikum
    (Analogien: Münzwurf, Röntgenbild-Zweitmeinung, Wettlauf mit Ausreißer-
    Läufer).
12. Auf Nutzeranfrage: `H3_CrossOver`-Tabelle erklärt.
13. Auf Nutzeranfrage: `H4_Divergenz`-Tabelle erklärt.

### Erkenntnisse (aus echten Daten, mit synthetischen Daten nicht erkennbar)

- **Unvollständiger letzter Handelstag:** Der jeweils jüngste Handelstag
  hatte teils bereits Open/High/Low/Volume, aber noch keinen final
  abgerechneten Close (Yahoo-Datenpipeline-Lag). Die ursprüngliche Logik
  hätte das per Zeit-Interpolation stillschweigend mit dem Vortages-Close
  aufgefüllt → inkonsistenter Datenpunkt. **Fix:** Zeile wird jetzt explizit
  erkannt (`last_valid_index()` auf `Close`) und verworfen statt
  interpoliert, mit Klartext-Meldung im Notebook-Output.
- **`columns.name = "Price"`-Artefakt** aus dem yfinance-MultiIndex-
  Flattening entfernt (rein kosmetisch, aber verwirrend in jeder Ausgabe).
- **Abrufdatum war nicht persistiert**, nur `print`-Ausgabe. Fix: pro Index
  wird `<Index>_raw_meta.json` gespeichert (Ticker, Abrufdatum, Zeitraum,
  yfinance-Version).
- **Datenqualitätslogik bestätigt korrekt:** Alle gefundenen
  Kalenderlücken (>4 Tage) sind reale Börsenschließungen — 1933 US-Bank-
  Holiday, 9/11-Schließung 2001 (US-Indizes), japanisches Neujahr und
  Golden Week (Nikkei). Keine Schwellenwert-Anpassung nötig.
- **Index-Besonderheiten aus `Datenverfügbarkeit.xlsx` bestätigt, aber ohne
  Fehler:** Nikkei-Zeitzone/-Kalender, DAX als Performanceindex,
  EuroStoxx-Datenlücken (bei diesem Abruf keine NaNs aufgetreten), Russell
  2000 Volumen häufig 0.
- **`std_a`/`std_b` in den H1-Ergebnistabellen ist ein Unsicherheits-, kein
  Richtungsmaß:** Über alle SMA-Fenster/Horizonte ist `std_b` (Kurs unter
  SMA) durchgehend größer als `std_a` (Kurs über SMA) — bei SMA200/90 Tage
  fast doppelt so groß (13,8 % vs. 6,9 %). Die Streuung wächst sowohl mit
  dem Prognosehorizont als auch mit der Länge des SMA-Fensters. Interpretation:
  „unterhalb des Trends“ zu liegen ist strukturell unsicherer/breiter
  gestreut in den Ergebnissen als „oberhalb“ — unabhängig vom Mittelwert.
- **H2 (SMA-Richtung) ist kein Duplikat von H1:** Der Drawdown-Effekt ist bei
  jedem SMA-Fenster (20/100/200) durchgehend signifikant. Der Rendite-
  Effekt ist dagegen nur bei SMA20 signifikant — bei SMA100/SMA200
  verschwindet er praktisch vollständig (alle 6 `fwd_return`-Zeilen dort
  nicht signifikant). Selbst der schwache Rendite-Effekt, den H1 für
  „Kurs>SMA200, 90 Tage“ noch zeigte, ist in H2 („SMA200 steigend“) nicht
  mehr signifikant (u_pvalue 0,032 → 0,118). Fazit: SMA-Richtung ist über
  alle Fenster ein robustes Risikosignal, aber nur beim schnellen SMA20
  auch ein Renditesignal.
- **H3 (Cross-Over): nur 12 von 54 möglichen Zeilen testbar.** Von 9
  konfigurierten SMA-Paaren (Tages-/Wochen-/Monatsbasis) erreichen nur
  SMA20/100 (Tage, 25/25 Ereignisse seit 2007) und SMA20/200 (Tage, 11/11
  Ereignisse) die Mindeststichprobe von 10 – alle Wochen-/Monatsbasis-Paare
  und sogar SMA100/200 (Tage) sind schlicht zu selten. Rendite-Unterschied
  bei keinem der beiden testbaren Paare signifikant; Drawdown-Unterschied
  nur bei SMA20/200 und dort nur knapp (p zwischen 0,017 und 0,042).
- **H4 (Divergenz): D2-Muster (Wochen/Monat) mit nur 2 Ereignissen seit 2007
  komplett nicht testbar**, fällt aus der Tabelle. D1-Muster (12 Ereignisse)
  zeigt trotz kleiner Stichprobe ein signifikant geringeres Drawdown-Risiko
  in den folgenden 30–60 Tagen (30 Tage: −2,9 % vs. −5,1 % Basisrate an
  einem x-beliebigen Tag), aber keinen signifikanten Renditeunterschied;
  bei 90 Tagen verwässert sich auch der Drawdown-Effekt (t signifikant,
  u nicht → insgesamt nicht signifikant nach UND-Regel).
- **Übergreifendes Muster über alle vier Hypothesen:** Der Drawdown-/
  Risiko-Effekt ist fast durchgehend robuster und häufiger signifikant als
  der Rendite-Effekt. Hinweis, dass diese SMA-basierten Signale in den
  echten Daten eher als Risiko-Frühwarnung denn als Renditeprognose
  taugen.

### Empfehlungen

- **Priorität hoch — Team-Abstimmung:** Analysezeitraum vereinheitlichen.
  Team-Notebook (`01_sma_regime_analysis.ipynb`) startet 2010, Blaupause
  (und Aufgabenstellung) 2007 (deckt Finanzkrise 2008 ab). Ergebnisse sind
  auf dieser Basis nicht direkt vergleichbar.
- **Priorität hoch:** Kurze Prognosehorizonte (1/5 Handelstage) zusätzlich zu
  30/60/90 in die Blaupause aufnehmen — näher an der eigentlichen
  Fragestellung einer täglichen Morgen-Routine.
- **Priorität mittel:** SMA20/50 als zusätzliches Cross-Over-Paar in
  `crossover_paare` (Tagesbasis) ergänzen — aus dem Team-Notebook
  übernommen, mit bestehender Infrastruktur umsetzbar.
- **Priorität niedrig:** Bibliotheksversionen team-weit vereinheitlichen und
  dokumentieren (Team-Notebook nutzt leicht andere Versionen, z. B. pandas
  3.0.3 vs. 3.0.5 in dieser venv).
- **Diskussionswürdig:** `std` (Streuung) als eigenständiger Risiko-/
  Unsicherheits-Indikator für die Ampel-Logik prüfen — unabhängig von der
  Richtungsfrage (Mittelwert positiv/negativ), die bereits über H1–H4
  abgedeckt ist.
- Log-Renditen, Regimewechsel-Zähler, LaTeX-Formeln aus dem Team-Notebook:
  optional, kein Blocker (siehe Gap-Analyse für Details).
- **Vorsicht bei H3/H4 als alleinige Ampel-Signale:** sehr kleine
  Ereigniszahlen (11–25 bei H3, nur 12 bei H4-D1, D2 gar nicht testbar).
  Ergebnisse eher deskriptiv als robust bestätigt behandeln, nicht als
  gleichwertig zu H1/H2 (dort tausende Beobachtungen) gewichten.
- Durchgängigen Befund „SMA-Signale sagen mehr über Risiko/Drawdown als
  über Rendite aus" (siehe Erkenntnisse) für das Ampel-Konzept nutzen:
  Risiko-Einschätzung und Rendite-Erwartung ggf. getrennt modellieren statt
  in einer Kennzahl zu vermischen.

### Offene Punkte / Backlog

- Hypothesentabellen-Export (H1–H4, CSV + Excel) ist bisher nur für S&P 500
  umgesetzt — auf Wunsch auf die anderen 6 Indizes übertragen.
- Empfehlungen aus der Gap-Analyse (kurze Horizonte, SMA20/50-Paar,
  Basisraten) sind dokumentiert, aber noch nicht in die Blaupause
  eingebaut — warten auf Freigabe durchs Team.
- `notebooks/01_DowJones_Blueprint.ipynb` liegt zusätzlich im Projektordner
  (Ursprung/Status bisher nicht geklärt) — bei Bedarf abgleichen, ob das
  noch gebraucht wird oder ein Altstand ist.
- Die H1–H4-Erläuterungen (Spaltenbedeutung, Signifikanz-Herleitung,
  Kernbefunde) existieren bisher nur als Chat-Antworten in dieser Session,
  nicht als eigenes Dokument — bei Bedarf für den Projektbericht/die Abgabe
  zusammenfassen und schriftlich fixieren.
