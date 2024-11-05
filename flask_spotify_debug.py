from flask import Flask, redirect, render_template, request, session, url_for
import os
import spotify.api

app = Flask(__name__)
app.secret_key = os.urandom(24)


@app.route("/export", methods = ["GET", "POST"])
def export_playlist():
    if request.method == "POST":
        # Retrieve the playlist link from the input field
        playlist_url = request.form.get("playlist_url")

        try:
            playlist = spotify.Playlist(playlist_url)
        except spotify.playlist.PlaylistError as e:
            return f"Failed to load playlist: {e}"

        # for item_uri in playlist.get_items_uri():
        #    track = spotify.Track(item_uri)

        # For now, just display the URL as confirmation
        return f"<h1>Playlist received: {playlist.title}</h1>"

    return render_template("export_playlist.html")


'''Spotify-user specific methods:'''


@app.route('/authenticate')
def login():
    # Step 1: Redirect user to Spotify for authorization
    # Capture the original destination using the 'next' parameter
    next_url = request.args.get('next', '/')
    login_url = spotify.api.Authenticate.get_login_url()
    return redirect(f"{login_url}&state={next_url}")  # Add 'state' parameter for redirection


@app.route(f'/{spotify.api.authenticate.SPOTIFY_CALLBACK_SLUG}')
def callback():
    # Step 2: Spotify redirects back to your callback with an authorization code
    auth_obj = spotify.api.Authenticate(request.args.get('code'))
    session['access_token'] = auth_obj.get_access_token()

    # Retrieve the 'state' parameter for redirection
    next_url = request.args.get('state', '/')
    return redirect(next_url)


@app.route('/play/<track_uri>')
def play_song(track_uri):
    access_token = session.get('access_token')
    if not access_token:
        # Redirect to /authenticate and include the original URL in the 'next' parameter
        return redirect(url_for('login', next = request.path))

    auth_obj = spotify.api.Authenticate(access_token = access_token)
    player = spotify.api.Player(auth_obj)

    try:
        player.play_track(track_uri)
        return "Song is playing in the background!"
    except RuntimeError as e:
        return f"Failed to play song: {e}"


if __name__ == "__main__":
    app.run(debug = True)
