from flask import render_template, request, session, redirect, url_for
from . import play_bp
import spotify.api


@play_bp.route('/<track_uri>')
def play_song(track_uri):

    # https://blog.minhazav.dev/QR-and-barcode-scanner-using-html-and-javascript/

    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('auth.login', next = request.path))

    auth_obj = spotify.api.Authenticate(access_token = access_token)
    player = spotify.api.Player(auth_obj)

    try:
        player.play_track(track_uri)
        return "Song is playing in the background!"
    except RuntimeError as e:
        return f"Failed to play song: {e}"
