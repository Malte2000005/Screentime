import os
import logging
from typing import List, Dict, Any
import pandas as pd
from flask import Flask, render_template, request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

PEOPLE = {
    "Malte": {"label": "Malte", "folder": "data/Malte"},
    "Julian": {"label": "Julian", "folder": "data/Julian"},
}

SOCIAL_APPS = {"Instagram", "Snapchat", "WhatsApp", "YouTube", "Spotify", "Toralarm"}
PRODUCTIVITY_APPS = {"GoodNotes", "ChatGPT", "Safari", "Duolingo", "Strava"}


def classify_app(app_name: str) -> str:
    """Ordnet Apps einer Kategorie zu."""
    if app_name in SOCIAL_APPS:
        return "social"
    if app_name in PRODUCTIVITY_APPS:
        return "productivity"
    return "other"


def parse_any_csv(file_path: str) -> List[Dict[str, Any]]:
    """
    Liest verschiedene CSV-Formate ein:
    1. App, Minuten
    2. App, Datum, Sekunden
    3. Apple-Format mit 'Sek.'
    """
    records = []
    file_name = os.path.basename(file_path)
    date_from_name = (
        file_name.replace("screen_time_", "")
        .replace("screentime_", "")
        .replace(".csv", "")
    )

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip().replace("\u200e", "")
                if not line:
                    continue

                if line.lower().startswith(("app", "name")):
                    continue

                parts = [part.strip() for part in line.split(",")]

                if len(parts) == 2:
                    try:
                        records.append({
                            "App": parts[0],
                            "Datum": date_from_name,
                            "Minuten": float(parts[1].replace(",", "."))
                        })
                        continue
                    except ValueError:
                        pass

                if "Sek." in line:
                    try:
                        seconds = parts[-1].replace("Sek.", "").replace(".", "").strip()
                        records.append({
                            "App": parts[0],
                            "Datum": date_from_name,
                            "Minuten": float(seconds) / 60
                        })
                        continue
                    except ValueError:
                        pass

                if len(parts) >= 3:
                    try:
                        records.append({
                            "App": parts[0],
                            "Datum": parts[1],
                            "Minuten": float(parts[2].replace(",", ".")) / 60
                        })
                    except ValueError:
                        pass

    except Exception as error:
        logger.error(f"Fehler bei Datei {file_path}: {error}")

    return records


def get_available_files(person_key: str) -> List[str]:
    """Gibt alle CSV-Dateien einer Person zurück."""
    folder = PEOPLE[person_key]["folder"]

    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
        return []

    return sorted([file for file in os.listdir(folder) if file.endswith(".csv")])


def prepare_daily_series(df: pd.DataFrame) -> pd.DataFrame:
    """Bereitet Tageswerte sortiert für Diagramm und Heatmap auf."""
    if df.empty:
        return pd.DataFrame(columns=["Datum", "Minuten"])

    df_daily = df.groupby("Datum")["Minuten"].sum().reset_index()

    df_daily["Sort"] = pd.to_datetime(
        df_daily["Datum"].astype(str) + ".2026",
        format="%d.%m.%Y",
        errors="coerce"
    )

    df_daily = df_daily.sort_values("Sort", na_position="last")
    df_daily = df_daily.drop(columns=["Sort"])

    return df_daily


def get_heatmap_level(ratio: float) -> str:
    """Gibt die passende Heatmap-Farbklasse zurück."""
    if ratio <= 0.20:
        return "heatmap-green"
    if ratio <= 0.40:
        return "heatmap-lime"
    if ratio <= 0.60:
        return "heatmap-yellow"
    if ratio <= 0.80:
        return "heatmap-orange"
    return "heatmap-red"


