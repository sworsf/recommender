# Movie Recommender

Movie Recommender is a web application that provides movie recommendations based on user ratings and preferences.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Dependencies](#dependencies)
- [Usage](#usage)


## Features

- **User Authentication:** Allows users to sign up, log in, and log out.
- **Movie Recommendations:** Recommends movies based on user ratings and preferences.
- **Genre Preferences:** Users can set and update their favorite movie genres.
- **Profile Page:** Displays user-rated movies, their ratings, and favorite genres.

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
