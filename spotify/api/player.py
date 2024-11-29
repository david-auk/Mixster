from .authenticate import Authenticate
import requests

# Spotify API endpoints for playback control
SPOTIFY_PLAYBACK_URL = 'https://api.spotify.com/v1/me/player/play'
SPOTIFY_PAUSE_URL = 'https://api.spotify.com/v1/me/player/pause'
SPOTIFY_CURRENT_PLAYBACK_URL = 'https://api.spotify.com/v1/me/player'


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

        response = requests.put(SPOTIFY_PLAYBACK_URL, headers=headers, json=json_data)

        if response.status_code != 204:
            raise RuntimeError(
                f"Failed to play song: {response.json().get('error', {}).get('message', 'Unknown error')}"
            )

    def pause(self):
        access_token = self.authenticate_obj.get_access_token()

        headers = {
            'Authorization': f'Bearer {access_token}',
        }

        response = requests.put(SPOTIFY_PAUSE_URL, headers=headers)

        if response.status_code != 204:
            raise RuntimeError(
                f"Failed to pause playback: {response.json().get('error', {}).get('message', 'Unknown error')}"
            )

    def resume(self):
        access_token = self.authenticate_obj.get_access_token()

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # Sending request to resume playback
        response = requests.put(SPOTIFY_PLAYBACK_URL, headers=headers)

        if response.status_code != 204:
            raise RuntimeError(
                f"Failed to resume playback: {response.json().get('error', {}).get('message', 'Unknown error')}"
            )

    def get_current_playback(self):
        access_token = self.authenticate_obj.get_access_token()

        headers = {
            'Authorization': f'Bearer {access_token}',
        }

        response = requests.get(SPOTIFY_CURRENT_PLAYBACK_URL, headers=headers)

        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to get playback state: {response.json().get('error', {}).get('message', 'Unknown error')}"
            )

        return response.json()

    def toggle_pause(self):
        playback_state = self.get_current_playback()

        if playback_state.get('is_playing'):
            self.pause()
        else:
            self.resume()