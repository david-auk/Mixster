import mysql.connector
from flask import request, jsonify, send_from_directory, session

from spotify.playlist import PlaylistDAO
from spotify.playlist_scan import PlaylistScan, PlaylistScanDAO
from spotify.album import AlbumDAO
from spotify.artist import ArtistDAO
from spotify.playlist_scan.interfaces import UpdateWeb
from spotify.track import TrackDAO
from spotify.user import UserDAO, User
from .cache import Cache
from celery import shared_task
from celery.result import AsyncResult
from . import export_bp
import json
from os import environ

from .backend import PDF


@export_bp.route("/api/start-build", methods = ["POST"])
def start_build_scan():
    access_token = session.get('access_token')
    user_vars = session.get('user_vars')
    if not access_token or not user_vars:
        return {'error': 'User not logged in'}, 500

    playlist_id = request.get_json().get('playlist_id')

    task = build_playlist_scan.delay(playlist_id, access_token, user_vars)
    return {"task_id": task.id}


@export_bp.route("/api/start-export", methods = ["POST"])
def start_export():

    playlist_scan_id = request.json.get("playlist_scan_id")
    if not playlist_scan_id:
        return jsonify({"error": "playlist_scan_id is required"}), 400

    task = build_pdf.delay(playlist_scan_id)
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


@export_bp.route("/api/get-playlist-details", methods = ["POST"])
def get_playlist_details():
    playlist_scan_id = request.json.get("playlist_scan_id")
    if not playlist_scan_id:
        return jsonify({"error": "playlist_scan_id is required"}), 400

    with mysql.connector.connect(
            host = environ["MYSQL_HOST"],
            user = environ["MYSQL_USER"],
            password = environ["MYSQL_PASSWORD"],
            database = environ["MYSQL_DATABASE"]
    ) as connection:
        playlist_dao = PlaylistDAO(connection)
        playlist = playlist_dao.get_instance_from_scan(playlist_scan_id)

    if playlist:
        return jsonify(playlist.export_attributes()), 200
    else:
        return jsonify({"error": "Error getting playlist object, is the id correct?"}), 400


@shared_task(bind = True)
def build_playlist_scan(self, playlist_id: str, access_token: str, user_vars: dict):
    # Do playlist url linting

    # Build user from user_vars
    user = User(**user_vars)

    # Create PlaylistScan object
    self.update_state(state = "BUILDING", meta = {'progress_info': {'task_description': 'Building Tracks using Spotify API'}})
    try:
        playlist_scan = PlaylistScan.build_from_api(playlist_id, access_token, user)
    except RuntimeError as e:
        return {'state': 'ERROR', 'error_msg': str(e)}

    # Save PlaylistScan object to database
    self.update_state(state = "PUSHING", meta = {'progress_info': {'task_description': 'Pushing Playlist data to Database'}})
    try:
        with mysql.connector.connect(
                host = environ["MYSQL_HOST"],
                user = environ["MYSQL_USER"],
                password = environ["MYSQL_PASSWORD"],
                database = environ["MYSQL_DATABASE"]
        ) as connection:
            # Create DAO instances
            artist_dao = ArtistDAO(connection)
            album_dao = AlbumDAO(connection, artist_dao)
            track_dao = TrackDAO(connection, album_dao, artist_dao)
            user_dao = UserDAO(connection)
            playlist_dao = PlaylistDAO(connection)
            playlist_scan_dao = PlaylistScanDAO(connection, playlist_dao, user_dao, track_dao)
            playlist_scan_dao.put_instance(playlist_scan)
    except Exception as e:
        return {'state': 'ERROR', 'error_msg': str(e)}

    self.update_state(state = "SUCCESS", meta = {'progress_info': {'task_description': 'Playlist initialised', 'playlist_scan_id': playlist_scan.id}})


@shared_task(bind = True)
def build_pdf(self, playlist_scan_id):
    from .. import redis_client

    meta = {
        'progress': 0,
        'progress_info': {
            'task_description': 'Getting Data from Database',
            'track_name': "N/A",
            'track_artist': "N/A",
            'iteration': 0,
            'time_left_estimate': "N/A",
            'total_pages': 'N/A'
        }
    }

    # Set initial 0% State
    self.update_state(state = "PULLING", meta = meta)

    with mysql.connector.connect(
            host = environ["MYSQL_HOST"],
            user = environ["MYSQL_USER"],
            password = environ["MYSQL_PASSWORD"],
            database = environ["MYSQL_DATABASE"]
    ) as connection:
        # Create DAO instances
        artist_dao = ArtistDAO(connection)
        album_dao = AlbumDAO(connection, artist_dao)
        track_dao = TrackDAO(connection, album_dao, artist_dao)
        user_dao = UserDAO(connection)
        playlist_dao = PlaylistDAO(connection)
        playlist_scan_dao = PlaylistScanDAO(connection, playlist_dao, user_dao, track_dao)

        playlist_scan = playlist_scan_dao.get_instance(playlist_scan_id)

        total_pages = PDF.get_total_pages(playlist_scan.amount_of_tracks)
        meta['progress_info']['total_pages'] = str(total_pages)

        updated_tracks = []
        for track in playlist_scan.tracks:
            updated_track = track
            updated_track.url = f"{track.url}?playlist_scan_id={playlist_scan_id}"
            updated_tracks.append(updated_track)

        meta['progress_info']['task_description'] = "Exporting data to PDF"

        # Generate a pdf with the playlist, track_info.
        pdf_output_path = f"/data/playlist/mixster_export_{playlist_scan_id}.pdf"

        pdf = PDF(updated_tracks, {'font_path': environ.get("FONT_PATH")},
                  redis_client = redis_client,
                  status_key = f"task_status:{self.request.id}",
                  update_method = self.update_state,
                  meta = meta)

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
