import os

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request

load_dotenv()

app = Flask(__name__)
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_API_URL = "https://api.themoviedb.org/3"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    query = request.form.get("movie", "").strip()
    if not query:
        return render_template("index.html", error="Enter a movie name to search.")

    try:
        response = requests.get(
            f"{TMDB_API_URL}/search/movie",
            params={"api_key": TMDB_API_KEY, "query": query},
            timeout=10,
        )
        response.raise_for_status()
        movies = response.json().get("results", [])[:5]
    except requests.RequestException:
        return render_template(
            "index.html", query=query, error="Could not load movies. Please try again."
        )

    return render_template("index.html", movies=movies, query=query)


@app.route("/movie/<int:movie_id>")
def movie_details(movie_id):
    try:
        response = requests.get(
            f"{TMDB_API_URL}/movie/{movie_id}",
            params={"api_key": TMDB_API_KEY, "append_to_response": "credits"},
            timeout=10,
        )
        response.raise_for_status()
        movie = response.json()
    except requests.RequestException:
        return render_template(
            "index.html", error="Could not load movie details. Please try another film."
        )

    credits = movie.get("credits", {})
    director = next(
        (person["name"] for person in credits.get("crew", []) if person.get("job") == "Director"),
        None,
    )
    cast = credits.get("cast", [])[:5]

    return render_template("movie.html", movie=movie, director=director, cast=cast)


if __name__ == "__main__":
    app.run(debug=True)
