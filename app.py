from flask import Flask, render_template, request
import requests
import matplotlib.pyplot as plt
import os
import datetime
import collections

app = Flask(__name__)

API_KEY = "cf68db653967dd3060b9205e4f5fa06c"


# 🔹 история за 2 года
def get_history(lat, lon):
    end = datetime.date.today()
    start = end - datetime.timedelta(days=730)

    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start}&end_date={end}&daily=temperature_2m_mean&timezone=auto"
    data = requests.get(url).json()

    return data["daily"]["time"], data["daily"]["temperature_2m_mean"]


@app.route("/", methods=["GET", "POST"])
def index():
    weather = None
    forecast_graph = None
    history_graph = None

    if request.method == "POST":
        city = request.form.get("city", "").strip()

        if not city:
            weather = {"error": "Введите название города"}
        else:
            # 🔹 текущая погода
            current_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric&lang=ru"
            current_data = requests.get(current_url).json()

            if current_data.get("cod") == 200:

                descriptions = [w["description"] for w in current_data["weather"]]

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

                # 🔹 график на 5 дней
                forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric&lang=ru"
                forecast_data = requests.get(forecast_url).json()

                if forecast_data.get("cod") == "200":
                    temps = []
                    dates = []

                    for i in range(0, len(forecast_data["list"]), 8):
                        item = forecast_data["list"][i]
                        temps.append(round(item["main"]["temp"]))
                        dates.append(item["dt_txt"].split(" ")[0])

                    plt.figure(figsize=(20, 10))
                    plt.rcParams.update({'font.size': 14})

                    plt.plot(dates, temps, marker='o')
                    plt.title(f"Прогноз на 5 дней: {city}")
                    plt.xlabel("Дата")
                    plt.ylabel("°C")
                    plt.grid()

                    forecast_path = "static/forecast.png"
                    plt.savefig(forecast_path)
                    plt.close()

                    forecast_graph = "/" + forecast_path

                # 🔹 график за 2 года (по месяцам, столбики)
                dates_hist, temps_hist = get_history(lat, lon)

                monthly_data = collections.defaultdict(list)

                for date, temp in zip(dates_hist, temps_hist):
                    month = date[:7]
                    monthly_data[month].append(temp)

                months = []
                avg_temps = []

                for month in sorted(monthly_data.keys()):
                    months.append(month)
                    avg_temps.append(round(sum(monthly_data[month]) / len(monthly_data[month])))

                plt.figure(figsize=(20, 10))
                plt.rcParams.update({'font.size': 14})

                plt.bar(months, avg_temps, color="orange")

                plt.title(f"Средняя температура по месяцам (2 года): {city}")
                plt.xlabel("Месяц")
                plt.ylabel("°C")
                plt.xticks(rotation=45)
                plt.grid(axis='y')

                history_path = "static/history.png"
                plt.savefig(history_path)
                plt.close()

                history_graph = "/" + history_path

            else:
                weather = {"error": "Город не найден"}

    return render_template(
        "index.html",
        weather=weather,
        forecast_graph=forecast_graph,
        history_graph=history_graph
    )


if __name__ == "__main__":
    app.run(debug=True)