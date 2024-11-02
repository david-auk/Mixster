import json

import spotapi
from spotapi import PublicPlaylist
import requests
from bs4 import BeautifulSoup


def build_soup(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    response = requests.get(url, headers = headers)
    if response.status_code != 200:
        raise Exception("Failed to retrieve track page")

    return BeautifulSoup(response.text, "html.parser")


class Track:
    """docstring for ClassName"""

    def __init__(self, track_uri):
        # Extract track ID from the URI in the format spotify:track:<track_id>
        self.track_id = track_uri.split(":")[-1]
        self.url = f"https://open.spotify.com/track/{self.track_id}"

        self.__soup = build_soup(self.url)

        self.name = self.__soup.find("meta", property = "og:title")["content"]
        self.artist = self.__soup.find("meta", attrs = {"name": "music:musician_description"})["content"]
        self.release_date = self.__soup.find("meta", attrs = {"name": "music:release_date"})["content"]


class Playlist:
    def __init__(self, playlist_uri: str):
        self.url = playlist_uri  # check with re for formatting issues

        self.__soup = build_soup(self.url)

        # Validating
        if not self.__is_public(self.__soup):
            raise spotapi.PlaylistError("Playlist not public")

        if not self.__is_valid_soup(self.__soup):
            self.__soup = self.__renew_soup_from_redirecturl(self.__soup)

        # Getting vars
        self.length = self.__get_playlist_length(self.__soup)

        pub_list_obj = PublicPlaylist(self.url)

        # Check if the playlist is small enough for a direct get_playlist_info method call
        if self.length > 343:
            self.items = []
            for page in pub_list_obj.paginate_playlist():
                self.items += page['items']
        else:
            rawdata = pub_list_obj.get_playlist_info(limit = self.length)

            if "errors" in rawdata:
                raise spotapi.PlaylistError(rawdata['errors'])

            self.items = rawdata['data']['playlistV2']['content']['items']

    @staticmethod
    def __is_public(soup: BeautifulSoup):

        if soup.find("title").text == 'Login - Spotify':
            return False

        return True

    @staticmethod
    def __is_valid_soup(soup: BeautifulSoup):
        """Validating method"""

        iframe_tag = soup.find('iframe', attrs = {"id": "urlSchemeIframeHandler"})

        if iframe_tag:
            style_attribute = iframe_tag['style']
            if style_attribute == "visibility: hidden":
                return False

        return True

    @staticmethod
    def __renew_soup_from_redirecturl(soup: BeautifulSoup):

        script_tag = soup.find('script', attrs = {"id": "urlSchemeConfig"})

        if script_tag:
            # Extract the script content
            script_content = script_tag.text.strip()

            data = json.loads(script_content)
            redirect_url = data.get("redirectUrl")

            return build_soup(redirect_url)
        else:
            raise Exception("Redirect url not found")

    @staticmethod
    def __get_playlist_length(soup: BeautifulSoup):
        result = soup.find("meta", attrs = {"name": "music:song_count"})
        if result:
            return int(result['content'])
        else:
            return None

    def get_items_uri(self):
        track_uris = []
        for item in self.items:
            item_uri = item['itemV2']['data']['uri']
            track_uris.append(item_uri)

        return track_uris
