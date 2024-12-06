from flask import render_template, request, send_from_directory, abort, session, redirect, url_for

from spotify.playlist_scan import PlaylistScan
from spotify.exceptions import URLError, PlaylistException
from spotify.user import User
from .backend import PDF
from .cache import Cache
from . import export_bp
import spotify.utilities


@export_bp.route("/", methods = ["GET", "POST"])
def export_playlist():
    access_token = session.get('access_token')
    user_vars = session.get('user_vars')
    if not access_token or not user_vars:
        return redirect(url_for('auth.login', next = request.path))

    user = User(**user_vars)

    return redirect('/export/check')


@export_bp.route('/scan/<scan_id>')
def scan(scan_id):
    return render_template("export/export.html", playlist_scan_id=scan_id)


@export_bp.route('/check', methods = ["GET", "POST"])
def check():
    """
    Method for rendering the html to enter an url that is checked and added to db
    :return: Rendered HTML page
    """
    access_token = session.get('access_token')
    user_vars = session.get('user_vars')
    if not access_token or not user_vars:
        return redirect(url_for('auth.login', next = request.path))

    user_id = user_vars.get('id')

    if request.method == "POST" and "playlist_url" in request.form:

        playlist_url = request.form.get("playlist_url")
        link_type, link_id = spotify.utilities.extract_spotify_type_id(playlist_url)

        if link_type != "playlist":

            # TODO Redirect to error page
            raise URLError(f"Invalid Spotify URL, expected 'playlist' but got '{link_type}'")

        return redirect(f'/export/check/{link_id}')

    return render_template("export/check.html", user_id = user_id)


@export_bp.route('/check/<playlist_id>')
def check_id(playlist_id):
    """
    Method for rendering the html to enter an url that is checked and added to db
    :return: Rendered HTML page
    """
    access_token = session.get('access_token')
    user_vars = session.get('user_vars')
    if not access_token or not user_vars:
        return redirect(url_for('auth.login', next = request.path))

    return render_template("export/check_id.html", playlist_id=playlist_id)


# Route to serve files from the 'data/playlist/' directory
@export_bp.route('/data/playlist/<filename>')
def serve_file(filename):
    try:
        # Define the directory containing your files
        directory = '/data/playlist'
        # Serve the requested file if it exists
        return send_from_directory(directory, filename)
    except FileNotFoundError:
        # If the file doesn't exist, return a 404 error
        abort(404)
