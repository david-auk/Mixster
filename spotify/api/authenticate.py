import time
from datetime import datetime

import mysql.connector
import requests
from os import environ
from spotify.user import User, UserDAO

# Spotify API constants

# Replace with your callback URL
SPOTIFY_REDIRECT_URI = environ.get("SPOTIFY_CALLBACK_URL", "/callback")

# Authorization URL for Spotify
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_USER_PROFILE_URL = 'https://api.spotify.com/v1/me'

# Spotify scopes needed to control playback
SCOPE = 'user-modify-playback-state user-read-playback-state user-read-private'


class Authenticate:
    __SPOTIFY_CLIENT_ID = environ.get('SPOTIFY_CLIENT_ID')
    __SPOTIFY_CLIENT_SECRET = environ.get('SPOTIFY_CLIENT_SECRET')

    def __init__(self, code=None, access_token=None):
        if code:
            # Authenticate
            auth_response = requests.post(SPOTIFY_TOKEN_URL, data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': SPOTIFY_REDIRECT_URI,
                'client_id': self.__SPOTIFY_CLIENT_ID,
                'client_secret': self.__SPOTIFY_CLIENT_SECRET,
            })
            auth_response_data = auth_response.json()
            self.__access_token = auth_response_data['access_token']
        elif access_token:
            self.__access_token = access_token
        else:
            raise RuntimeError("Cant initialise without a spotify code response or access_token")

    def get_access_token(self):
        return self.__access_token

    def get_user(self) -> User:
        """Fetches the user's profile information and updates the database"""
        headers = {
            'Authorization': f'Bearer {self.__access_token}'
        }

        response = requests.get(SPOTIFY_USER_PROFILE_URL, headers = headers)
        if response.status_code != 200:
            raise RuntimeError(f"Error fetching user profile: {response.status_code}, {response.text}")

        user_data = response.json()

        with mysql.connector.connect(
                host = environ["MYSQL_HOST"],
                user = environ["MYSQL_USER"],
                password = environ["MYSQL_PASSWORD"],
                database = environ["MYSQL_DATABASE"]
        ) as connection:
            user_dao = UserDAO(connection)

            # Get registry_date or get current date if not found
            user_db = user_dao.get_instance(user_data.get('id'))
            registry_date = user_db.registry_date if user_db else datetime.now()  # Todo update to correct timezone

            user = User(
                id = user_data.get('id'),
                name = user_data.get('display_name'),
                profile_picture_image_url = user_data['images'][0]['url'] if user_data.get('images') else None,
                last_login = datetime.now(),  # Todo update to correct timezone
                registry_date = registry_date
            )

            user_dao.put_instance(user)
            user_dao.update_last_login(user)

        return user

    @staticmethod
    def get_login_url():
        return f"{SPOTIFY_AUTH_URL}?client_id={Authenticate.__SPOTIFY_CLIENT_ID}&response_type=code&redirect_uri={SPOTIFY_REDIRECT_URI}&scope={SCOPE}"
