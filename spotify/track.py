from . import utilities


class Track:
    """docstring for ClassName"""

    def __init__(self, track_uri):
        # Extract track ID from the URI in the format spotify:track:<track_id>
        self.track_id = track_uri.split(":")[-1]
        self.url = f"https://open.spotify.com/track/{self.track_id}"

        pull_tries = 5
        for attempt in range(pull_tries):
            attempt += 1
            try:
                self.__soup = utilities.build_soup(self.url)
                break
            except Exception as e:
                if str(e) != "Failed to retrieve track page":
                    raise Exception(e)
                else:
                    if attempt == pull_tries:
                        raise Exception(e)

        self.name = self.__soup.find("meta", property = "og:title")["content"]
        self.artist = self.__soup.find("meta", attrs = {"name": "music:musician_description"})["content"]
        self.release_date = self.__soup.find("meta", attrs = {"name": "music:release_date"})["content"]
