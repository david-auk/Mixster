from flask import Flask, render_template, request
import spotify

app = Flask(__name__)


@app.route("/export", methods=["GET", "POST"])
def export_playlist():
    if request.method == "POST":
        # Retrieve the playlist link from the input field
        playlist_url = request.form.get("playlist_url")

        tracklist = spotify.get_tracklist_from_playlist(playlist_url)

        for track in tracklist:
            pass

        # For now, just display the URL as confirmation
        return f"<h1>Playlist URL received: {playlist_url}</h1>"

    return render_template("export_playlist.html")


@app.route('/load/<track_id>')
def load_track(track_id):
    return f'{track_id} < track_id'


if __name__ == '__main__':
    app.run(debug=True)