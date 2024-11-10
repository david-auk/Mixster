import requests
from os import environ

# Spotify API constants

# Replace with your callback URL
SPOTIFY_REDIRECT_URI = environ.get("SPOTIFY_CALLBACK_URL", "/callback")

# Authorization URL for Spotify
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'

# Spotify scopes needed to control playback
SCOPE = 'user-modify-playback-state'  # user-read-playback-state


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

    @staticmethod
    def get_login_url():
        return f"{SPOTIFY_AUTH_URL}?client_id={Authenticate.__SPOTIFY_CLIENT_ID}&response_type=code&redirect_uri={SPOTIFY_REDIRECT_URI}&scope={SCOPE}"