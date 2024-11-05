from .authenticate import Authenticate
import requests

# Spotify API endpoint for playback control
SPOTIFY_PLAYBACK_URL = 'https://api.spotify.com/v1/me/player/play'


class Player:

    def __init__(self, authenticate: Authenticate):
        self.authenticate_obj = authenticate

    def play_track(self, track_uri: str):
        access_token = self.authenticate_obj.get_access_token()

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        json_data = {
            'uris': [track_uri]
        }

        # Sending request to play the song
        response = requests.put(SPOTIFY_PLAYBACK_URL, headers = headers, json = json_data)

        # Throw error if song isn't being played
        if response.status_code != 204:
            raise RuntimeError(
                f"Failed to play song: {response.json().get('error', {}).get('message', 'Unknown error')}")
