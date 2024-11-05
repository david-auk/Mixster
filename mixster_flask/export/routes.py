from flask import render_template, request
from . import export_bp
import spotify.api


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
            return f"Failed to load playlist: {e}"  # Else


        return f"<h1>Playlist received: {playlist.title}</h1>"

    return render_template("export/export_playlist.html")
