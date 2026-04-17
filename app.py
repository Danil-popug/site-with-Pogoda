from flask import Flask, render_template, request
import requests

app = Flask(__name__)
API_KEY = "cf68db653967dd3060b9205e4f5fa06c"

@app.route("/", methods=["GET", "POST"])
def index():
    weather = None
    if request.method == "POST":
        city = request.form.get("city", "").strip()
        if city:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric&lang=ru"
            data = requests.get(url).json()
            if data.get("cod") == 200:
                weather = {
                    "city": data["name"],
                    "temp": round(data["main"]["temp"]),
                    "feels_like": round(data["main"]["feels_like"]),
                    "description": data["weather"][0]["description"],
                    "icon": data["weather"][0]["icon"]
                }
            else:
                weather = {"error": "Город не найден"}
        else:
            weather = {"error": "Введите название города"}
    return render_template("index.html", weather=weather)

if __name__ == "__main__":
    app.run(debug=True)