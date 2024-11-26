import mysql.connector
from flask import request, jsonify, send_from_directory

from spotify.playlist import PlaylistDAO
from spotify.playlist_scan import PlaylistScan, PlaylistScanDAO
from spotify.album import AlbumDAO
from spotify.artist import ArtistDAO
from spotify.playlist_scan.interfaces import UpdateWeb
from spotify.track import TrackDAO
from spotify.user import UserDAO
from .cache import Cache
from celery import shared_task
from celery.result import AsyncResult
from . import export_bp
import json
from os import environ

from .backend import PDF


@export_bp.route("/api/start", methods = ["POST"])
def start():

    # For linting
    PlaylistScan.build_from_attributes(request.get_json())

    task = build_track_objects.delay(request.get_json())
    return {"task_id": task.id}


@export_bp.route("/api/stop", methods = ["POST"])
def stop():
    # Import inside function to combat circular import error
    from .. import redis_client

    task_id = request.json.get("task_id")
    if not task_id:
        return jsonify({"error": "Task ID is required"}), 400

    # Stop the task
    status_key = f"task_status:{task_id}"
    redis_client.set(status_key, "stop")
    return jsonify({"message": "Task has been canceled"}), 200


@shared_task(bind = True)
def build_track_objects(self, playlist_scan_attributes: dict):
    from .. import redis_client

    print("started build_tracks")

    playlist_scan = PlaylistScan.build_from_attributes(playlist_scan_attributes)

    print(f'starting {playlist_scan.playlist.title}')

    # Set initial 0% State
    self.update_state(state = "PROSESSING", meta = {'progress': 0})

    total_pages = PDF.get_total_pages(playlist_scan.amount_of_tracks)

    meta = {
        'progress': 0,
        'progress_info': {
            'task_description': 'Scraping Spotify for track info',
            'track_name': "N/A",
            'track_artist': "N/A",
            'iteration': 0,
            'time_left_estimate': "N/A",
            'total_pages': str(total_pages)
        }
    }

    update_obj = UpdateWeb(redis_client = redis_client, status_key = f"task_status:{self.request.id}", update_method = self.update_state, meta = meta)

    with mysql.connector.connect(
        host = environ["MYSQL_HOST"],
        user = environ["MYSQL_USER"],
        password = environ["MYSQL_PASSWORD"],
        database = environ["MYSQL_DATABASE"]
    ) as connection:
        # Create DAO instances
        artist_dao = ArtistDAO(connection)
        album_dao = AlbumDAO(connection, artist_dao)
        track_dao = TrackDAO(connection, album_dao)
        user_dao = UserDAO(connection)
        playlist_dao = PlaylistDAO(connection)
        playlist_scan_dao = PlaylistScanDAO(connection, playlist_dao, user_dao, track_dao)

        # Scan for the dates and update the web interface
        playlist_scan.get_tracks(track_dao, update_obj)

        playlist_scan_dao.put_instance(playlist_scan)

    meta = update_obj.meta

    if update_obj.remote_stop():
        return {"result": "Interrupted"}

    meta['progress_info']['task_description'] = "Exporting data to PDF"

    # Make title filename friendly
    safe_title = playlist_scan.playlist.title
    safe_title = safe_title.lower().replace(' ', '_')
    keepcharacters = ('.', '_')
    safe_title = "".join(c for c in safe_title if c.isalnum() or c in keepcharacters).rstrip()

    # Generate a pdf with the playlist, track_info.
    pdf_output_path = f"/data/playlist/mixster_export_{safe_title}.pdf"

    pdf = PDF(playlist_scan.tracks, {'font_path': environ.get("FONT_PATH")},
              redis_client=redis_client,
              status_key=f"task_status:{self.request.id}",
              update_method=self.update_state,
              meta=meta)

    result = pdf.export(pdf_output_path)

    if result == "USER_EXIT":
        return {"result": "Interrupted"}
    else:

        meta['progress_info']['task_description'] = "Ready to Download"
        meta['progress_info']['total_pages'] = f"({total_pages}/{total_pages})"
        meta['progress_info']['time_left_estimate'] = "0:00:00"
        meta['progress_info']['pdf_filename'] = pdf_output_path.split('/')[-1]

        return meta

@export_bp.route("/api/progress", methods = ["POST"])
def track_progress():
    data = request.get_json()

    try:
        task = AsyncResult(data["task_id"])

        if task.info is None or type(task.info) != dict:
            progress = 0
            progress_info = {}
        else:

            # Handle internal worker errors:
            if task.info.get("state", "") == "ERROR":
                raise AttributeError(str(task.info.get("error_msg", "No message")))

            progress = task.info.get("progress", 0)
            progress_info = task.info.get("progress_info", {})
    except AttributeError as e:
        return {"state": "ERROR", "error_msg": str(e)}

    return {"state": task.state, "progress": progress, "progress_info": progress_info}


@export_bp.route("/api/cache", methods = ["POST"])
def cache_interacter(data=None):
    if data is None:
        data = request.get_json()

    attribute = data.get("attribute")
    key = data.get("key")

    if "get_output_method" in data:  # Run method from cached instance
        if not Cache.has_key(attribute, key):
            return jsonify({"error": "Cache key not found"}), 400

        instance = Cache.get(attribute, key)

        method_name = data.get("get_output_method")

        # Check if the requested method exists and is callable
        if hasattr(instance, method_name) and callable(getattr(instance, method_name)):
            # Run the method and get the output
            method = getattr(instance, method_name)
            output = method()
            return jsonify(output)
        else:
            return jsonify({"error": "Invalid method title"}), 400
    else:
        if not Cache.has_key(attribute, key):
            return jsonify(None)
            # return jsonify({"error": "Cache key not found"}), 400

        return jsonify(Cache.get(attribute, key))
