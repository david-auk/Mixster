import requests
from flask import request, session, jsonify

from . import media_control_bp

# Spotify API endpoint for checking playback state
SPOTIFY_PLAYER_URL = 'https://api.spotify.com/v1/me/player'


def get_error(response):
    if 'application/json' in response.headers.get('Content-Type', ''):
        response_message = {"error": response.json().get('error', {}).get('message', 'Unknown error')}
    else:
        response_message = {'error': 'Unknown error'}

    return jsonify(response_message), 400


def get_playback_data(access_token):
    headers = {'Authorization': f'Bearer {access_token}', }
    response = requests.get(SPOTIFY_PLAYER_URL, headers = headers)

    if response.status_code != 200:
        return get_error(response)

    return response.json()


def get_device_id(playback_data):
    # Check if there is an active device
    device = playback_data.get('device')
    if device and device.get('is_active'):
        return device.get("id")

    return None


def control_playback(access_token, control_type, device_id=None):

    if not device_id:
        device_id = get_device_id(get_playback_data(access_token))
        if not device_id:
            return jsonify({"error": "no playable device found"}), 400

    headers = {'Authorization': f'Bearer {access_token}'}

    response = requests.put(f"{SPOTIFY_PLAYER_URL}/{control_type}", headers = headers, json = {'device_id': device_id})

    if response.status_code != 200:
        return get_error(response)

    return jsonify({"message": f"playback controlled"}), 200


@media_control_bp.route('/check', methods = ['GET'])
def check_preconditions():
    """
    Method for getting a status of an access_token
    :return: Status of playability
    """
    access_token = session.get('access_token')
    user_vars = session.get('user_vars')

    # Check if user is logged in
    if not access_token or not user_vars:
        return jsonify({
            "status": "error",
            "message": "You are not logged in. Please log in to continue."
        }), 401

    headers = {'Authorization': f'Bearer {access_token}', }

    # Check for an active device
    response = requests.get(SPOTIFY_PLAYER_URL, headers = headers)

    if response.status_code == 200:
        playback_data = response.json()
        device = playback_data.get('device')

        if not device or not device.get('is_active'):
            return jsonify({
                "status": "warning",
                "message": "No active Spotify device detected. Please open Spotify on a device to play tracks."
            }), 200

        return jsonify({
            "status": "success",
            "message": "All systems are ready!"
        }), 200

    if response.status_code == 204:
        return jsonify({
            "status": "warning",
            "message": "No active playback session. Please ensure a Spotify device is active."
        }), 200

    return jsonify({
        "status": "error",
        "message": "Failed to verify playback state. Please try again."
    }), 500


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

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Construct URL with optional device_id query parameter
    url = f"{SPOTIFY_PLAYER_URL}/play"

    # The code below should work but sadly doesn't, there is a spotify bug that gives a 'bad gateway' when a play
    # request is done directly into a device

    # If a device_id is passed, use that for playback device targeting
    device_id = request.json.get("device_id")
    if device_id:
        url += f"?device_id={device_id}"

    response = requests.put(url, headers = headers, json = {'uris': [track_uri]})

    if response.status_code != 204:
        return get_error(response)

    return jsonify({"message": "playing track"}), 200


@media_control_bp.route('/toggle-pause', methods = ["GET", "POST"])
def toggle_pause():
    access_token = session.get('access_token')
    user_vars = session.get('user_vars')
    if not access_token or not user_vars:
        return jsonify({"error": "access_token is required, are you logged in?"}), 400

    # If a device_id is passed, use that for playback device targeting
    playback_data = get_playback_data(access_token)
    device_id = request.json.get("device_id")
    if not device_id:
        device_id = get_device_id(playback_data)

        if not device_id:
            return jsonify({"error": "no playable device found"})

    if isinstance(playback_data, dict) and playback_data["is_playing"]:
        return pause(device_id, playback_data)  # Pause playback if playing
    else:
        return resume(device_id, playback_data)  # Resume playback if paused


@media_control_bp.route('/pause', methods = ["GET"])
def pause(device_id=None, playback_data=None):
    access_token = session.get('access_token')
    user_vars = session.get('user_vars')
    if not access_token or not user_vars:
        return jsonify({"error": "access_token is required, are you logged in?"}), 400

    if not playback_data:
        playback_data = get_playback_data(access_token)
        if not device_id:
            device_id = get_device_id(playback_data)

    if playback_data["is_playing"]:
        return control_playback(access_token, control_type = "pause", device_id = device_id)

    return jsonify({'message': 'track already paused'}), 200


@media_control_bp.route('/resume', methods = ["GET"])
def resume(device_id=None, playback_data=None):
    access_token = session.get('access_token')
    user_vars = session.get('user_vars')
    if not access_token or not user_vars:
        return jsonify({"error": "access_token is required, are you logged in?"}), 400

    if not playback_data:
        playback_data = get_playback_data(access_token)
        if not device_id:
            device_id = get_device_id(playback_data)

    if not playback_data["is_playing"]:
        return control_playback(access_token, control_type = "play", device_id = device_id)

    return jsonify({'message': 'track already playing'}), 200


@media_control_bp.route('/get-current-device', methods = ["GET"])
def get_current_device():
    access_token = session.get('access_token')
    user_vars = session.get('user_vars')
    if not access_token or not user_vars:
        return jsonify({"error": "access_token is required, are you logged in?"}), 400

    device_id = get_device_id(get_playback_data(access_token))

    if device_id:
        return jsonify({'device_id': str(device_id)}), 200
    else:
        return jsonify({'error': 'No playback device found'}), 400
