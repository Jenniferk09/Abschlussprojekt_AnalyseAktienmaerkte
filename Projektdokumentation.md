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
14. Auf Nutzeranfrage: Notebook um **Abschnitt 13** (Regime-EDA: prozentuale
    Verteilung, Laufzeiten-Histogramm, Kursverlauf mit Regime-Hintergrund,
    Rendite-/Drawdown-Verteilung je Regime, Streuung je Regime über alle
    Horizonte als Boxplot) und **Abschnitt 14** (hypothesenübergreifende
    Effektgrößen-Visualisierung + Robustheits-Tabelle) erweitert — als
    Entscheidungsgrundlage für die Ampel-Parameterwahl. Bisher nur für
    S&P 500 umgesetzt, wartet auf Team-Review vor Übertragung auf die
    anderen 6 Indizes. Farbwahl (Blau/Orange statt Grün/Rot für die beiden
    Regime-Zustände) bewusst gegen CVD-Validator geprüft, siehe Erkenntnisse.
15. Beim Bauen der neuen Abschnitte zwei technische Bugs gefunden und in den
    neuen Zellen behoben (siehe Erkenntnisse).
16. Export-Zelle für die Hypothesentabellen (`hypexp02`, schreibt
    `S&P_500_hypothesentests.xlsx`) beim Neu-Ausführen des Notebooks bewusst
    übersprungen, um vom Team dort ergänzte Anmerkungen/Screenshots nicht zu
    überschreiben. Dafür eigenes Skript geschrieben, das einzelne Zellen
    gezielt von der Ausführung ausspart, den Rest aber normal durchlaufen
    lässt.

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
- **Regime-Zuordnungsfehler an den ersten Handelstagen entdeckt:** Die
  ersten `sma_fenster` Handelstage nach 2007-01-01 haben noch keinen
  gültigen SMA-Wert (Rolling-Window-Anlauf, betrifft v. a. SMA200: die
  ersten 199 Tage). `Close > SMA` wertet einen Vergleich mit `NaN` in
  pandas als `False` aus — diese Tage wurden dadurch bisher fälschlich der
  Gruppe „Kurs < SMA" zugerechnet. Betrifft in kleinem Umfang auch die
  bestehenden `tabelle_h1`/`tabelle_h2`. In den neuen EDA-Zellen behoben
  (`regime_gruppen()` schließt diese Tage explizit aus); die bestehenden
  Hypothesentabellen wurden **nicht** rückwirkend angepasst (nicht
  angefragt, siehe Offene Punkte).
- **NumPy-2.x-Inkompatibilität gefunden:** Verschachteltes `np.where(...)`
  mit gemischten String-/NaN-Typen wird von NumPy 2.x nicht mehr
  automatisch auf `object`-Dtype hochgestuft (`DTypePromotionError`) — auf
  pandas Boolean-Indexing umgestellt.
- **Regime-Laufzeiten (Median über die Analyseperiode):** SMA20 ≈ 4
  Handelstage (551 Phasen seit 2007 – viele kurze Wechsel), SMA100 ≈ 3 Tage
  (223 Phasen, aber einzelne Phasen bis 313 Tage), SMA200 ≈ 4 Tage (115
  Phasen, einzelne Phasen bis 477 Tage). SMA20 erzeugt also die meisten
  Regimewechsel, SMA200 die stabilsten Langphasen.
- **Farbwahl für die neuen Regime-Charts bewusst nicht Grün/Rot:** Die im
  Notebook bereits vorhandenen `COLOR_GOOD`/`COLOR_BAD` (Grün/Rot) bestehen
  den Farbfehlsichtigkeits-Check für Deuteranopie nicht (ΔE 4,1, deutlich
  unter dem Zielwert), obwohl im Notebook-Text als „farbenblind-sicher
  geprüft" beschrieben. Für die zwei Regime-Zustände stattdessen Blau/Orange
  (`COLOR_SMA_1`/`COLOR_SMA_2`) verwendet, die den Check bestehen (ΔE 9,2).

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
- Nach dem Team-Review der neuen Abschnitte 13/14: die dort sichtbar
  werdende Parameterwahl (welche SMA-Fenster/Signale robust genug für die
  Ampel sind) explizit in `ToDos.docx`/`Zielbild.docx` oder einem eigenen
  Ampel-Konzeptdokument festhalten, nicht nur implizit im Notebook stehen
  lassen.
