from flask import Flask, redirect, request, session
import requests
import os
import secret

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Spotify API constants

SPOTIFY_REDIRECT_URI = 'http://127.0.0.1:5000/callback'  # Replace with your callback URL

# Authorization URL for Spotify
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'

# Spotify API endpoint for playback control
SPOTIFY_PLAYBACK_URL = 'https://api.spotify.com/v1/me/player/play'

# Your desired song URI (replace with any Spotify track URI)
SONG_URI = 'spotify:track:09IGIoxYilGSnU0b0OambC'

# Spotify scopes needed to control playback
SCOPE = 'user-modify-playback-state user-read-playback-state'


@app.route('/authenticate')
def login():
    # Step 1: Redirect user to Spotify for authorization
    return redirect(f"{SPOTIFY_AUTH_URL}?client_id={secret.SPOTIFY_CLIENT_ID}&response_type=code&redirect_uri={SPOTIFY_REDIRECT_URI}&scope={SCOPE}")


@app.route('/callback')
def callback():
    # Step 2: Spotify redirects back to your callback with an authorization code
    code = request.args.get('code')
    # Step 3: Exchange code for access token
    auth_response = requests.post(SPOTIFY_TOKEN_URL, data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': SPOTIFY_REDIRECT_URI,
        'client_id': secret.SPOTIFY_CLIENT_ID,
        'client_secret': secret.SPOTIFY_CLIENT_SECRET,
    })
    auth_response_data = auth_response.json()
    session['access_token'] = auth_response_data['access_token']
    return "Authorization successful! You can now play music."


@app.route('/play-song')
def play_song():
    access_token = session.get('access_token')
    if not access_token:
        return redirect('/authenticate')

    # Step 4: Control playback on the user’s device
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    json_data = {
        'uris': [SONG_URI]
    }

    # Sending request to play the song
    response = requests.put(SPOTIFY_PLAYBACK_URL, headers=headers, json=json_data)

    if response.status_code == 204:
        return "Song is playing in the background!"
    else:
        return f"Failed to play song: {response.json().get('error', {}).get('message', 'Unknown error')}"

if __name__ == "__main__":
    app.run(debug=True)