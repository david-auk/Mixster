from flask import request
from celery import shared_task
from celery.result import AsyncResult
from time import time
from datetime import timedelta
from . import export_bp

from spotify import Track


@export_bp.route("/start", methods = ["POST"])
def start():
    data = request.get_json()
    if not ("track_uris" in data):
        raise RuntimeError("Start command received without usable data")

    task = build_track_objects.delay(data)
    return {"task_id": task.id}


@shared_task(bind = True)
def build_track_objects(self, playlist_dict):
    self.update_state(state = "PROSESSING", meta = {'progress': 0})
    increment = 100 / playlist_dict["length"]
    runtimes = []
    for index, track_uri in enumerate(playlist_dict["track_uris"]):
        progress = increment * (index + 1)

        start_time = time()

        # Get the track object
        track = Track(track_uri)

        # Do analytics
        runtimes.append(time() - start_time)
        avg_time = sum(runtimes) / len(runtimes)
        time_left = round(avg_time * (playlist_dict["length"] - index))
        time_left_string = str(timedelta(seconds = time_left))

        self.update_state(state = "PROSESSING", meta = {
            'progress': progress,
            'progress_info': {
                'track_name': track.name,
                'track_artist': track.artist,
                'iteration': index,
                'time_left_estimate': time_left_string
            }
        })

    return {"result": "Task is done!", "progress": 100}


@export_bp.route("/progress", methods = ["POST"])
def track_progress():
    data = request.get_json()
    task = AsyncResult(data["task_id"])
    if task.info is None:
        progress = 0
        progress_info = {}
    else:
        try:
            progress = task.info.get("progress", 0)
            progress_info = task.info.get("progress_info", {})
        except AttributeError as e:
            return {"state": "ERROR", "error_msg": str(e)}

    return {"state": task.state, "progress": progress, "progress_info": progress_info}
