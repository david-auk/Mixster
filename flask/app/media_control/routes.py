from flask import render_template, request, session, redirect, url_for, jsonify

from . import media_control_bp
import spotify.api


# TODO Make more modular & fix play/pause playback

@media_control_bp.route('/play', methods = ["POST"])
def play():
    access_token = session.get('access_token')
    user_vars = session.get('user_vars')
    if not access_token or not user_vars:
        return jsonify({"error": "access_token is required, are you logged in?"}), 400

    track_id = request.json.get("track_id")
    if not track_id:
        return jsonify({"error": "track_id is required"}), 400

    track_uri = f"spotify:track:{track_id}"

    auth_obj = spotify.api.Authenticate(access_token = access_token)
    player = spotify.api.Player(auth_obj)

    try:
        player.play_track(track_uri)
        return jsonify({"message": "playing track"}), 400
    except RuntimeError as e:
        jsonify({"error": str(e)}), 400


@media_control_bp.route('/toggle-pause', methods=["POST"])
def toggle_pause():
    access_token = session.get('access_token')
    user_vars = session.get('user_vars')
    if not access_token or not user_vars:
        return jsonify({"error": "access_token is required, are you logged in?"}), 400

    auth_obj = spotify.api.Authenticate(access_token=access_token)
    player = spotify.api.Player(auth_obj)

    try:
        # Get current playback state
        playback_state = player.get_current_playback()
        if playback_state is None:
            return jsonify({"error": "No playback state available"}), 400

        if playback_state["is_playing"]:
            player.pause()  # Pause playback if playing
            return jsonify({"message": "playback paused"}), 200
        else:
            player.resume()  # Resume playback if paused
            return jsonify({"message": "playback resumed"}), 200
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400


@media_control_bp.route('/pause', methods=["POST"])
def pause():
    access_token = session.get('access_token')
    user_vars = session.get('user_vars')
    if not access_token or not user_vars:
        return jsonify({"error": "access_token is required, are you logged in?"}), 400

    auth_obj = spotify.api.Authenticate(access_token=access_token)
    player = spotify.api.Player(auth_obj)

    try:
        player.pause()  # Spotify API call to pause playback
        return jsonify({"message": "playback paused"}), 200
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400
