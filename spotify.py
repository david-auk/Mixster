from spotapi import PublicPlaylist
import requests
from bs4 import BeautifulSoup


class Track():
    """docstring for ClassName"""

    def __init__(self, track_uri):
        # Extract track ID from the URI in the format spotify:track:<track_id>
        self.track_id = track_uri.split(":")[-1]
        self.url = f"https://open.spotify.com/track/{self.track_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        response = requests.get(self.url, headers=headers)
        if response.status_code != 200:
            raise Exception("Failed to retrieve track page")

        self.__soup = BeautifulSoup(response.text, "html.parser")

        self.name = self.__soup.find("meta", property="og:title")["content"]
        self.artist = self.__get_from_attr("music:musician_description")
        self.release_date = self.__get_from_attr("music:release_date")

    def __get_from_attr(self, attr):
        return self.__soup.find("meta", attrs={"name": attr})["content"]

def get_tracklist_from_playlist(uri):
    p = PublicPlaylist(uri)
    p.get_playlist_info()
    items = p.get_playlist_info(limit=1000)['data']['playlistV2']['content']['items']

    track_uris = []
    for item in items:
        track_uris.append(get_track_uri_from_track(item))

    return track_uris

def get_track_uri_from_track(track):
    return track['itemV2']['data']['uri']
