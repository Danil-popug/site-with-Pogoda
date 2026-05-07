from flask import Flask, render_template, request
from dotenv import load_dotenv
import os
import requests
import matplotlib

matplotlib.use('Agg')

import matplotlib.pyplot as plt
import datetime
import collections

load_dotenv()

API_KEY = os.getenv("API_KEY")

app = Flask(__name__)

CITIES = [
    # Европа
    "Moscow", "London", "Paris", "Berlin", "Madrid",
    "Rome", "Oslo", "Helsinki", "Stockholm", "Reykjavik",
    "Warsaw", "Prague", "Vienna", "Budapest",

    # Азия
    "Tokyo", "Beijing", "Seoul", "Bangkok", "Delhi",
    "Yakutsk", "Novosibirsk", "Norilsk",

    # Америка
    "New York", "Toronto", "Chicago", "Vancouver",
    "Anchorage", "Montreal",

    # Южная Америка
    "Buenos Aires", "Santiago",

    # Африка
    "Cape Town", "Cairo",

    # Австралия
    "Sydney", "Melbourne"
]


def get_history(lat, lon):

    end = datetime.date.today()
    start = end - datetime.timedelta(days=730)

    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}&longitude={lon}"
        f"&start_date={start}"
        f"&end_date={end}"
        f"&daily=temperature_2m_mean"
        f"&timezone=auto"
    )

    data = requests.get(url).json()

    return data["daily"]["time"], data["daily"]["temperature_2m_mean"]


def parse_query(query):

    query = query.strip().lower()

    if query == "самые жаркие города":
        return "hot"

    elif query == "самые холодные города":
        return "cold"

    elif query == "самые снежные города":
        return "snow"

    elif query == "самые дождливые города":
        return "rain"

    return None


def get_top_cities(filter_type):

    results = []

    for city in CITIES:

        url = (
            f"https://api.openweathermap.org/data/2.5/weather?"
            f"q={city}"
            f"&appid={API_KEY}"
            f"&units=metric"
            f"&lang=ru"
        )

        data = requests.get(url).json()

        if data.get("cod") == 200:

            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
            wid = data["weather"][0]["id"]

            results.append({
                "city": data["name"],
                "temp": round(temp),
                "description": desc,
                "weather_id": wid
            })

    if filter_type == "hot":

        results.sort(
            key=lambda x: x["temp"],
            reverse=True
        )

    elif filter_type == "cold":

        results.sort(
            key=lambda x: x["temp"]
        )

    elif filter_type == "snow":

        snow_results = [
            r for r in results
            if 600 <= r["weather_id"] < 700
        ]

        if not snow_results:

            snow_results = [
                r for r in results
                if "обла" in r["description"]
            ]

        results = snow_results

    elif filter_type == "rain":

        rain_results = [
            r for r in results
            if 500 <= r["weather_id"] < 600
        ]

        if not rain_results:

            rain_results = [
                r for r in results
                if "пасмур" in r["description"]
            ]

        results = rain_results

    return results[:7]


@app.route("/", methods=["GET", "POST"])
def index():

    weather = None
    forecast_graph = None
    history_graph = None
    top_cities = None

    if request.method == "POST":

        city = request.form.get("city", "").strip()
        filter_query = request.form.get("filter", "")

        filter_type = parse_query(filter_query)

        if filter_type:
            top_cities = get_top_cities(filter_type)

        if city:

            current_url = (
                f"https://api.openweathermap.org/data/2.5/weather?"
                f"q={city}"
                f"&appid={API_KEY}"
                f"&units=metric"
                f"&lang=ru"
            )

            current_data = requests.get(current_url).json()

            if current_data.get("cod") == 200:

                descriptions = [
                    w["description"]
                    for w in current_data["weather"]
                ]

                weather = {
                    "city": current_data["name"],
                    "temp": round(current_data["main"]["temp"]),
                    "feels_like": round(current_data["main"]["feels_like"]),
                    "description": ", ".join(descriptions),
                    "icon": current_data["weather"][0]["icon"]
                }

                lat = current_data["coord"]["lat"]
                lon = current_data["coord"]["lon"]

                os.makedirs("static", exist_ok=True)

                # Прогноз на 5 дней
                forecast_url = (
                    f"https://api.openweathermap.org/data/2.5/forecast?"
                    f"q={city}"
                    f"&appid={API_KEY}"
                    f"&units=metric"
                    f"&lang=ru"
                )

                forecast_data = requests.get(forecast_url).json()

                if forecast_data.get("cod") == "200":

                    temps = []
                    dates = []

                    for i in range(0, len(forecast_data["list"]), 8):

                        item = forecast_data["list"][i]

                        temps.append(
                            round(item["main"]["temp"])
                        )

                        dates.append(
                            item["dt_txt"].split(" ")[0]
                        )

                    plt.figure(figsize=(20, 10))

                    plt.rcParams.update({
                        'font.size': 14
                    })

                    plt.plot(
                        dates,
                        temps,
                        marker='o'
                    )

                    plt.title(
                        f"Прогноз на 5 дней: {city}"
                    )

                    plt.xlabel("Дата")
                    plt.ylabel("°C")

                    plt.grid()

                    forecast_path = "static/forecast.png"

                    plt.savefig(forecast_path)
                    plt.close()

                    forecast_graph = "/" + forecast_path

                # История за 2 года
                dates_hist, temps_hist = get_history(lat, lon)

                monthly_data = collections.defaultdict(list)

                for d, t in zip(dates_hist, temps_hist):
                    monthly_data[d[:7]].append(t)

                months = sorted(monthly_data.keys())

                avg_temps = [
                    round(
                        sum(monthly_data[m]) /
                        len(monthly_data[m])
                    )
                    for m in months
                ]

                plt.figure(figsize=(20, 10))

                plt.rcParams.update({
                    'font.size': 14
                })

                plt.bar(
                    months,
                    avg_temps,
                    color="orange"
                )

                plt.title(
                    f"Средняя температура по месяцам (2 года): {city}"
                )

                plt.xlabel("Месяц")
                plt.ylabel("°C")

                plt.xticks(rotation=45)

                plt.grid(axis='y')

                history_path = "static/history.png"

                plt.savefig(history_path)
                plt.close()

                history_graph = "/" + history_path

            else:

                weather = {
                    "error": "Город не найден"
                }

    return render_template(
        "index.html",
        weather=weather,
        forecast_graph=forecast_graph,
        history_graph=history_graph,
        top_cities=top_cities
    )


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )