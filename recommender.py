# Contains parts from: https://flask-user.readthedocs.io/en/latest/quickstart_app.html

from flask import Flask, render_template, request
from flask_user import login_required, UserManager, current_user
from datetime import datetime
import pandas as pd
import numpy as np
import warnings
import traceback
from sklearn.metrics import mean_squared_error
from models import db, User, Movie, MovieGenre, MovieTag, MovieLink, Rating, GenreScore
from read_data import check_and_read_data


# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'

    # Flask-SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = 'sqlite:///movie_recommender.sqlite'  # File-based SQL database
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Avoids SQLAlchemy warning

    # Flask-User settings
    USER_APP_NAME = "Movie Recommender"  # Shown in and email templates and page footers
    USER_ENABLE_EMAIL = False  # Disable email authentication
    USER_ENABLE_USERNAME = True  # Enable username authentication
    USER_REQUIRE_RETYPE_PASSWORD = True  # Simplify register form

    # make sure we redirect to home view, not /
    # (otherwise paths for registering, login and logout will not work on the server)
    USER_AFTER_LOGIN_ENDPOINT = 'home_page'
    USER_AFTER_LOGOUT_ENDPOINT = 'home_page'
    USER_AFTER_REGISTER_ENDPOINT = 'home_page'
    USER_AFTER_CONFIRM_ENDPOINT = 'home_page'

# Create Flask app'
app = Flask(__name__, static_url_path='/static')
app = Flask(__name__)
app.config.from_object(__name__ + '.ConfigClass')  # configuration
app.app_context().push()  # create an app context before initializing db
db.init_app(app)  # initialize database
db.create_all()  # create database if necessary
user_manager = UserManager(app, db, User)  # initialize Flask-User management


@app.cli.command('initdb')
def initdb_command():
    global db
    global ratings_matrix
    """Creates the database tables."""
    # Record start time
    start_time = time.time()

    check_and_read_data(db, fewer_ratings=False)
    print('Initialized the database.')
    print(f"Saved {User.query.count()} users from ratings")
    # Record end time
    end_time = time.time()
    # Calculate execution time
    execution_time = end_time - start_time
    print(f"Execution Time for initializing the database: {execution_time} seconds")


# The Home page is accessible to anyone
@app.route('/')
def home_page():
    # render home.html template
    return render_template("home.html")


# The Members page is only accessible to authenticated users via the @login_required decorator
import time
from flask import render_template


# Import other necessary modules

