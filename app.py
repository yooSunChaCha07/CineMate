from flask import Flask, jsonify, request, render_template,redirect,url_for,flash
import numpy as np
import pandas as pd
# Import your movie recommender script here
from SoftwareProject_MovieRecommender_SVD import get_movie_suggestions, get_similar_movies, movies_list_lowercase, unique_movies
from flask_cors import CORS
import requests
import re
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from SoftwareProject_MovieRecommender_SVD import get_movies_based_on_genres


app = Flask(__name__)
app.secret_key = 'movie_key' 
CORS(app)

#login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id_, username):
        self.id = id_
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('movie.db')
    c = conn.cursor()
    c.execute('SELECT * FROM user WHERE id = ?', (user_id,))
    user_data = c.fetchone()
    conn.close()
    if user_data:
        return User(id_=user_data[0], username=user_data[1])
    return None




OMDB_API_KEY = '6805b76b'  # Your OMDb API key

def get_movie_details(full_title):
    """Get movie details from the OMDb API."""
    # Use regular expression to separate title from year
    match = re.match(r"(.+)\s\((\d{4})\)", full_title)
    if match:
        title, year = match.groups()
    else:
        # If the regex match fails, assume the full title is just the title
        title, year = full_title, None
    
    if title.endswith(', The'):
        title = 'The ' + title[:-5]

    params = {'t': title, 'apikey': OMDB_API_KEY}
    if year:
        params['y'] = year  # Include the year in the search if available

    response = requests.get('https://www.omdbapi.com/', params=params)
    if response.status_code == 200:
        return response.json()
    else:
        # If the response was not OK, print the status code for debugging
        print(f'OMDb API request failed with status code: {response.status_code}')
        return None


# Route for serving the webpage

@app.route('/')
def cover():
    return render_template('cover.html')

#login
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None  # Initialize error variable here
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('movie.db')
        c = conn.cursor()
        c.execute('SELECT * FROM user WHERE username = ?', (username,))
        user_data = c.fetchone()
        conn.close()

        if user_data and check_password_hash(user_data[2], password):
            user = User(id_=user_data[0], username=user_data[1])
            login_user(user)
            return redirect(url_for('home'))
        else:
            error = 'Oops! We couldn’t find a match for that username and password combination. Please try again or reset your password if you’ve forgotten it.'
    return render_template('login.html', error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('cover'))

#register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('movie.db')
        c = conn.cursor()
        
        # Check if the username already exists
        c.execute('SELECT * FROM user WHERE username = ?', (username,))
        if c.fetchone():
            conn.close()
            flash('Username already exists.')
            return redirect(url_for('register'))
        
        # Hash the password and insert the new user into the database
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        c.execute('INSERT INTO user (username, password) VALUES (?, ?)', (username, hashed_password))
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/search')
@login_required
def search():
    return render_template('search.html')


@app.route('/home')
@login_required
def home():
    user_id = current_user.id
    
    # Pagination setup
    page = request.args.get('page', 1, type=int)
    per_page = 4

    conn = sqlite3.connect('movie.db')
    c = conn.cursor()

    # Calculate the total number of favorite movies for the user
    c.execute('SELECT COUNT(*) FROM favorites WHERE user_id = ?', (user_id,))
    total_movies = c.fetchone()[0]

    # Fetch the subset of favorite movies for the current page
    offset = (page - 1) * per_page
    c.execute('SELECT movie_title, movie_poster FROM favorites WHERE user_id = ? ORDER BY movie_title ASC LIMIT ? OFFSET ?', (user_id, per_page, offset))
    favorite_movies_raw = c.fetchall()

    # Fetch ALL favorite movies to calculate genre counts
    c.execute('SELECT movie_title FROM favorites WHERE user_id = ?', (user_id,))
    all_favorite_movies = c.fetchall()

    # Initialize a dictionary to count genres
    genre_counts = {}
    for movie in all_favorite_movies:
        movie_details = get_movie_details(movie[0])  # movie[0] is the movie_title
        if movie_details and movie_details['Response'] == 'True':
            genre = movie_details.get('Genre', 'Unknown').split(', ')[0]
            genre_counts[genre] = genre_counts.get(genre, 0) + 1

    # Process current page's favorite movies
    favorite_movies = []
    for movie in favorite_movies_raw:
        movie_details = get_movie_details(movie[0])  # movie[0] is the movie_title
        if movie_details and movie_details['Response'] == 'True':
            imdb_url = f"https://www.imdb.com/title/{movie_details.get('imdbID')}/"
            genre = movie_details.get('Genre', 'Unknown').split(', ')[0]
            favorite_movies.append((movie[0], movie[1], imdb_url, genre))
        else:
            favorite_movies.append((movie[0], movie[1], '#', 'Unknown'))

    conn.close()

    # Sort genres by count in descending order
    sorted_genre_counts = sorted(genre_counts.items(), key=lambda item: item[1], reverse=True)

    # Calculate total pages
    total_pages = total_movies // per_page + (1 if total_movies % per_page > 0 else 0)

    return render_template('favorites.html', favorite_movies=favorite_movies,
                           favorite_genres=sorted_genre_counts, page=page,
                           total_pages=total_pages, per_page=per_page)






