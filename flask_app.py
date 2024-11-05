from flask import Flask, render_template, request
import spotify



app = Flask(__name__)





@app.route('/load/<track_id>')
def load_track(track_id):
    #https://open.spotify.com/track/09IGIoxYilGSnU0b0OambC?si=e079268c013e4365
    track = spotify.Track(track_id)

    return f'Name: {track.name}\nArtist: {track.artist}\nDate: {track.release_date}'


if __name__ == '__main__':
    app.run(debug=True)