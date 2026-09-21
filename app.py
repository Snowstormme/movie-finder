import os

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request

load_dotenv()

app = Flask(__name__)
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
OMDB_API_KEY = os.getenv("OMDB_API_KEY")
TMDB_API_URL = "https://api.themoviedb.org/3"


def tmdb_get(path, **extra_params):
    response = requests.get(
        f"{TMDB_API_URL}{path}",
        params={"api_key": TMDB_API_KEY, **extra_params},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def sorted_unique_movies(credits):
    """Sort film credits by release date and show each movie only once."""
    movies = []
    seen_ids = set()

    for movie in sorted(credits, key=lambda film: film.get("release_date") or "", reverse=True):
        if movie.get("id") not in seen_ids:
            movies.append(movie)
            seen_ids.add(movie.get("id"))

    return movies


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    query = request.form.get("movie", "").strip()
    if not query:
        return render_template("index.html", error="Enter a movie name to search.")

    try:
        movies = tmdb_get("/search/movie", query=query).get("results", [])[:5]
    except requests.RequestException:
        return render_template(
            "index.html", query=query, error="Could not load movies. Please try again."
        )

    return render_template("index.html", movies=movies, query=query)


@app.route("/movie/<int:movie_id>")
def movie_details(movie_id):
    try:
        movie = tmdb_get(
            f"/movie/{movie_id}", append_to_response="credits,recommendations"
        )
    except requests.RequestException:
        return render_template(
            "index.html", error="Could not load movie details. Please try another film."
        )

    credits = movie.get("credits", {})
    director = next(
        (person for person in credits.get("crew", []) if person.get("job") == "Director"),
        None,
    )
    cast = credits.get("cast", [])[:5]
    recommendations = movie.get("recommendations", {}).get("results", [])[:4]

    # OMDb can add IMDb and Rotten Tomatoes scores when its key is available.
    other_ratings = {}
    if OMDB_API_KEY and movie.get("imdb_id"):
        try:
            response = requests.get(
                "https://www.omdbapi.com/",
                params={"apikey": OMDB_API_KEY, "i": movie["imdb_id"]},
                timeout=6,
            )
            response.raise_for_status()
            omdb_data = response.json()
            if omdb_data.get("Response") == "True":
                other_ratings = {
                    item.get("Source"): item.get("Value")
                    for item in omdb_data.get("Ratings", [])
                    if item.get("Source") and item.get("Value")
                }
        except requests.RequestException:
            pass

    runtime_minutes = movie.get("runtime") or 0
    runtime = (
        f"{runtime_minutes // 60}h {runtime_minutes % 60}m"
        if runtime_minutes >= 60
        else f"{runtime_minutes}m" if runtime_minutes else None
    )

    return render_template(
        "movie.html",
        movie=movie,
        director=director,
        cast=cast,
        recommendations=recommendations,
        runtime=runtime,
        imdb_rating=other_ratings.get("Internet Movie Database"),
        rotten_rating=other_ratings.get("Rotten Tomatoes"),
    )


@app.route("/person/<int:person_id>")
def person_details(person_id):
    try:
        person = tmdb_get(
            f"/person/{person_id}", append_to_response="movie_credits"
        )
    except requests.RequestException:
        return render_template(
            "index.html", error="Could not load this person's films. Please try again."
        )

    credits = person.get("movie_credits", {})
    acting_movies = sorted_unique_movies(credits.get("cast", []))
    directed_movies = sorted_unique_movies(
        film for film in credits.get("crew", []) if film.get("job") == "Director"
    )

    return render_template(
        "person.html",
        person=person,
        acting_movies=acting_movies,
        directed_movies=directed_movies,
    )


@app.route("/movie/<int:movie_id>/cast")
def movie_cast(movie_id):
    try:
        movie = tmdb_get(f"/movie/{movie_id}", append_to_response="credits")
    except requests.RequestException:
        return render_template(
            "index.html", error="Could not load the cast. Please try again."
        )

    cast = movie.get("credits", {}).get("cast", [])
    return render_template("cast.html", movie=movie, cast=cast)


if __name__ == "__main__":
    app.run(debug=True)
