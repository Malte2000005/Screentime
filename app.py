from flask import Flask, render_template, request
import os
import pandas as pd

app = Flask(__name__)

PEOPLE = {
    "Julian": {
        "label": "Julian",
        "folder": "data/Julian"
    },
    "Malte": {
        "label": "Malte",
        "folder": "data/Malte"
    }
}


def read_screen_time_file(file_path):
    """
    Liest eine einzelne CSV-Datei mit Bildschirmzeit-Daten ein.

    Parameter:
        file_path (str): Pfad zur CSV-Datei.

    Rückgabewert:
        list[dict]: Liste mit Datensätzen in der Form
                    {"App": app_name, "Minuten": minutes}.
    """
    records = []

    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    for line in lines:
        parts = line.strip().split(",")

        if len(parts) < 3:
            continue

        app_name = parts[0].strip()
        seconds_text = parts[2].replace("Sek.", "").strip()

        if not app_name:
            continue

        if app_name.lower() in ["screentimeunlock", "app", "name"]:
            continue

        try:
            seconds = int(seconds_text)
        except ValueError:
            continue

        minutes = seconds / 60

        records.append({
            "App": app_name,
            "Minuten": minutes
        })

    return records


def load_data_for_person(folder_path):
    """
    Liest alle CSV-Dateien aus einem Ordner ein und erstellt ein DataFrame.

    Parameter:
        folder_path (str): Ordner mit CSV-Dateien.

    Rückgabewert:
        pandas.DataFrame: DataFrame mit den Spalten "App" und "Minuten".
    """
    all_records = []

    if not os.path.exists(folder_path):
        print(f"Ordner nicht gefunden: {folder_path}")
        return pd.DataFrame(columns=["App", "Minuten"])

    for file_name in os.listdir(folder_path):
        if file_name.endswith(".csv"):
            file_path = os.path.join(folder_path, file_name)
            file_records = read_screen_time_file(file_path)
            all_records.extend(file_records)

    return pd.DataFrame(all_records)


def summarize_app_usage(data_frame):
    """
    Gruppiert die Daten nach App und summiert die Nutzungszeit.
    """
    if data_frame.empty:
        return pd.DataFrame(columns=["App", "Minuten"])

    summary = (
        data_frame.groupby("App")["Minuten"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    return summary


def build_dashboard_data(selected_person):
    """
    Erstellt alle Werte für das Dashboard.

    Parameter:
        selected_person (str): Name der ausgewählten Person.

    Rückgabewert:
        dict: Werte für das HTML-Template.
    """
    if selected_person not in PEOPLE:
        selected_person = "Julian"

    folder_path = PEOPLE[selected_person]["folder"]
    data_frame = load_data_for_person(folder_path)
    app_usage = summarize_app_usage(data_frame)

    if app_usage.empty:
        return {
            "selected_person": selected_person,
            "selected_person_label": PEOPLE[selected_person]["label"],
            "people": PEOPLE,
            "total_minutes": 0,
            "app_count": 0,
            "top_apps": [],
            "top3": [],
            "pie_apps": []
        }

    total_minutes = round(app_usage["Minuten"].sum(), 2)
    app_count = len(app_usage)
    top_apps = app_usage.to_dict(orient="records")
    top3 = app_usage.head(3).to_dict(orient="records")
    pie_apps = app_usage.head(10).to_dict(orient="records")

    return {
        "selected_person": selected_person,
        "selected_person_label": PEOPLE[selected_person]["label"],
        "people": PEOPLE,
        "total_minutes": total_minutes,
        "app_count": app_count,
        "top_apps": top_apps,
        "top3": top3,
        "pie_apps": pie_apps
    }


@app.route("/")
def index():
    """
    Startseite des Dashboards.
    Die Person wird über den URL-Parameter 'person' ausgewählt.
    """
    selected_person = request.args.get("person", "Julian")
    dashboard_data = build_dashboard_data(selected_person)

    return render_template("index.html", **dashboard_data)


if __name__ == "__main__":
    app.run(debug=True)