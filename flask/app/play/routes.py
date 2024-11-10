from flask import render_template, request, session, redirect, url_for
from os import environ
from mariadb import Database
from . import play_bp
import spotify.api

if environ.get('MYSQL_DATABASE') is not None:
    db = Database(
        database = environ.get("MYSQL_DATABASE"),
        user = environ.get("MYSQL_USER"),
        password = environ.get("MYSQL_PASSWORD"),
        host = environ.get("MYSQL_HOST")
    )

@play_bp.route('/<track_uri>')
def play_song(track_uri):

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