def build_heatmap(df_daily: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Erstellt eine Heatmap:
    niedrigster Wert = knallgrün
    höchster Wert = knallrot
    """
    if df_daily.empty:
        return []

    min_value = df_daily["Minuten"].min()
    max_value = df_daily["Minuten"].max()
    value_range = max_value - min_value

    heatmap = []

    for _, row in df_daily.iterrows():
        minutes = row["Minuten"]

        if value_range == 0:
            ratio = 0
        else:
            ratio = (minutes - min_value) / value_range

        heatmap.append({
            "date": row["Datum"],
            "minutes": int(round(minutes, 0)),
            "level": get_heatmap_level(ratio)
        })

    return heatmap


def build_comparison(total_minutes: int, day_count: int) -> List[Dict[str, str]]:
    """Erstellt Vergleichsgrößen für das Storytelling."""
    average = total_minutes / day_count if day_count > 0 else 0

    return [
        {
            "title": "Gesamtzeit",
            "value": f"{total_minutes / 60:.1f} h",
            "text": "So viel Zeit wurde im ausgewählten Zeitraum insgesamt am Handy verbracht."
        },
        {
            "title": "Arbeitstage",
            "value": f"{total_minutes / 480:.1f}",
            "text": "Das entspricht ungefähr so vielen vollen 8-Stunden-Tagen."
        },
        {
            "title": "Vorlesungen",
            "value": f"{total_minutes / 90:.1f}",
            "text": "Umgerechnet wären das ungefähr so viele 90-Minuten-Vorlesungen."
        },
        {
            "title": "Ø pro Tag",
            "value": f"{average:.0f} Min",
            "text": "Durchschnittliche tägliche Nutzung im betrachteten Zeitraum."
        },
    ]


def build_story(df: pd.DataFrame, df_daily: pd.DataFrame, app_summary: pd.DataFrame) -> List[Dict[str, str]]:
    """Erstellt kurze Insight-Texte."""
    if df.empty or df_daily.empty or app_summary.empty:
        return [{"title": "Keine Daten", "text": "Für die aktuelle Auswahl liegen keine Daten vor."}]

    max_day = df_daily.loc[df_daily["Minuten"].idxmax()]
    avg_day = df_daily["Minuten"].mean()
    top_app = app_summary.iloc[0]

    social_sum = df[df["Kategorie"] == "social"]["Minuten"].sum()
    productivity_sum = df[df["Kategorie"] == "productivity"]["Minuten"].sum()

    if social_sum > productivity_sum:
        category_text = "Social-Media-Apps nehmen im betrachteten Zeitraum mehr Zeit ein."
    elif productivity_sum > social_sum:
        category_text = "Produktivitäts-Apps nehmen im betrachteten Zeitraum mehr Zeit ein."
    else:
        category_text = "Social Media und Produktivitäts-Apps sind ungefähr gleich stark vertreten."

    return [
        {
            "title": "Nutzungs-Peak",
            "text": f"Der stärkste Tag war der {max_day['Datum']} mit {max_day['Minuten']:.0f} Minuten."
        },
        {
            "title": "Tagesdurchschnitt",
            "text": f"Im Durchschnitt liegt die Bildschirmzeit bei rund {avg_day:.0f} Minuten pro Tag."
        },
        {
            "title": "Dominierende App",
            "text": f"Die meistgenutzte App ist {top_app['App']} mit insgesamt {top_app['Minuten']:.0f} Minuten."
        },
        {
            "title": "Kategorie-Vergleich",
            "text": category_text
        },
    ]


@app.route("/")
def index():
    selected_person = request.args.get("person", "Malte")
    selected_file = request.args.get("file", "")
    selected_category = request.args.get("category", "all")

    if selected_person not in PEOPLE:
        selected_person = "Malte"

    folder = PEOPLE[selected_person]["folder"]
    records = []

    files_to_read = [selected_file] if selected_file else get_available_files(selected_person)

    for file_name in files_to_read:
        if file_name:
            records.extend(parse_any_csv(os.path.join(folder, file_name)))

    df = pd.DataFrame(records)

    if not df.empty:
        df["Kategorie"] = df["App"].apply(classify_app)

        if selected_category in ["social", "productivity"]:
            df = df[df["Kategorie"] == selected_category]

    if df.empty:
        total_minutes = 0
        app_count = 0
        top5 = []
        df_daily = pd.DataFrame(columns=["Datum", "Minuten"])
        app_summary = pd.DataFrame(columns=["App", "Minuten"])
    else:
        total_minutes = int(round(df["Minuten"].sum(), 0))

        app_summary = (
            df.groupby("App")["Minuten"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )

        top5 = app_summary.head(5).to_dict("records")
        app_count = len(app_summary)
        df_daily = prepare_daily_series(df)

    return render_template(
        "index.html",
        people=PEOPLE,
        selected_person=selected_person,
        selected_file=selected_file,
        selected_category=selected_category,
        available_files=get_available_files(selected_person),
        total_minutes=total_minutes,
        app_count=app_count,
        top5=top5,
        time_series=df_daily.to_dict("records"),
        heatmap_data=build_heatmap(df_daily),
        comparison_data=build_comparison(total_minutes, len(df_daily)),
        story_texts=build_story(df, df_daily, app_summary)
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)