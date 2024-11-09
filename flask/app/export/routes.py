from flask import render_template, request, jsonify
from . import export_bp
import spotify.api


@export_bp.route("/", methods=["GET", "POST"])
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
            return f"Failed to load playlist: {e}"  # Catch-all exception

        # Extract tracks from the playlist
        track_names = []
        for track_uri in playlist.get_items_uri():
            track = spotify.Track(track_uri)  # This operation is slow
            track_names.append(track.name)

        # You can return the track names or simply indicate success
        return jsonify({
            "message": f"Playlist received: {playlist.title}",
            "tracks": track_names  # Optional: include the tracks
        })

    return render_template("export/export_playlist.html")