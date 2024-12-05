from os import environ
import mysql.connector
from flask import render_template, request, session, redirect, url_for, jsonify

from spotify.album import AlbumDAO
from spotify.artist import ArtistDAO
from spotify.playlist import PlaylistDAO
from spotify.playlist_scan import PlaylistScanDAO
from spotify.track import TrackDAO
from spotify.user import UserDAO
from . import scan_bp
import spotify.api

@scan_bp.route('/')
def scan():
    access_token = session.get('access_token')
    user_vars = session.get('user_vars')
    if not access_token or not user_vars:
        return redirect(url_for('auth.login', next = request.path))

    return render_template("scan/scan_card.html")


@scan_bp.route('/get-playlist-data', methods = ["POST"])
def stop():
    scan_id = request.json.get("scan_id")
    if not scan_id:
        return jsonify({"error": "Task ID is required"}), 400

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

        playlist_scan = playlist_scan_dao.get_instance(scan_id)

    return jsonify(playlist_scan.playlist.export_attributes()), 200
