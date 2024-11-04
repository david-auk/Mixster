from flask import Flask, render_template, request
import spotify

app = Flask(__name__)


@app.route("/export", methods=["GET", "POST"])
def export_playlist():
    if request.method == "POST":
        # Retrieve the playlist link from the input field
        playlist_url = request.form.get("playlist_url")

        playlist = spotify.Playlist(playlist_url)

        for item_uri in playlist.get_items_uri():
            track = spotify.Track(item_uri)

        # For now, just display the URL as confirmation
        return f"<h1>Playlist URL received: {playlist_url}</h1>"

    return render_template("export_playlist.html")


@app.route('/load/<track_id>')
def load_track(track_id):
    #https://open.spotify.com/track/09IGIoxYilGSnU0b0OambC?si=e079268c013e4365
    track = spotify.Track(track_id)

    return f'Name: {track.name}\nArtist: {track.artist}\nDate: {track.release_date}'


if __name__ == '__main__':
    app.run(debug=True)