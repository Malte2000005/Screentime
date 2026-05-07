# Screen-Time Dashboard

Dieses Projekt ist eine Flask-Webapp zur Visualisierung der Bildschirmzeit über den Verlauf der letzten Wochen.

Die Anwendung liest CSV-Dateien ein, verarbeitet die Daten und stellt verschiedene Statistiken sowie Diagramme in einem Dashboard dar.

## Funktionen

- Auswahl zwischen mehreren Personen
- Einlesen unterschiedlicher CSV-Formate
- Anzeige der gesamten Bildschirmzeit
- Top-5-Apps Übersicht
- Tagesbezogene Statistik
- Heatmap der Nutzung
- Kategoriefilter für Social Media und Produktivität
- Automatisch generierte Insight-Texte
- Logging und grundlegendes Error Handling

## Verwendete Technologien

- Python
- Flask
- Pandas
- HTML / CSS
- Chart.js
- Git / GitHub

## Projektstruktur

```text
project/
│
├── app.py
├── templates/
│   └── index.html
├── static/
│   └── style.css
├── data/
│   ├── Julian/
│   └── Malte/
├── README.md
└── .gitignore

## Aufgabenverteilung
Julian: CSV Dateien einlesen lassen und formatieren, Heatmap, Error handling, GUI Interface
Malte: CSV Dateien einlesen lassen und formatieren, Storytelling, logger konfiguration, GUI Interface