- Den in dieser Session gefundenen Regime-Zuordnungsfehler (siehe
  Erkenntnisse) bei Gelegenheit auch in den bestehenden Zellen von
  Abschnitt 7/8 (`tabelle_h1`/`tabelle_h2`) beheben, nicht nur in den neuen
  EDA-Zellen — Auswirkung auf die bisherigen Ergebnisse ist vermutlich klein
  (wenige Prozent der Stichprobe), aber ungeprüft.

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
- Abschnitt 13/14 (Regime-EDA + Ampel-Eignung) ist bisher nur im
  S&P-500-Notebook umgesetzt — wartet auf Team-Review, bevor es auf die
  anderen 6 Indizes übertragen wird.
- `S&P_500_hypothesentests.xlsx` enthält vom Team ergänzte Anmerkungen/
  Screenshots. Bei künftigen Notebook-Läufen die Export-Zelle (`hypexp02`)
  weiterhin bewusst aussparen bzw. vorher Rücksprache halten, bis das Team
  einen neuen Stand freigibt und ein Überschreiben ausdrücklich erlaubt.

---

## Session 2 — 2026-08-05

### Ausgangslage
- Anknüpfend an Session 1: Team hat Rückfragen zu den in Abschnitt 13 des
  `01_SP500_Blaupause.ipynb` neu ergänzten EDA-Grafiken (Regime-Analyse
  Preis vs. SMA), die als Entscheidungsgrundlage für die Ampel-
  Parameterwahl dienen sollen.

### Arbeitsschritte
1. Auf Nutzeranfrage: Abschnitt 13b (Regime-Laufzeiten-Histogramm,
   "Wie lange halten Regime-Phasen typischerweise an?") erklärt — Aufbau
   der Grafik, Bedeutung von "Laufzeit" (zusammenhängende Handelstage im
   selben Kurs-vs-SMA-Zustand), Bucket-Verteilung gegen die echten Daten
   nachgerechnet (nicht nur aus den Notebook-Outputs übernommen).
2. Auf Nutzeranfrage: Abschnitt 13d (Verteilung Rendite & Max Drawdown je
   Regime, Histogramme mit Mittelwert/Median) erklärt, inkl. Nachrechnung
   der Zusammenfassungstabelle sowie ergänzend der 5-%-Tail-Perzentile
   (nicht im Notebook enthalten, zur Einordnung des Tail-Risikos ergänzt).
3. Auf Nutzerrückfrage ("wieso konkret -22,6 vs -10,2?"): Herleitung der
   Perzentil-Zahlen Schritt für Schritt erklärt — Stichprobengrößen
   (n=3.579 Tage "Kurs>SMA200" / n=1.119 Tage "Kurs<SMA200"), Perzentil-
   Konzept, und historische Verortung der schlimmsten Einzeltage auf die
   Lehman-Woche (15.–19.09.2008) zur Plausibilisierung der Kennzahl.
4. Auf Nutzeranfrage: Abschnitt 13e (Streuung je Regime über alle
   Prognosehorizonte, Boxplots) erklärt, inkl. Nachrechnung einer
   Standardabweichungs-/IQR-Tabelle über alle Kombinationen aus SMA-Fenster
   (20/100/200) × Horizont (30/60/90 Tage) × Regime × Kennzahl
   (Rendite/MDD).
5. Alle Erklärungen wurden bewusst mit echten, gegen die aktuellen
   Datendateien (`data/S&P_500_clean_with_sma.csv`) nachgerechneten Zahlen
   unterlegt statt nur aus dem Notebook-Text paraphrasiert — Notebook selbst
   wurde in dieser Session nicht verändert, nur zur Erklärung herangezogen.

### Erkenntnisse (aus echten Daten)

- **13b – Regime-Laufzeiten sind stark rechtsschief; Median täuscht.** SMA20:
  551 Phasen seit 2007, Median 4 Handelstage, aber nur 14 % aller
  Handelstage liegen tatsächlich in kurzen (≤5 Tage) Phasen, obwohl diese
  58 % der Phasen*anzahl* ausmachen. Bei SMA200 ist der Effekt noch
  stärker: nur 2 % der Handelstage in kurzen Phasen trotz 52 % Phasenanteil.
  Phasenzahl und Zeitanteil zeichnen also ein sehr unterschiedliches Bild —
  wichtig für die Lesart des Histogramms.
- **13b – Aufwärtsphasen halten strukturell länger an als Abwärtsphasen,**
  besonders bei den längeren SMA-Fenstern: bei SMA100 gibt es 11
  "Kurs>SMA"-Phasen mit >100 Tagen gegenüber nur 1 "Kurs<SMA"-Phase in
  diesem Bucket; bei SMA200 13 vs. 2. Passt zum bekannten Marktmuster
  "Treppe hoch, Fahrstuhl runter".