@app.route('/movies')
@login_required  # User must be authenticated
def movies_page():
    # Record start time
    start_time = time.time()

    # get the genre scores of current User
    c_user_genre_scores = GenreScore.query.filter_by(user_id=current_user.id).all()

    # display cold start page if user does not have any genre preferences
    # if rated_movies.count() == 0:
    if len(c_user_genre_scores) == 0:
        # get the genres that can be chosen
        all_genres = set()
        for movie_genre in MovieGenre.query.all():
            all_genres.add(movie_genre.genre)
        return render_template("cold_start.html", genres=all_genres)

    # get all ratings done by the current user
    # then only get movies that have not been rated by current user
    c_user_ratings = Rating.query.filter_by(user_id=current_user.id).subquery()
    c_user_rated_movies = Movie.query.join(c_user_ratings, Movie.id == c_user_ratings.c.movie_id)
    c_user_unrated_movies = Movie.query.except_(c_user_rated_movies)

    print("Movies rated by current user: \n", c_user_rated_movies.all())

    #############################################################
    # get movies based on genre preferences (may take 20-30sec) #
    #############################################################
    movies_genres = []

    # get the genre scores of user, sort them by score and get three favorite genres
    best_genres = GenreScore.query.filter_by(user_id=current_user.id).order_by(GenreScore.score.desc()).limit(3).all()
    print(
        f"The 3 favorite genres of the current user are {best_genres[0].genre}, {best_genres[1].genre}, and {best_genres[2].genre}")

    # filter unrated movies by 3 favorite genres
    movies1 = c_user_unrated_movies.filter(Movie.genres.any(MovieGenre.genre == best_genres[0].genre))
    movies2 = c_user_unrated_movies.filter(Movie.genres.any(MovieGenre.genre == best_genres[1].genre))
    movies3 = c_user_unrated_movies.filter(Movie.genres.any(MovieGenre.genre == best_genres[2].genre))
    movies_genres.extend(movies1.union(movies2).union(movies3).limit(10).all())
    print("Movies selected based on those genres: \n", movies_genres)


    ################################################
    # get movies based on similar user preferences #
    ################################################
    movies_users = []

    if c_user_rated_movies.count() >= 5:

        # make a matrix with all the ratings (user id as row_index, movie_id as column index)
        warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)
        ratings_matrix = pd.DataFrame()
        for rating in Rating.query.all():
            ratings_matrix.loc[str(rating.user_id), str(rating.movie_id)] = rating.rating
        print("Peak into ratings matrix: \n", ratings_matrix.head())

        # get the ratings of current user
        ratings_c_user = ratings_matrix.loc[str(current_user.id)]

        # compute the mean squarred error between the current user ratings and ratings of other users
        distances = {}
        for index, row in ratings_matrix.iterrows():
            if index != str(current_user.id):
                # take only the columns without NaN's (movies they both have rated)
                mask = np.logical_and(np.isfinite(ratings_c_user.values), np.isfinite(row.values))
                current_user_ratings = np.array(ratings_c_user.values)[mask]
                other_user_ratings = np.array(row.values)[mask]
                # if they have movies in common, compute mean squarred error distance
                if any(mask):
                    mse = mean_squared_error([current_user_ratings], [other_user_ratings])
                    distances[str(index)] = mse

        # sort the distances from lowest to highest (https://www.geeksforgeeks.org/python-sort-python-dictionaries-by-key-or-value/)
        # and also remove any users with a too large distance (similarity threshold)
        MAX_DISTANCE = 9  # unrealistic number, just for testing!!! Better would be something like 3 or 5
        keys = list(distances.keys())
        values = list(distances.values())
        high_dist = [int(rating) <= MAX_DISTANCE for rating in values]
        values = np.array(values)[high_dist]
        sorted_value_index = np.argsort(values)
        sorted_distances = {keys[i]: values[i] for i in sorted_value_index}

        print("Distances calculated between current user and other users (sorted): \n", sorted_distances)

        # collect movies liked by similar users (sorted by similarity)
        for (user_id, distance) in sorted_distances.items():
            # get movies rated by this user at least with 4 but not rated by current user
            user_ratings = Rating.query.filter_by(user_id=user_id).filter(Rating.rating >= 4).subquery()
            user_rated_movies = Movie.query.join(user_ratings, Movie.id == user_ratings.c.movie_id)
            movies_users.extend(user_rated_movies.except_(c_user_rated_movies).all())
            print(
                f"Of {user_rated_movies.count()} movies rated positively by user{user_id}, {user_rated_movies.except_(c_user_rated_movies).count()} have not been rated by the current user: ",
                user_rated_movies.except_(c_user_rated_movies).all())

        # delete duplicates and limit recommendet movies list to 10 movies
        movies_users = list(set(movies_users))
        if len(movies_users) > 10:
            movies_users = movies_users[0:10]
        print("Movies selected based on similar users: \n", movies_users)

    # Record end time
    end_time = time.time()
    # Calculate execution time
    execution_time = end_time - start_time
    print(f"Execution Time for getting recommondations: {execution_time} seconds")

    return render_template("movies.html", movies_genres=movies_genres, movies_users=movies_users)


