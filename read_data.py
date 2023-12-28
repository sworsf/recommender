import csv
from sqlalchemy.exc import IntegrityError
import pandas as pd
from models import Movie, MovieGenre, MovieLink, MovieTag, Rating, User

def check_and_read_data(db):
    # check if we have movies in the database
    # read data if database is empty
    if Movie.query.count() == 0:
        # read movies from csv
        with open('data/movies.csv', newline='', encoding='utf8') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            count = 0
            for row in reader:
                if count > 0:
                    try:
                        id = row[0]
                        title = row[1]
                        movie = Movie(id=id, title=title)
                        db.session.add(movie)
                        genres = row[2].split('|')  # genres is a list of genres
                        for genre in genres:  # add each genre to the movie_genre table
                            movie_genre = MovieGenre(movie_id=id, genre=genre)
                            db.session.add(movie_genre)
                        db.session.commit()  # save data to database
                    except IntegrityError:
                        print("Ignoring duplicate movie: " + title)
                        db.session.rollback()
                        pass
                count += 1
                if count % 100 == 0:
                    print(count, " movies read")

    if MovieLink.query.count() == 0:
        with open('data/links.csv', newline='', encoding='utf8') as csvfile:
                reader = csv.reader(csvfile, delimiter=',')
                count = 0
                for row in reader:
                    if count > 0:
                        try:
                            movie_id = row[0]
                            imdb_id = row[1]
                            tmdb_id = row[2]
                            link = MovieLink(movie_id=movie_id, imdb_id=imdb_id, tmdb_id=tmdb_id)
                            db.session.add(link)
                            db.session.commit()
                        except IntegrityError:
                            print(f"Ignoring duplicate link for movie ID: {movie_id}")
                            db.session.rollback()
                            pass
                    count += 1
                    if count % 100 == 0:
                        print(count, " links read")

        if MovieTag.query.count() == 0:
            with open('data/tags.csv', newline='', encoding='utf8') as csvfile:
                reader = csv.reader(csvfile, delimiter=',')
                count = 0
                for row in reader:
                    if count > 0:
                        try:
                            user_id = row[0]
                            movie_id = row[1]
                            tag = row[2]
                            timestamp = row[3] 
                            tag_entry = MovieTag(user_id=user_id, movie_id=movie_id, tag=tag, timestamp=timestamp)
                            db.session.add(tag_entry)
                            db.session.commit()
                        except IntegrityError:
                            print(f"Ignoring duplicate tag for movie ID: {movie_id}")
                            db.session.rollback()
                            pass
                    count += 1
                    if count % 100 == 0:
                        print(count, " tags read")

    # Specify the fraction of the data we want to include in the smaller file version
    sample_fraction = 0.05  # Adjust as needed

    # Read the original CSV file using pandas
    original_data = pd.read_csv('data/ratings.csv')

    # Sample a fraction of the data
    smaller_data = original_data.sample(frac=sample_fraction, random_state=42)

    # Write the smaller data to a new CSV file ratings_small.csv
    smaller_data.to_csv('data/ratings_small.csv', index=False)

    if Rating.query.count() == 0:

        # read ratings from csv
        with open('data/ratings_small.csv', newline='', encoding='utf8') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            count = 0
            for row in reader:
                if count > 0:
                    try:
                        user_id = row[0]
                        #create user objects/db entires for the users found in the rating file
                        user = User(id=user_id, active=1)
                        db.session.add(user)
                        movie_id = row[1]
                        rating_score = row[2]
                        timestamp = row[3]
                        rating = Rating(user_id=user_id, movie_id=movie_id,rating=rating_score,timestamp=timestamp )
                        db.session.add(rating)
                        db.session.commit()  # save data to database
                    except IntegrityError:
                        #print("Rating Object:", rating.__dict__)
                        db.session.rollback()
                        pass
                count += 1
                if count % 100 == 0:
                    print(count, " ratings read")