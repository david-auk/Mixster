from abc import ABC, abstractmethod
from datetime import timedelta
from time import time

from spotify.track import Track


class Update(ABC):
    @abstractmethod
    def get_analytics(self, iteration: int, total_iterations: int, current_track: Track):
        pass

    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def remote_stop(self) -> bool:
        pass


class UpdateWeb(Update):
    def __init__(self, redis_client, status_key: str, update_method, meta: dict):
        self.meta = meta
        self.update_method = update_method
        self.status_key = status_key
        self.redis_client = redis_client

        self.start_time = time()
        self.runtimes = []

    def get_analytics(self, iteration: int, total_iterations: int, current_track: Track):

        analytics = {}

        # Progress
        increment = 100 / total_iterations
        self.meta['progress'] = increment * iteration
        self.meta['progress_info']['iteration'] = iteration

        # Time left
        self.runtimes.append(time() - self.start_time)
        avg_time = sum(self.runtimes) / len(self.runtimes)
        time_left = round(avg_time * (total_iterations - iteration))
        analytics['time_left_string'] = str(timedelta(seconds = time_left))

        # Track info
        self.meta['progress_info']['track_name'] = current_track.title
        self.meta['progress_info']['track_artist'] = current_track.album.get_artist_name()

        # For next iter
        self.start_time = time()

        return self.meta

    def update(self):

        # Update status
        #self.meta['progress'] = analytics['progress']  #
        #self.meta['progress_info']['track_name'] = analytics['track_title']
        #self.meta['progress_info']['track_artist'] = analytics['track_artist']
        #self.meta['progress_info']['iteration'] = analytics['iteration']
        #self.meta['progress_info']['time_left_estimate'] = analytics['time_left_string']

        # Send status
        self.update_method(state = "PROSESSING", meta = self.meta)

    def remote_stop(self) -> bool:
        user_input = self.redis_client.get(self.status_key)
        if user_input and user_input.decode() == "stop":
            return True

        return False


class UpdateStdOut(Update):
    def __init__(self):
        self.meta = {}

    def get_analytics(self, iteration: int, total_iterations: int, current_track: Track):
        self.meta['iteration'] = iteration
        self.meta['track'] = current_track

    def update(self):
        print(self.meta)

    def remote_stop(self) -> bool:
        return False
