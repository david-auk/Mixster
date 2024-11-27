from flask import render_template, request, send_from_directory, abort, session, redirect, url_for

from spotify.playlist_scan import PlaylistScan
from spotify.exceptions import URLError, PlaylistException
from spotify.user import User
from .backend import PDF
from .cache import Cache
from . import export_bp
import spotify.api

@export_bp.route("/", methods = ["GET", "POST"])
def export_playlist():

    access_token = session.get('access_token')
    user_vars = session.get('user_vars')
    if not access_token or not user_vars:
        return redirect(url_for('auth.login', next = request.path))

    user = User(**user_vars)

    if request.method == "POST" and "playlist_url" in request.form:
        playlist_url = request.form.get("playlist_url")
        try:
            playlist_scan = PlaylistScan.build_from_url(playlist_url, user)
        except URLError as e:
            return f"URL error: {e}"
        except PlaylistException as e:
            return f"Failed to pull playlist: {e}"  # If spotapi pull Fails
        except Exception as e:
            return f"Unexpected error while pulling playlist: {e}"  # Catch-all exception

        # Add the playlist to the cache, so it can be reused dynamically
        if Cache.has_key('playlist_scan_obj', playlist_scan.playlist.id):
            Cache.remove('playlist_scan_obj', playlist_scan.playlist.id)

        # TODO make more unique so duplicate requests are impossible
        Cache.add('playlist_scan_obj', playlist_scan.playlist.id, playlist_scan)

        return render_template("export/export_playlist_bar.html",
                               playlist_title = playlist_scan.playlist.title,
                               image_url = playlist_scan.playlist.cover_image_url,
                               playlist_amount_of_tracks = playlist_scan.amount_of_tracks,
                               playlist_id = playlist_scan.playlist.id,
                               total_pages = PDF.get_total_pages(playlist_scan.amount_of_tracks))

    return render_template("export/export_playlist.html")


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