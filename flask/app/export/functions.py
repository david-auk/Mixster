from flask import request, jsonify

from .cache import Cache
from celery import shared_task
from celery.result import AsyncResult
from time import time
from datetime import timedelta
from . import export_bp
import json

from spotify import Track

@export_bp.route("/api/start", methods = ["POST"])
def start():
    data = json.loads(request.get_json())
    if not "track_uris" in data:
        raise RuntimeError("Start command received without usable data")

    task = build_track_objects.delay(data)
    return {"task_id": task.id}

@export_bp.route("/api/stop", methods = ["POST"])
def stop():

    # Import inside function to combat circular import error
    from .. import redis_client

    task_id = request.json.get("task_id")
    if not task_id:
        return jsonify({"error": "Task ID is required"}), 400

    # Stop the task
    status_key = f"task_status:{task_id}"
    redis_client.set(status_key, "stop")
    return jsonify({"message": "Task has been canceled"}), 200


@shared_task(bind = True)
def build_track_objects(self, playlist_dict):

    from .. import redis_client

    task_id = self.request.id
    status_key = f"task_status:{task_id}"

    self.update_state(state = "PROSESSING", meta = {'progress': 0})
    increment = 100 / playlist_dict["amount_of_tracks"]
    runtimes = []
    stopping = False
    for iteration, track_uri in enumerate(playlist_dict["track_uris"], 1):

        user_input = redis_client.get(status_key)
        if user_input and user_input.decode() == "stop":
            stopping = True
            break

        progress = increment * iteration
        start_time = time()

        # Get the track object
        track = Track(track_uri)

        # Do analytics
        runtimes.append(time() - start_time)
        avg_time = sum(runtimes) / len(runtimes)
        time_left = round(avg_time * (playlist_dict["amount_of_tracks"] - iteration))
        time_left_string = str(timedelta(seconds = time_left))

        # Send status
        self.update_state(state = "PROSESSING", meta = {
            'progress': progress,
            'progress_info': {
                'track_name': track.name,
                'track_artist': track.artist,
                'iteration': iteration,
                'time_left_estimate': time_left_string
            }
        })

    if stopping:
        return {"result": "Interrupted"}

    return {"result": "Task is done!",
        "progress": 100,
        'progress_info': {
            'track_name': track.name,
            'track_artist': track.artist,
            'iteration': iteration,
            'time_left_estimate': time_left_string
        }
    }


@export_bp.route("/api/progress", methods = ["POST"])
def track_progress():
    data = request.get_json()

    try:
        task = AsyncResult(data["task_id"])

        if task.info is None or type(task.info) != dict:
            progress = 0
            progress_info = {}
        else:

            # Handle internal worker errors:
            if task.info.get("state", "") == "ERROR":
                raise AttributeError(str(task.info.get("error_msg", "No message")))

            progress = task.info.get("progress", 0)
            progress_info = task.info.get("progress_info", {})
    except AttributeError as e:
        return {"state": "ERROR", "error_msg": str(e)}

    return {"state": task.state, "progress": progress, "progress_info": progress_info}


@export_bp.route("/api/cache", methods = ["POST"])
def cache_interacter(data=None):
    if data is None:
        data = request.get_json()

    attribute = data.get("attribute")
    key = data.get("key")

    if "get_output_method" in data:  # Run method from cached instance
        if not Cache.has_key(attribute, key):
            return jsonify({"error": "Cache key not found"}), 400

        instance = Cache.get(attribute, key)

        method_name = data.get("get_output_method")

        # Check if the requested method exists and is callable
        if hasattr(instance, method_name) and callable(getattr(instance, method_name)):
            # Run the method and get the output
            method = getattr(instance, method_name)
            output = method()
            return jsonify(output)
        else:
            return jsonify({"error": "Invalid method name"}), 400
    else:
        if not Cache.has_key(attribute, key):
            return jsonify(None)
            # return jsonify({"error": "Cache key not found"}), 400

        return jsonify(Cache.get(attribute, key))