@app.route('/rate', methods=['POST'])
@login_required  # User must be authenticated
def rate():
    movie_id = request.form.get('movieid')
    rating_score = int(request.form.get('rating_score'))
    user_id = current_user.id
    timestamp = f'{datetime.now():%d-%m-%Y %H:%M:%S%z}'
    print(timestamp)

    # if the db does not contain a rating for that movie from that user, save rating
    if Rating.query.filter(Rating.user_id == user_id).filter(Rating.movie_id == movie_id).count() == 0:
        # add rating to database
        rating = Rating(user_id=user_id, movie_id=movie_id,rating=rating_score,timestamp=timestamp)
        db.session.add(rating)
        db.session.commit()  # save data to database
        print("Rate {} for {} by {}".format(rating_score, movie_id, user_id))

        # change the score of the genres dependent on the rating
        # e.g. add -2 to if rating = 1, add +2 if rating = 5
        movie_genres = Movie.query.filter(Movie.id == movie_id).first().genres
        for movie_genre in movie_genres:
            genre = movie_genre.genre
            genre_score = GenreScore.query.filter_by(user_id = user_id).filter_by(genre=genre).first()

            if genre_score == None:
                # if there is no score safed for the genre and the user, create a new one
                db.session.add(GenreScore(user_id=user_id, genre=genre, score=(rating_score - 3))) # (-3 for "mean centering")
                db.session.commit()
                print(f"Score {GenreScore.query.filter_by(user_id = current_user.id).filter_by(genre=genre).first().score} for {genre} has been created")

            else:
                # change the score dependent on the rating
                print(f"Score for {genre} is {genre_score.score}")
                genre_score.score = genre_score.score + (rating_score - 3) # (-3 for "mean centering")
                db.session.commit()
                print(f"Score for {genre} has been changed to {GenreScore.query.filter_by(user_id = current_user.id).filter_by(genre=genre).first().score}")

    else:
        print(f"movie {movie_id} already rated by {user_id}")


    return render_template("rated.html", rating_score=rating_score)

@app.route('/fav_genre', methods=['POST'])
@login_required  # User must be authenticated
def fav_genre():

    SCORE_FOR_CHOSEN_GENRE = 10

    # get the genres chosen by user
    genre1 = request.form.get('genre1')
    genre2 = request.form.get('genre2')
    genre3 = request.form.get('genre3')
    user_id = current_user.id
    print("received genres ", [genre1, genre2, genre3], " for user ", user_id)
    genres = [genre1, genre2, genre3]

    # adds a score for each genre and the user
    db.session.add(GenreScore(user_id=user_id, genre=genre1, score=SCORE_FOR_CHOSEN_GENRE))
    db.session.add(GenreScore(user_id=user_id, genre=genre2, score=SCORE_FOR_CHOSEN_GENRE))
    db.session.add(GenreScore(user_id=user_id, genre=genre3, score=SCORE_FOR_CHOSEN_GENRE))
    db.session.commit()

    return render_template("genre_info.html", genres=genres)



# Import other necessary modules

@app.route('/profile')
@login_required
def profile_page():
    # Get the rated movies for the current user
    user_ratings = Rating.query.filter_by(user_id=current_user.id).all()
    user_rated_movies = [rating.movie for rating in user_ratings]
    rated_movies = []

    # Printing the list using loop
    for movie, rating in zip(user_rated_movies, user_ratings):
        # Access the rating attribute from the relationship
        print(f"Movie: {movie.title}, Rating: {rating.rating}")
        rated_movies.append({'title': movie.title, 'rating': rating.rating})


    # Get the favorite genres for the current user
    favorite_genres = GenreScore.query.filter_by(user_id=current_user.id).order_by(GenreScore.score.desc()).limit(3).all()

    return render_template('profile.html', rated_movies=rated_movies, favorite_genres=favorite_genres)


# Start development web server
if __name__ == '__main__':
    app.run(port=5000, debug=True)

@app.errorhandler(500)
def internal_error(exception):
   return "<pre>"+traceback.format_exc()+"</pre>"