- **13d – Drawdown-Effekt ist über alle drei SMA-Fenster konsistent**
  (Kurs<SMA immer mit schlechterem mittlerem Forward-MDD als Kurs>SMA),
  **der Rendite-Effekt dagegen nicht:** bei SMA20/SMA100 ist die mittlere
  30-Tage-Forward-Rendite im Zustand "Kurs<SMA" sogar höher als im Zustand
  "Kurs>SMA" (Mean-Reversion-Muster, aber mit deutlich höherem Risiko
  erkauft). Erst bei SMA200 ziehen Rendite- und Risikosignal in dieselbe,
  intuitive Richtung (Kurs>SMA200 = höhere erwartete Rendite UND
  geringeres Risiko).
- **13d – Tail-Risk-Kennzahlen zeigen eine deutlich größere Kluft als der
  Mittelwert:** 5-%-Perzentil des 30-Tage-Forward-MDD bei SMA200:
  −10,2 % (Kurs>SMA) vs. −22,6 % (Kurs<SMA) — mehr als doppelt so tief,
  während der Mittelwertunterschied nur −4,2 % vs. −8,2 % beträgt. Die
  schlimmsten Einzeltage in der "Kurs<SMA200"-Gruppe konzentrieren sich
  real auf die Lehman-Woche September 2008 (MDD bis −32 %) — kein
  statistisches Artefakt, sondern eine reale, bekannte Krisenperiode.
- **13e – Streuung ist das robusteste der drei EDA-Muster: ausnahmslos in
  allen 18 geprüften Kombinationen** (3 SMA-Fenster × 3 Horizonte ×
  2 Kennzahlen) ist die Streuung (Standardabweichung/IQR) im Zustand
  "Kurs<SMA" größer als im Zustand "Kurs>SMA" — keine einzige Ausnahme,
  anders als beim Rendite-Mittelwert. Die Lücke wächst sowohl mit dem
  Prognosehorizont als auch mit der SMA-Fensterlänge: bei SMA20/90 Tage
  ca. 1,4× (11,3 % vs. 8,1 %), bei SMA200/90 Tage bereits >2× (14,7 % vs.
  6,9 %) — deckungsgleich mit dem bereits in Session 1 unter `std_a`/
  `std_b` notierten Befund zu H1, hier aber erstmals über alle drei
  Horizonte gemeinsam sichtbar gemacht.

### Empfehlungen

- **Priorität hoch:** Für die Ampel-Logik im "Kurs<SMA"-Zustand eher eine
  Bandbreite/Perzentil-basierte Risikoangabe verwenden statt einer reinen
  Punktschätzung (Mittelwert) — dieser Zustand ist strukturell sowohl
  stärker tail-risk-behaftet (13d) als auch stärker gestreut/weniger
  vorhersagbar (13e); ein einzelner Erwartungswert suggeriert dort eine
  Präzision, die die Daten nicht hergeben.
- **Bestätigt (aus Session 1, jetzt mit zusätzlicher Evidenz):** SMA200
  bleibt der robusteste Kandidat für den primären, stabilen Ampel-Zustand —
  wenige, lange Regime-Phasen (13b), und als einziges Fenster ziehen dort
  Rendite- und Risikosignal in dieselbe Richtung (13d).
- **Bestätigt:** Rendite- und Risiko-Achse in der Ampel-Logik weiterhin
  getrennt behandeln, nicht in einer Kennzahl vermischen — die
  Rendite-Ergebnisse widersprechen sich zwischen den SMA-Fenstern (13d),
  während Risiko/Streuung durchgängig konsistent sind (13d/13e).

### Offene Punkte / Backlog

- Die in dieser Session hergeleiteten Zusatzkennzahlen (5-%-Tail-Perzentile,
  Streuungstabelle über alle Horizonte) existieren bisher nur im
  Chat-Verlauf bzw. in dieser Zusammenfassung, nicht im Notebook selbst —
  bei Bedarf als zusätzliche Ausgabe/Tabelle in Abschnitt 13d/13e ergänzen.
- Übrige Backlog-Punkte aus Session 1 unverändert offen (siehe oben),
  insbesondere: Übertragung von Abschnitt 13/14 auf die anderen 6 Indizes
  wartet weiterhin auf Team-Review.

---

## Session 2 (Fortsetzung) — 2026-08-05: H2–H4-EDA im Notebook

