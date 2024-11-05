from flask import render_template, request
from . import export_bp
import spotify.api


@export_bp.route("/", methods = ["GET", "POST"])
def export_playlist():
    if request.method == "POST":
        playlist_url = request.form.get("playlist_url")

        try:
            playlist = spotify.Playlist(playlist_url)
        except spotify.playlist.PlaylistError as e:
            return f"Failed to load playlist: {e}"

        return f"<h1>Playlist received: {playlist.title}</h1>"

    return render_template("export/export_playlist.html")
