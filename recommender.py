# Contains parts from: https://flask-user.readthedocs.io/en/latest/quickstart_app.html

from flask import Flask, render_template, request
from flask_user import login_required, UserManager, current_user
from datetime import datetime
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from models import db, User, Movie, MovieGenre, MovieTag, MovieLink, Rating, GenreScore
from read_data import check_and_read_data, fill_rating_matrix

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

# Create Flask app
app = Flask(__name__)
app.config.from_object(__name__ + '.ConfigClass')  # configuration
app.app_context().push()  # create an app context before initializing db
db.init_app(app)  # initialize database
db.create_all()  # create database if necessary
user_manager = UserManager(app, db, User)  # initialize Flask-User management
ratings_matrix = pd.DataFrame()


@app.cli.command('initdb')
def initdb_command():
    global db
    global ratings_matrix
    """Creates the database tables."""
    check_and_read_data(db)
    print('Initialized the database.')
    # create a matrix of user ratings
    ratings_matrix = fill_rating_matrix(ratings_matrix)
    print('Initialized the ratings matrix.')
    print('matrix shape: ', ratings_matrix.shape)
    print("Number of users and movies total: ",User.query.count(), Movie.query.count())
    print(ratings_matrix.head())

# The Home page is accessible to anyone
@app.route('/')
def home_page():
    # render home.html template
    return render_template("home.html")


# The Members page is only accessible to authenticated users via the @login_required decorator
@app.route('/movies')
@login_required  # User must be authenticated
def movies_page():  

    # get the genre scores of current User
    c_user_genre_scores = GenreScore.query.filter_by(user_id = current_user.id).all()

    # display cold start page if user does not have any genre preferences
    # if rated_movies.count() == 0:
    if len(c_user_genre_scores) == 0:
        # get the genres that can be chosen
        all_genres = set()
        for movie_genre in MovieGenre.query.all():
            all_genres.add(movie_genre.genre)
        return render_template("cold_start.html", genres=all_genres)
    

    # get the genre scores of user, sort them by score and get three favorite genres
    best_genres = GenreScore.query.filter_by(user_id = current_user.id).order_by(GenreScore.score).limit(3).all()
    print(f"the 3 favorite genres are {best_genres[0].genre}, {best_genres[1].genre}, and {best_genres[2].genre}")

    # get all ratings done by the current user 
    # then only get movies that have not been rated by current user
    c_user_ratings = Rating.query.filter_by(user_id = current_user.id).subquery()
    rated_movies = Movie.query.join(c_user_ratings, Movie.id == c_user_ratings.c.movie_id)
    unrated_movies = Movie.query.except_(rated_movies)

    # filter unrated movies by 3 favorite genres
    movies1 = unrated_movies.filter(Movie.genres.any(MovieGenre.genre == best_genres[0].genre))
    movies2 = unrated_movies.filter(Movie.genres.any(MovieGenre.genre == best_genres[1].genre))
    movies3 = unrated_movies.filter(Movie.genres.any(MovieGenre.genre == best_genres[2].genre))
    genre_movie_selection = movies1.union(movies2).union(movies3).limit(10).all()

    return render_template("movies.html", movies=genre_movie_selection)

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

        # add rating to rating matrix
        global ratings_matrix
        ratings_matrix.loc[str(user_id),str(movie_id)] = rating_score #(-3 for "mean centering")

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

#def recommend_movies(user_id):
@app.cli.command('try_rec')
def recommend_movies():

    user_id = User.query.first().id
    global ratings_matrix
    print("user id: ", user_id)
    print("matrix: ", ratings_matrix.head())
    # get the ratings of current user
    ratings_c_user = ratings_matrix.loc[str(user_id)]
    print("user ratings : ", ratings_c_user)

    cos_matrix = pd.DataFrame(cosine_similarity(ratings_matrix.to_list(), ratings_c_user.to_list()), index=ratings_matrix.index)

    print(cos_matrix.head())

    # for each other user
        # check that its not the current user
        # get ratings of other user
        # calculate and store similarity
    
    # for each user, sorted by similarity
        # take the 4 and 5 star rated movies unknown to current user
    
    # do this until 10 movies reached

# Start development web server
if __name__ == '__main__':
    app.run(port=5000, debug=True)