### Ausgangslage
- Team-Rückfrage: Abschnitt 13/14 (Regime-EDA für die Ampel-Parameterwahl)
  war bisher ausschließlich für Hypothese 1 (Kurs vs. SMA) umgesetzt.
  Auftrag: dieselbe Analysetiefe für H2 (SMA-Richtung), H3 (Cross-Over) und
  H4 (Divergenz) ergänzen, inkl. je einer ausführlichen, in einfacher
  Sprache gehaltenen Fazit-Zelle zur Praxisrelevanz. Vorgehen wurde vor
  Umsetzung per Plan mit dem Team abgestimmt (u. a. Entscheidung: H1
  bekommt zur Konsistenz ebenfalls eine Fazit-Zelle; datenarme Fälle bei
  H3/H4 werden deskriptiv statt mit irreführenden Verteilungscharts
  behandelt).

### Arbeitsschritte
1. `01_SP500_Blaupause.ipynb` um 22 neue Zellen erweitert: eine
   konsolidierte Fazit-Zelle am Ende von Abschnitt 13 (H1), sowie drei neue
   Abschnitte — **15 (H2, SMA-Richtung)**, **16 (H3, Cross-Over)**,
   **17 (H4, Divergenz)** — jeweils mit EDA-Grafiken analog zu Abschnitt 13
   und einer abschließenden Fazit-Zelle in einfacher Sprache.
2. H1/H2 (Zustands-/Regime-basiert) erhielten dieselbe fünfteilige Struktur
   wie Abschnitt 13 (Verteilung, Laufzeiten, Kursverlauf mit
   Regime-Hintergrund, Rendite-/Drawdown-Verteilung, Streuung). H3/H4
   (seltene Einzelereignisse statt andauernder Zustände) wurden inhaltlich
   angepasst: Ereignishäufigkeit/-abstand statt Regime-Laufzeit; bei H3
   Vergleich Golden- vs. Death-Cross (wie im bestehenden Hypothesentest in
   Abschnitt 9), bei H4 Vergleich Ereignis vs. Basisrate (wie im
   bestehenden Test in Abschnitt 10).
3. Datenarme Fälle bewusst ohne Verteilungs-/Streuungscharts behandelt: bei
   H3 nur 2 von 9 SMA-Paaren (SMA20/100 und SMA20/200, beide Tagesbasis)
   mit ausreichender Ereigniszahl (≥10 je Gruppe) für Verteilungscharts;
   bei H4 wurde für Muster D2 (nur 2 Ereignisse) komplett auf
   Verteilungsdarstellung verzichtet, nur Ereignistabelle mit den zwei
   Einzelwerten. Bei H3/H4-Verteilungscharts mit kleiner Stichprobe (n=25/
   11/12) wurden zusätzlich zu Boxplot/Histogramm die Einzelpunkte
   eingezeichnet, um keine irreführend glatte Verteilung zu suggerieren.
4. Alle neuen Zellen einzeln gegen die echten Daten ausgeführt, danach das
   gesamte Notebook von oben durchlaufen lassen (`nbclient`, Kernel
   `sp500-venv`), um Zellreihenfolge/Abhängigkeiten zu verifizieren — dabei
   wurde die Export-Zelle `hypexp02` (schreibt
   `S&P_500_hypothesentests.xlsx`, enthält vom Team ergänzte Anmerkungen)
   gezielt per Cell-ID von der Ausführung ausgenommen; Datei-Zeitstempel
   nach dem Lauf bestätigt, dass sie unverändert blieb.
5. Bug beim ersten Ausführungsversuch gefunden und behoben: zwei neue
   Code-Zellen (H2-Hilfsfunktionen) enthielten fälschlich escapte
   Docstring-Anführungszeichen (`\'\'\'` statt `"""`), die beim Einfügen
   über ein Python-Rawstring-Skript entstanden sind — Syntaxfehler beim
   Ausführen, vor dem zweiten Lauf per Syntax-Check aller neuen Zellen
   (`compile()`) verifiziert und korrigiert.

### Erkenntnisse (aus echten Daten)

- **H2-Regimeverteilung/-laufzeiten (15a/15b):** Deutlich unausgewogener
  als H1 (65/35 bei SMA20 bis 78/22 bei SMA200 – "steigend" überwiegt
  strukturell). Neuer Befund: die SMA-Richtung ist eine **noch trägere
  Zustandsgröße als die Kursposition** — bei SMA200 dauert die längste
  Phase 870 Handelstage (fast 3,5 Jahre) gegenüber 477 Tagen bei H1. Für
  eine stabile Ampel-Basis ist H2/SMA200 damit sogar noch geeigneter als
  H1/SMA200.