@app.route('/add_to_favorites', methods=['POST'])
@login_required
def add_to_favorites():
    data = request.json
    movie_title = data.get('movie_title')
    movie_poster = data.get('movie_poster')
    movie_genre = data.get('movie_genre') 
    
    user_id = current_user.id  
    
    conn = sqlite3.connect('movie.db')
    c = conn.cursor()

    # Check if the movie is already in the favorites
    c.execute('SELECT * FROM favorites WHERE user_id = ? AND movie_title = ?', (user_id, movie_title))
    if c.fetchone():
        conn.close()
        return jsonify({'status': 'fail', 'message': 'Movie already in favorites'})

    # If not already in favorites, insert the new favorite
    c.execute('INSERT INTO favorites (user_id, movie_title, movie_poster, movie_genre) VALUES (?, ?, ?, ?)', 
              (user_id, movie_title, movie_poster, movie_genre))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success', 'message': 'Movie added to favorites'})

@app.route('/remove_from_favorites', methods=['POST'])
@login_required
def remove_from_favorites():
    data = request.json
    movie_title = data.get('movie_title')
    user_id = current_user.id

    conn = sqlite3.connect('movie.db')
    c = conn.cursor()
    
    # Check if the movie exists in the favorites
    c.execute('SELECT * FROM favorites WHERE user_id = ? AND movie_title = ?', (user_id, movie_title))
    if not c.fetchone():
        conn.close()
        print(f"Movie '{movie_title}' not found in favorites.")
        return jsonify({'status': 'fail', 'message': 'Movie not found in favorites'}), 404
    
    # Delete the movie from the favorites
    c.execute('DELETE FROM favorites WHERE user_id = ? AND movie_title = ?', (user_id, movie_title))
    conn.commit()
    conn.close()

    print(f"Movie '{movie_title}' has been removed from favorites.")
    return jsonify({'status': 'success', 'message': 'Movie removed from favorites'})



@app.route('/favorites/genre/<genre_name>')
@login_required
def favorites_by_genre(genre_name):
    user_id = current_user.id
    conn = sqlite3.connect('movie.db')
    c = conn.cursor()

    # Fetch the favorite movies for the given genre
    c.execute('SELECT movie_title, movie_poster FROM favorites WHERE user_id = ? AND movie_genre = ?', (user_id, genre_name))
    genre_movies_raw = c.fetchall()
    conn.close()

    # Get additional details for each movie
    genre_movies = []
    for movie_title, movie_poster in genre_movies_raw:
        movie_details = get_movie_details(movie_title)
        if movie_details and movie_details['Response'] == 'True':
            imdb_url = f"https://www.imdb.com/title/{movie_details.get('imdbID')}/"
            genre_movies.append((movie_title, movie_poster, imdb_url))
        else:
            genre_movies.append((movie_title, movie_poster, '#'))

    return render_template('favorites_by_genre.html', genre_movies=genre_movies, genre_name=genre_name)


