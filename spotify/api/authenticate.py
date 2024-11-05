import requests
from . import secret

# Spotify API constants

SPOTIFY_CALLBACK_SLUG = 'callback'

SPOTIFY_REDIRECT_URI = 'http://127.0.0.1:5000/' + SPOTIFY_CALLBACK_SLUG  # Replace with your callback URL

# Authorization URL for Spotify
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'

# Your desired song URI (replace with any Spotify track URI)
SONG_URI = 'spotify:track:09IGIoxYilGSnU0b0OambC'

# Spotify scopes needed to control playback
SCOPE = 'user-modify-playback-state user-read-playback-state'


class Authenticate:

    def __init__(self, code=None, access_token=None):

        if code:

            # Authenticate
            auth_response = requests.post(SPOTIFY_TOKEN_URL, data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': SPOTIFY_REDIRECT_URI,
                'client_id': secret.SPOTIFY_CLIENT_ID,
                'client_secret': secret.SPOTIFY_CLIENT_SECRET,
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
        return f"{SPOTIFY_AUTH_URL}?client_id={secret.SPOTIFY_CLIENT_ID}&response_type=code&redirect_uri={SPOTIFY_REDIRECT_URI}&scope={SCOPE}"
