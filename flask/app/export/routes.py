from flask import render_template, request
from celery.result import AsyncResult
from . import extentions
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

        playlist_dict = {
            'url': playlist.url,
            'title': playlist.title,
            'length': playlist.length,
            'image_url': playlist.image_url,
            'track_uris': playlist.get_items_uri()
        }

        return render_template("export/export_playlist_bar.html", playlist = playlist_dict)

    return render_template("export/export_playlist.html")


@export_bp.route("/start", methods = ["POST"])
def start():
    data = request.get_json()
    if not ("track_uris" in data):
        raise RuntimeError("Start command received without usable data")

    task = extentions.build_track_objects.delay(data)
    return {"task_id": task.id}


@export_bp.route("/progress", methods = ["POST"])
def track_progress():
    data = request.get_json()
    task = AsyncResult(data["task_id"])
    if task.info is None:
        progress = 0
        progress_info = {}
    else:
        try:
            progress = task.info.get("progress", 0)
            progress_info = task.info.get("progress_info", {})
        except AttributeError as e:
            return {"state": "ERROR", "error_msg": str(e)}

    return {"state": task.state, "progress": progress, "progress_info": progress_info}


@export_bp.route("/test", methods = ["GET"])
def test():
    pass

    # tracks = session["tracks"]
    # for track in tracks:
    #   print(track.release_date)
