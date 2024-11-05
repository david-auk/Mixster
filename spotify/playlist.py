import json

from . import utilities
from spotapi import PublicPlaylist, PlaylistError

class Playlist:
    def __init__(self, playlist_uri: str):
        self.url = playlist_uri  # check with re for formatting issues

        self.__soup = utilities.build_soup(self.url)

        # Validating
        if not self.__is_public(self.__soup):
            raise PlaylistError("Playlist not public")

        if not self.__is_valid_soup(self.__soup):
            self.__soup = self.__renew_soup_from_redirecturl(self.__soup)

        # Getting vars
        self.length = self.__get_playlist_length(self.__soup)
        self.title = self.__soup.find("meta", property = "og:title")["content"]
        self.image_url = self.__soup.find("meta", property = "og:image")["content"]

        pub_list_obj = PublicPlaylist(self.url)

        # Check if the playlist is small enough for a direct get_playlist_info method call
        if self.length > 343:
            self.items = []
            for page in pub_list_obj.paginate_playlist():
                self.items += page['items']
        else:
            rawdata = pub_list_obj.get_playlist_info(limit = self.length)

            if "errors" in rawdata:
                raise PlaylistError(rawdata['errors'])

            self.items = rawdata['data']['playlistV2']['content']['items']

    @staticmethod
    def __is_public(soup: utilities.BeautifulSoup):

        if soup.find("title").text == 'Login - Spotify':
            return False

        return True

    @staticmethod
    def __is_valid_soup(soup: utilities.BeautifulSoup):
        """Validating method"""

        iframe_tag = soup.find('iframe', attrs = {"id": "urlSchemeIframeHandler"})

        if iframe_tag:
            style_attribute = iframe_tag['style']
            if style_attribute == "visibility: hidden":
                return False

        return True

    @staticmethod
    def __renew_soup_from_redirecturl(soup: utilities.BeautifulSoup):

        script_tag = soup.find('script', attrs = {"id": "urlSchemeConfig"})

        if script_tag:
            # Extract the script content
            script_content = script_tag.text.strip()

            data = json.loads(script_content)
            redirect_url = data.get("redirectUrl")

            return utilities.build_soup(redirect_url)
        else:
            raise Exception("Redirect url not found")

    @staticmethod
    def __get_playlist_length(soup: utilities.BeautifulSoup):
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