from flask import render_template, request
from mariadb import Database
from . import export_bp
import spotify.api
from os import environ

if environ.get('MYSQL_DATABASE') is not None:
    db = Database(
        database = environ.get("MYSQL_DATABASE"),
        user = environ.get("MYSQL_USER"),
        password = environ.get("MYSQL_PASSWORD"),
        host = environ.get("MYSQL_HOST")
    )

@export_bp.route("/", methods = ["GET", "POST"])
def export_playlist():
    if request.method == "POST":
        playlist_url = request.form.get("playlist_url")

        try:
            playlist = spotify.Playlist(playlist_url)
        except spotify.playlist.PrivatePlaylistException as e:
            return f"Playlist is not public: {e}"  # If playlist is private
        except spotify.playlist.PublicPlaylistException as e:
            return f"Failed to pull playlist: {e}"  # If spotapi pull Fails
        except Exception as e:
            return f"Failed to load playlist: {e}"  # Catch-all exception

        # Extract tracks from the playlist
        for track_uri in playlist.get_items_uri():
            track = spotify.Track(track_uri)  # This operation is slow

    return render_template("export/export_playlist.html")