- **H2-Rendite/Drawdown (15d) und Streuung (15e):** Bestätigen das H1-Muster
  fast deckungsgleich (Drawdown durchgehend robuster als Rendite-Effekt;
  Streuung im Zustand "fallend" ausnahmslos größer). Bei SMA200 sind H1- und
  H2-Kennzahlen nahezu identisch (z. B. Streuung Forward Return 90d: H1
  6,9 %/14,7 %, H2 7,1 %/14,7 %) — beide Hypothesen überlappen bei diesem
  Fenster stark und liefern wenig zusätzliche, unabhängige Information.
  Eigenständigen Mehrwert bietet H2 eher bei SMA20.
- **H3-Ereignishäufigkeit (16a):** Nur 2 von 9 SMA-Paaren erreichen
  überhaupt die Mindeststichprobe (SMA20/100: 25/25, SMA20/200: 11/11);
  selbst das "klassische" SMA100/200 bleibt mit 8/8 knapp darunter. Alle
  Wochen-/Monatsbasis-Paare liegen bei 0–5 Ereignissen über 19 Jahre.
- **H3-Ereignisabstände (16b):** Auch die zwei testbaren Paare feuern
  extrem unregelmäßig — Median 77 bzw. 156 Tage zwischen Ereignissen, aber
  Spannen bis 663 bzw. 1.320 Kalendertage (bis 3,6 Jahre ohne jedes
  Signal). Cross-Over ist damit strukturell ungeeignet als primäres,
  regelmäßiges Ampel-Signal.
- **H3-Rendite/Drawdown (16d) – kontraintuitiver Befund:** Nach einem
  Death Cross ist die mittlere Forward-Rendite historisch nicht niedriger,
  teils sogar höher als nach einem Golden Cross (SMA20/100, 30d: Death
  2,04 % vs. Golden 0,63 %) — Death Crosses treten oft nahe eines
  Zwischentiefs auf. Der Drawdown ist dagegen konsistent in erwarteter
  Richtung schlechter nach Death Cross. Erneut: Cross-Over eher Risiko- als
  Renditesignal.
- **H4-D1 (17a/17c, n=12):** Einziger Baustein der gesamten H1–H4-EDA, bei
  dem Rendite- UND Risikosignal gleichzeitig günstig ausfallen (30d: Ø
  Rendite 2,6 % vs. 1,2 % Basisrate; Ø Drawdown −2,9 % vs. −5,1 %
  Basisrate). 11 von 12 Einzelereignissen moderat bis deutlich positiv, nur
  ein Ausreißer (27.04.2012). Trotzdem bei n=12 rein deskriptiv zu werten,
  nicht als robuster Beweis (bestehender Test bestätigt nur den
  Drawdown-Effekt, nicht den Renditeeffekt).
- **H4-D2 (17a, n=2):** 01.04.2016 und 01.03.2019, uneinheitliches Ergebnis
  (30d-Rendite −1,3 % bzw. +3,7 %) — für jede Aussage zu klein, sollte
  nicht in die Ampel-Logik einfließen.

### Empfehlungen

- **Bestätigt/verstärkt:** Das durchgängige Muster "SMA-Signale sagen mehr
  über Risiko als über Rendite aus" gilt nicht nur für H1, sondern zeigt
  sich unabhängig auch bei H2 und H3 — erhöht die Verlässlichkeit dieser
  Kernaussage für das Ampel-Konzept.
- **Priorität mittel:** Cross-Over (H3) wegen geringer und höchst
  unregelmäßiger Ereignisfrequenz nicht als primäres Ampel-Signal
  verwenden, allenfalls als seltenen Zusatzbaustein neben einem
  regime-basierten Hauptsignal (H1/H2).
- **Priorität niedrig, aber beobachtenswert:** H4-Muster D1 zeigt ein
  auffällig konsistentes Bild (11/12 positiv), ist bei n=12 aber nicht
  seriös von Zufall zu unterscheiden — im Auge behalten, nicht als
  eigenständiges Ampel-Signal einsetzen. D2 aus der Ampel-Logik ausschließen
  (n=2).
- Da H1 und H2 bei SMA200 stark überlappende Signale liefern, bei der
  finalen Ampel-Parameterwahl prüfen, ob beide gleichzeitig einen echten
  Mehrwert bieten oder ob eines der beiden (z. B. H2/SMA200 wegen der noch
  stabileren Laufzeiten) als primäres Signal genügt.

### Offene Punkte / Backlog

- Abschnitt 15/16/17 (H2–H4-EDA) ist wie Abschnitt 13/14 bisher nur im
  S&P-500-Notebook umgesetzt — Übertragung auf die anderen 6 Indizes bleibt
  wie bisher offen, wartet auf Team-Review.
- Übrige Backlog-Punkte aus Session 1/2 unverändert offen (siehe oben).
