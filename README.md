# Movie Recommender

Movie Recommender is a web application that provides movie recommendations based on user ratings and preferences.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Dependencies](#dependencies)
- [Usage](#usage)


## Features

- **Cold start solution:** Users choose 3 initial favorite genres, if no genre preferation are stored for them already. This way some meaningful recommandations can be made from the start. The 3 chosen genres are initialized with a genre score of 10.
- **Two Movie Recommondatins:** There are two types of recommondations available to the user. Genre based and User-user based recommondations.  
  - For the genre based recommondations 10 movies are presented, each belonging to one of the three favorite genres of the user (the genres with the highest genre scores). Also it is made sure, that the movies recommended have not been rated by the current user before.
  - The User-User based recommondations are based on similar users and are only accesible, if the current user has rated at least 5 movies. To get the recommondations, the mean squarred error is calculated between each the current user and each other user, only for those movies, both of them have rated. In order of similarity, from those users, who pass a similarity threshold (MSE <= 9) , the movies which received a rating of 4 or 5 and have not been watched by the current user are extracted. Of those, the first 10 at most are displayed to the current user as recommondations for rating.
- **Updating genre scores when rating:** The genre preference of the user is kept up to data. Whenever a user rates a movie, the genre scores for each genre the movie belongs to are updated. If the rating score is 3 the genre scores stay the same. For ratings of 1 the genre score decreases by 2, respectively for ratings of 5 the genre score increases by 2.
- **Notification for missing recommondations:** If their are no user-user based recommondations, a Notification is displayed instead. This happens when the current user has not fullfilled the condition of at least 5 ratings, or no movies fullfill the condition of being positively rated by similar users and to not be rated by the current user already. This can happen easily with the sparsity of the rating data available. 
- **Profile Page:** Displays user-rated movies, their ratings, and favorite genres.
- **Adapted Design:** The style of the recommender is adapted slightly (colors, positions, navigations, homepage) for aesthetics and easy use.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/sworsf/recommender.git

2. Install dependencies:
    ```bash
    pip install -r requirements.txt

3. Initialize the database:
    ```bash
   flask --app recommender.py initdb

## Dependencies
* Flask
* Flask-User
* Flask-SQLAlchemy
* NumPy
* Pandas
* Bootstrap (for styling)


## Usage
1. Run the project on the server
    ```bash
   flask --app recommender.py run
   
2. Open the application in your web browser:
http://localhost:5000
