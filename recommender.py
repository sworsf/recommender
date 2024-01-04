# Contains parts from: https://flask-user.readthedocs.io/en/latest/quickstart_app.html

from flask import Flask, render_template, request
from flask_user import login_required, UserManager, current_user
from datetime import datetime

from models import db, User, Movie, MovieGenre, MovieTag, MovieLink, Rating
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

# Create Flask app
app = Flask(__name__)
app.config.from_object(__name__ + '.ConfigClass')  # configuration
app.app_context().push()  # create an app context before initializing db
db.init_app(app)  # initialize database
db.create_all()  # create database if necessary
user_manager = UserManager(app, db, User)  # initialize Flask-User management


@app.cli.command('initdb')
def initdb_command():
    global db
    """Creates the database tables."""
    check_and_read_data(db)
    print('Initialized the database.')

# The Home page is accessible to anyone
@app.route('/')
def home_page():
    # render home.html template
    return render_template("home.html")


# The Members page is only accessible to authenticated users via the @login_required decorator
@app.route('/movies')
@login_required  # User must be authenticated
def movies_page():
    # String-based templates

    # first 10 movies
    movies = Movie.query.limit(10).all()

    # only Romance movies
    # movies = Movie.query.filter(Movie.genres.any(MovieGenre.genre == 'Romance')).limit(10).all()

    # only Romance AND Horror movies
    # movies = Movie.query\
    #     .filter(Movie.genres.any(MovieGenre.genre == 'Romance')) \
    #     .filter(Movie.genres.any(MovieGenre.genre == 'Horror')) \
    #     .limit(10).all()

    return render_template("movies.html", movies=movies)

@app.route('/rate', methods=['POST'])
@login_required  # User must be authenticated
def rate():
    movie_id = request.form.get('movieid')
    rating_score = request.form.get('rating_score')
    user_id = current_user.id
    timestamp = f'{datetime.now():%d-%m-%Y %H:%M:%S%z}'
    print(timestamp)

    # if the db does not contain a rating for movie from that user, save rating
    if Rating.query.filter(Rating.user_id == user_id).filter(Rating.movie_id == movie_id).count() == 0:
        rating = Rating(user_id=user_id, movie_id=movie_id,rating=rating_score,timestamp=timestamp)
        db.session.add(rating)
        db.session.commit()  # save data to database
        print("Rate {} for {} by {}".format(rating_score, movie_id, user_id))
    else:
        print(f"movie {movie_id} already rated by {user_id}")
    return render_template("rated.html", rating_score=rating_score)

# Start development web server
if __name__ == '__main__':
    app.run(port=5000, debug=True)
