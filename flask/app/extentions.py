from celery import shared_task
from time import time
from datetime import timedelta

from spotify import Track


@shared_task(bind = True)
def build_track_objects(self, playlist_dict):
    self.update_state(state="PROSESSING", meta={'progress': 0})
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
        time_left_string = str(timedelta(seconds=time_left))

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
