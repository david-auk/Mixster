from flask import render_template, request

from .backend import PDF
from .cache import Cache
from spotify import Playlist, exeptions
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
    if request.method == "POST" and "playlist_url" in request.form:
        playlist_url = request.form.get("playlist_url")
        try:
            playlist = Playlist(playlist_url)
        except spotify.exeptions.URLError as e:
            return f"URL error: {e}"
        except spotify.exeptions.PlaylistException as e:
            return f"Failed to pull playlist: {e}"  # If spotapi pull Fails
        except Exception as e:
            return f"Unexpected error while pulling playlist: {e}"  # Catch-all exception

        # Add the playlist to the cache, so it can be reused dynamically
        if Cache.has_key('playlist_obj', playlist.id):
            Cache.remove('playlist_obj', playlist.id)

        Cache.add('playlist_obj', playlist.id, playlist)

        return render_template("export/export_playlist_bar.html",
                               playlist_title = playlist.title,
                               image_url = playlist.image_url,
                               playlist_amount_of_tracks = playlist.amount_of_tracks,
                               playlist_id = playlist.id,
                               total_pages = PDF.get_total_pages(playlist.amount_of_tracks))

    return render_template("export/export_playlist.html")
