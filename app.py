import os
import logging
from typing import List, Dict, Any
import pandas as pd
from flask import Flask, render_template, request

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

PEOPLE: Dict[str, Dict[str, str]] = {
    "Malte": {"label": "Malte", "folder": "data/Malte"},
    "Julian": {"label": "Julian", "folder": "data/Julian"},
}


def parse_any_csv(file_path: str) -> List[Dict[str, Any]]:
    """
    Liest verschiedene CSV-Formate ein:
    1) Neues bereinigtes Format: App,Minutes
    2) Maltes Format: App,Datum,Sekunden
    3) Apple-/älteres Format mit 'Sek.'
    """
    records = []
    file_name = os.path.basename(file_path)

    date_from_name = file_name.replace("screen_time_", "").replace(".csv", "")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip().replace("\u200e", "")
                if not line:
                    continue

                lower = line.lower()
                if lower.startswith("app") or lower.startswith("name"):
                    continue

                parts = [p.strip() for p in line.split(",")]

                # FORMAT 1: Neues bereinigtes Format -> App,Minutes
                if len(parts) == 2:
                    try:
                        app_name = parts[0]
                        minuten = float(parts[1].replace(",", "."))
                        records.append(
                            {
                                "App": app_name,
                                "Datum": date_from_name,
                                "Minuten": minuten,
                            }
                        )
                        continue
                    except ValueError:
                        pass

                # FORMAT 2: Apple-/älteres Format mit "Sek."
                if "Sek." in line:
                    try:
                        app_name = parts[0]
                        if app_name.lower() in ["screentimeunlock", ""]:
                            continue

                        raw_sec = parts[-1].replace("Sek.", "").replace(".", "").strip()
                        sekunden = float(raw_sec)

                        records.append(
                            {
                                "App": app_name,
                                "Datum": date_from_name,
                                "Minuten": sekunden / 60,
                            }
                        )
                        continue
                    except ValueError:
                        pass

                # FORMAT 3: Maltes Format -> App, Datum, Sekunden
                if len(parts) >= 3:
                    try:
                        app_name = parts[0]
                        datum = parts[1]
                        sekunden = float(parts[2].replace(",", "."))
                        records.append(
                            {"App": app_name, "Datum": datum, "Minuten": sekunden / 60}
                        )
                    except (ValueError, IndexError):
                        continue

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
    files_to_read = (
        [selected_file] if selected_file else get_available_files(selected_person)
    )
    for f in files_to_read:
        if f:
            all_records.extend(parse_any_csv(os.path.join(folder, f)))

    df = pd.DataFrame(all_records)

    if not df.empty:
        total_min = round(df["Minuten"].sum(), 2)
        app_summary = (
            df.groupby("App")["Minuten"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        top5 = app_summary.head(5).to_dict(orient="records")
        # Wichtig für den Graph: Nach Datum summieren und sortieren
        df_daily = df.groupby("Datum")["Minuten"].sum().reset_index()

        df_daily["SortDate"] = pd.to_datetime(
            df_daily["Datum"], format="%d.%m", errors="coerce"
        )
        df_daily = df_daily.sort_values("SortDate").drop(columns=["SortDate"])

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
        app_count=app_count,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
print("Branch 1")