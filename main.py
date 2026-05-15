from flask import Flask, render_template, request, redirect, url_for
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
    "Moscow", "London", "Paris", "Berlin",
    "Tokyo", "New York", "Toronto",
    "Sydney", "Oslo", "Helsinki",
    "Yakutsk", "Norilsk", "Reykjavik"
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

    response = requests.get(
        url,
        timeout=5
    )

    data = response.json()

    return (
        data["daily"]["time"],
        data["daily"]["temperature_2m_mean"]
    )


def parse_query(query):

    query = query.strip().lower()

    if "жарк" in query:
        return "hot"

    elif "холод" in query:
        return "cold"

    elif "снеж" in query:
        return "snow"

    elif "дожд" in query:
        return "rain"

    return None


def get_top_cities(filter_type):

    results = []

    for city in CITIES:

        try:

            url = (
                f"https://api.openweathermap.org/data/2.5/weather?"
                f"q={city}"
                f"&appid={API_KEY}"
                f"&units=metric"
                f"&lang=ru"
            )

            response = requests.get(
                url,
                timeout=3
            )

            data = response.json()

            # Если API вернул ошибку
            if data.get("cod") != 200:
                continue

            temp = data["main"]["temp"]

            desc = data["weather"][0]["description"]

            wid = data["weather"][0]["id"]

            results.append({

                "city": data["name"],

                "temp": round(temp),

                "description": desc,

                "weather_id": wid
            })

        except:

            continue

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

        results = [

            r for r in results

            if 600 <= r["weather_id"] < 700
        ]

    elif filter_type == "rain":

        results = [

            r for r in results

            if 500 <= r["weather_id"] < 600
        ]

    return results[:7]


@app.route("/")
def index():

    return render_template(
        "index.html"
    )


@app.route(
    "/weather",
    methods=["GET", "POST"]
)
def weather():

    if request.method == "POST":

        city = request.form.get(
            "city",
            ""
        ).strip()

    else:

        return redirect(
            url_for("index")
        )

    weather = None

    try:

        current_url = (
            f"https://api.openweathermap.org/data/2.5/weather?"
            f"q={city}"
            f"&appid={API_KEY}"
            f"&units=metric"
            f"&lang=ru"
        )

        response = requests.get(
            current_url,
            timeout=5
        )

        current_data = response.json()

        if current_data.get("cod") == 200:

            descriptions = [

                w["description"]

                for w in current_data["weather"]
            ]

            weather = {

                "city": current_data["name"],

                "temp": round(
                    current_data["main"]["temp"]
                ),

                "feels_like": round(
                    current_data["main"]["feels_like"]
                ),

                "description": ", ".join(descriptions),

                "icon": current_data["weather"][0]["icon"]
            }

        else:

            weather = {
                "error": "Город не найден"
            }

    except:

        weather = {
            "error": "Ошибка подключения к API"
        }

    return render_template(
        "weather.html",
        weather=weather
    )


@app.route("/graphs/<city>")
def graphs(city):

    forecast_graph = None

    history_graph = None

    try:

        current_url = (
            f"https://api.openweathermap.org/data/2.5/weather?"
            f"q={city}"
            f"&appid={API_KEY}"
            f"&units=metric"
            f"&lang=ru"
        )

        response = requests.get(
            current_url,
            timeout=5
        )

        current_data = response.json()

        if current_data.get("cod") == 200:

            lat = current_data["coord"]["lat"]

            lon = current_data["coord"]["lon"]

            os.makedirs(
                "static",
                exist_ok=True
            )

            forecast_url = (
                f"https://api.openweathermap.org/data/2.5/forecast?"
                f"q={city}"
                f"&appid={API_KEY}"
                f"&units=metric"
                f"&lang=ru"
            )

            forecast_response = requests.get(
                forecast_url,
                timeout=5
            )

            forecast_data = forecast_response.json()

            if forecast_data.get("cod") == "200":

                temps = []

                dates = []

                for i in range(
                    0,
                    len(forecast_data["list"]),
                    8
                ):

                    item = forecast_data["list"][i]

                    temps.append(
                        round(
                            item["main"]["temp"]
                        )
                    )

                    dates.append(
                        item["dt_txt"].split(" ")[0]
                    )

                plt.figure(
                    figsize=(20, 10)
                )

                plt.plot(
                    dates,
                    temps,
                    marker='o'
                )

                plt.title(
                    f"Прогноз на 5 дней: {city}",
                    fontsize=24
                )

                plt.xlabel(
                    "Дата",
                    fontsize=18
                )

                plt.ylabel(
                    "Температура °C",
                    fontsize=18
                )

                plt.grid()

                forecast_path = "static/forecast.png"

                plt.savefig(
                    forecast_path
                )

                plt.close()

                forecast_graph = "/" + forecast_path

            dates_hist, temps_hist = get_history(
                lat,
                lon
            )

            monthly_data = collections.defaultdict(list)

            for d, t in zip(
                dates_hist,
                temps_hist
            ):

                monthly_data[d[:7]].append(t)

            months = sorted(
                monthly_data.keys()
            )

            avg_temps = [

                round(
                    sum(monthly_data[m]) /
                    len(monthly_data[m])
                )

                for m in months
            ]

            plt.figure(
                figsize=(20, 10)
            )

            plt.bar(
                months,
                avg_temps,
                color="orange"
            )

            plt.title(
                f"Средняя температура за 2 года: {city}",
                fontsize=24
            )

            plt.xlabel(
                "Месяц",
                fontsize=18
            )

            plt.ylabel(
                "Температура °C",
                fontsize=18
            )

            plt.xticks(
                rotation=45,
                fontsize=12
            )

            plt.grid(axis='y')

            history_path = "static/history.png"

            plt.savefig(
                history_path
            )

            plt.close()

            history_graph = "/" + history_path

    except:

        pass

    return render_template(
        "graphs.html",
        city=city,
        forecast_graph=forecast_graph,
        history_graph=history_graph
    )


@app.route(
    "/filters",
    methods=["GET", "POST"]
)
def filters():

    if request.method == "POST":

        filter_query = request.form.get(
            "filter",
            ""
        )

    else:

        return redirect(
            url_for("index")
        )

    filter_type = parse_query(
        filter_query
    )

    top_cities = []

    if filter_type:

        top_cities = get_top_cities(
            filter_type
        )

    return render_template(
        "filters.html",
        top_cities=top_cities,
        filter_query=filter_query
    )


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=True
    )