@app.route('/recommended_movies')
@login_required
def recommended_movies():
    user_id = current_user.id
    page = request.args.get('page', 1, type=int)
    per_page = 6  # Number of items per page

    # Fetch latest favorite genres and their counts
    conn = sqlite3.connect('movie.db')
    c = conn.cursor()
    c.execute('''
        SELECT movie_genre, COUNT(movie_genre) as genre_count 
        FROM favorites 
        WHERE user_id = ? 
        GROUP BY movie_genre 
        ORDER BY genre_count DESC
    ''', (user_id,))
    favorite_genres_with_counts = c.fetchall()
    conn.close()

    # Generate recommendations based on the favorite genres sorted by their counts
    all_recommended_movies = []
    for genre, _ in favorite_genres_with_counts:
        genre_recommendations = get_movies_based_on_genres([genre], top_n_per_movie=5)
        all_recommended_movies.extend(genre_recommendations)

    # Remove duplicates while preserving order
    seen = set()
    unique_recommended_movies = [x for x in all_recommended_movies if not (x in seen or seen.add(x))]

    # Limit the recommendations to the first 30 movies
    limited_recommended_movies = unique_recommended_movies[:10]
    
    movie_poster = []
    for i in range(len(limited_recommended_movies)):
        poster_img = get_movie_details(limited_recommended_movies[i]).get('Poster')
        movie_poster.append(poster_img)

    # print(len(movie_poster))

    # Implement pagination within the limited list of recommended movies
    movies_to_show = limited_recommended_movies[(page-1)*per_page : page*per_page]
    posters_to_show = movie_poster[(page-1)*per_page : page*per_page]
    
    # Calculate total pages for pagination
    total_pages = (len(limited_recommended_movies) + per_page - 1) // per_page

    movies_and_posters = zip(movies_to_show, posters_to_show)
    return render_template('recommended_movie.html', movies_and_posters=movies_and_posters, page=page, total_pages=total_pages)





# Route for movie suggestions (for autocomplete or search suggestions)
@app.route('/suggest', methods=['GET'])
def suggest():
    query = request.args.get('query', '')
    suggestions = get_movie_suggestions(query)
    return jsonify(suggestions)

# Route for getting recommendations
@app.route('/recommend', methods=['GET'])
def recommend():
    movie_name_query = request.args.get('movie', '')
    number_of_recommendations = request.args.get('number', 8, type=int)

    # Remove any potential year from the query and convert to lowercase for a case-insensitive match
    movie_name_query_processed = re.sub(r'\(\d{4}\)', '', movie_name_query).lower().strip()

    # Find a match in the dataset without considering the year and in a case-insensitive manner
    matched_movie_title = next((movie for movie in unique_movies if re.sub(r'\(\d{4}\)', '', movie).lower().strip() == movie_name_query_processed), None)

    if matched_movie_title:
        # Fetch more recommendations than needed as some might not have details available
        recommendations = get_similar_movies(matched_movie_title, number_of_recommendations + 10)

        # Fetch movie details for each recommendation using the OMDb API
        detailed_recommendations = []
        for title in recommendations:
            if len(detailed_recommendations) >= number_of_recommendations:
                # Break out of the loop if we have enough recommendations
                break

            movie_details = get_movie_details(title)
            if movie_details and movie_details['Response'] == 'True':
                detailed_recommendations.append({
                    'title': movie_details.get('Title', title),
                    'poster': movie_details.get('Poster', 'Poster not available'),
                    'imdb_url': f"https://www.imdb.com/title/{movie_details.get('imdbID', '')}/",
                    'director': movie_details.get('Director', 'Director not available'),
                    'actors': movie_details.get('Actors', 'Actors not available'),
                    'genre': movie_details.get('Genre', 'Genre not available'),
                    'rating': movie_details.get('imdbRating', 'Rating not available')
                })

        return jsonify(detailed_recommendations)
    else:
        # No exact match found, provide suggestions
        suggestions = get_movie_suggestions(movie_name_query_processed)
        # Convert lowercase suggestions back to original case
        original_case_suggestions = [unique_movies[movies_list_lowercase.index(suggestion.lower())] for suggestion in suggestions if suggestion.lower() in movies_list_lowercase]
        return jsonify({
            'error': "This movie name does not match with any movie in the dataset.",
            'suggestions': original_case_suggestions
        }), 404

    # try:
    #     # Get recommendations if the movie exists
    #     recommendations = get_similar_movies(movie_name, number_of_recommendations)
    #     if recommendations is None:
    #         raise ValueError("No recommendations returned from the model.")

    #     formatted_recommendations = [{'title': title} for title in recommendations]
    #     return jsonify(formatted_recommendations)
    # except (KeyError, ValueError) as e:
    #     return jsonify({'error': str(e)}), 404


if __name__ == '__main__':
    app.run(debug=True)
