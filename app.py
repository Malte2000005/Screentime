import os
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
from flask import Flask, render_template, request

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

PEOPLE: Dict[str, Dict[str, str]] = {
    "Malte": {"label": "Malte", "folder": "data/Malte"},
    "Julian": {"label": "Julian", "folder": "data/Julian"}
}

def parse_any_csv(file_path: str) -> List[Dict[str, Any]]:
    """
    Erkennt automatisch, ob es Maltes Format oder Julians Apple-Export ist.
    Anforderung: Error Handling & Modularisierung.
    """
    records = []
    file_name = os.path.basename(file_path)
    # Fallback Datum aus Dateiname, falls es nicht in der Zeile steht (Apple Export)
    date_from_name = file_name.replace("screen_time_", "").replace(".csv", "")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip().replace('\u200e', '') # Apple-Spezialzeichen weg
                if not line or line.lower().startswith("app") or line.lower().startswith("name"):
                    continue

                parts = line.split(",")
                if len(parts) < 3: continue

                # LOGIK 1: Apple Export (Julian) - Ende ist "954 Sek."
                if "Sek." in line:
                    app_name = parts[0].strip()
                    if app_name.lower() in ["screentimeunlock", ""]: continue
                    try:
                        raw_sec = parts[-1].replace("Sek.", "").strip().replace(".", "")
                        records.append({
                            "App": app_name,
                            "Datum": date_from_name,
                            "Minuten": float(raw_sec) / 60
                        })
                    except ValueError: continue

                # LOGIK 2: Maltes Format - App, Datum, Sekunden
                else:
                    try:
                        app_name = parts[0].strip()
                        datum = parts[1].strip()
                        sekunden = float(parts[2].strip())
                        records.append({
                            "App": app_name,
                            "Datum": datum,
                            "Minuten": sekunden / 60
                        })
                    except (ValueError, IndexError): continue
    except Exception as e:
        logger.error(f"Fehler bei Datei {file_path}: {e}")
    return records

def get_available_files(person_key: str) -> List[str]:
    folder = PEOPLE[person_key]["folder"]
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
        return []
    return sorted([f for f in os.listdir(folder) if f.endswith(".csv")])

@app.route("/")
def index():
    selected_person = request.args.get("person", "Malte")
    selected_file = request.args.get("file", "")

    if selected_person not in PEOPLE:
        selected_person = "Malte"

    folder = PEOPLE[selected_person]["folder"]
    all_records = []

    # Dateien laden
    files_to_read = [selected_file] if selected_file else get_available_files(selected_person)
    for f in files_to_read:
        if f:
            all_records.extend(parse_any_csv(os.path.join(folder, f)))

    df = pd.DataFrame(all_records)

    if not df.empty:
        total_min = round(df["Minuten"].sum(), 2)
        app_summary = df.groupby("App")["Minuten"].sum().sort_values(ascending=False).reset_index()
        top5 = app_summary.head(5).to_dict(orient="records")
        # Wichtig für den Graph: Nach Datum summieren und sortieren
        df_daily = df.groupby("Datum")["Minuten"].sum().reset_index().sort_values("Datum")
        time_series = df_daily.to_dict(orient="records")
        app_count = len(app_summary)
    else:
        total_min, top5, time_series, app_count = 0, [], [], 0

    return render_template(
        "index.html",
        people=PEOPLE,
        selected_person=selected_person,
        available_files=get_available_files(selected_person),
        selected_file=selected_file,
        total_minutes=total_min,
        top5=top5,
        time_series=time_series,
        app_count=app_count
    )

if __name__ == "__main__":
    app.run(debug=True, port=5000)ard_data)
