import mysql.connector
from flask import request, jsonify, session

from spotify.playlist import PlaylistDAO, Playlist
from spotify.playlist_scan import PlaylistScan, PlaylistScanDAO
from spotify.album import AlbumDAO
from spotify.artist import ArtistDAO
from spotify.track import TrackDAO
from spotify.user import UserDAO, User
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

    config = request.json.get("config")
    if not config:
        return jsonify({"error": "config json is required"}), 400

    task = build_pdf.delay(playlist_scan_id, config)
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

    config = request.json.get("config")
    if not config:
        return jsonify({"error": "config json is required"}), 400

    with mysql.connector.connect(
            host = environ["MYSQL_HOST"],
            user = environ["MYSQL_USER"],
            password = environ["MYSQL_PASSWORD"],
            database = environ["MYSQL_DATABASE"]
    ) as connection:
        artist_dao = ArtistDAO(connection)
        album_dao = AlbumDAO(connection, artist_dao)
        track_dao = TrackDAO(connection, album_dao, artist_dao)
        user_dao = UserDAO(connection)
        playlist_dao = PlaylistDAO(connection)
        playlist_scan_dao = PlaylistScanDAO(connection, playlist_dao, user_dao, track_dao)

        if config.get('extend_scan', None) and config['extend_scan'] != "":
            newer_than_date = playlist_scan_dao.get_attributes(config['extend_scan'], ('ps.timestamp',))['timestamp']
        else:
            newer_than_date = None

        attributes = playlist_scan_dao.get_attributes(playlist_scan_id, (
            'p.title', 'p.id AS playlist_id', 'p.cover_image_url', 'ps.export_completed'
        ))

        # Get all the available previous scans to extend from
        attributes['extend_options'] = playlist_scan_dao.get_available_scans_to_extend_from(attributes['playlist_id'])

        if config.get('only_unique', False):
            track_attributes = playlist_scan_dao.get_track_attributes(playlist_scan_id, (
                'COUNT(DISTINCT track_id) as amount_of_unique_tracks',
            ), newer_than_date)
            attributes['amount_of_tracks'] = track_attributes['amount_of_unique_tracks'] if track_attributes['amount_of_unique_tracks'] else 0
        else:
            track_attributes = playlist_scan_dao.get_track_attributes(playlist_scan_id, (
                'COUNT(track_id) as amount_of_tracks',
            ), newer_than_date)
            attributes['amount_of_tracks'] = track_attributes['amount_of_tracks'] if track_attributes['amount_of_tracks'] else 0

        attributes['total_pages'] = PDF.get_total_pages(attributes['amount_of_tracks'], config.get('pdf_layout_style', 'default'))

    if attributes:
        return jsonify(attributes), 200
    else:
        return jsonify({"error": "Error getting playlist object, is the id correct?"}), 400


@shared_task(bind = True)
def build_playlist_scan(self, playlist_id: str, access_token: str, user_vars: dict):
    # Do playlist url linting
    self.update_state(state = "BUILDING",
                      meta = {'progress_info': {'task_description': 'Getting Playlist info'}})

    try:
        playlist = Playlist.build_from_url(f"https://open.spotify.com/playlist/{playlist_id}")
    except Exception as e:
        return {'state': 'ERROR', 'error_msg': str(e)}

    # Build user from user_vars
    user = User(**user_vars)

    # Create PlaylistScan object
    self.update_state(state = "BUILDING", meta = {'progress_info': {'task_description': 'Building Tracks using Spotify API'}})
    try:
        playlist_scan = PlaylistScan.build_from_api(playlist.id, access_token, user)
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
def build_pdf(self, playlist_scan_id: str, config: dict):
    from .. import redis_client

    # Lint build_config

    meta = {
        'progress': 0,
        'progress_info': {
            'task_description': 'Getting Data from Database',
            'track_name': "N/A",
            'track_artist': "N/A",
            'iteration': 0,
            'time_left_estimate': "N/A",
            'total_tracks': '',
            'total_pages': ''
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

        if config.get("extend_scan", None):
            extends_playlist_scan = playlist_scan_dao.get_instance(config['extend_scan'])
            playlist_scan = playlist_scan_dao.get_instance(playlist_scan_id, config.get('only_unique', False), tracks_newer_than = extends_playlist_scan.created_at)
            playlist_scan.extends_playlist_scan = extends_playlist_scan
        else:
            playlist_scan = playlist_scan_dao.get_instance(playlist_scan_id, config.get('only_unique', False))

        amount_of_tracks = len(playlist_scan.tracks)

        # Set initial 0% State
        meta['progress_info']['total_tracks'] = str(amount_of_tracks)

        total_pages = PDF.get_total_pages(amount_of_tracks, config.get('pdf_layout_style', 'default'))
        meta['progress_info']['total_pages'] = str(total_pages)

        self.update_state(state = "PULLING", meta = meta)

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
                  meta = meta,
                  layout_style = config.get('pdf_layout_style', 'default'))

        result = pdf.export(pdf_output_path)

        if result == "USER_EXIT":
            return {"result": "Interrupted"}
        else:

            # Push to Database
            playlist_scan.export_completed = True
            playlist_scan_dao.put_instance(playlist_scan)

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