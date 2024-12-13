import json
import requests

from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection

import spotify.utilities as utilities
from spotify.exceptions import URLError, PlaylistException
from bs4 import BeautifulSoup


class Playlist:
    def __init__(self, id: str, title: str, cover_image_url, url: str = None):
        self.id = id
        self.url = url if url else f"https://open.spotify.com/playlist/{self.id}"
        self.title = title
        self.cover_image_url = cover_image_url

    @classmethod
    def build_from_url(cls, playlist_url: str):

        # Validating
        playlist_id = cls.lint_url(playlist_url)

        soup = utilities.build_soup(playlist_url)
        return cls.build_from_soup(soup, playlist_id)

    @classmethod
    def build_from_soup(cls, soup: BeautifulSoup, playlist_id: str):

        soup = cls.lint_soup(soup)

        # Getting vars
        title_dict = soup.find("meta", property = "og:title")
        if title_dict and title_dict.has_attr("content"):
            title = title_dict["content"]
        else:
            raise RuntimeError("Invalid soup, value of title not found")

        image_dict = soup.find("meta", property = "og:image")
        if image_dict and image_dict.has_attr("content"):
            cover_image_url = image_dict["content"]
        else:
            raise RuntimeError("Invalid soup, value of image not found")

        return cls(
            id = playlist_id,
            title = title,
            cover_image_url = cover_image_url
        )

    @staticmethod
    def lint_url(playlist_url: str) -> str:

        link_type, link_id = utilities.extract_spotify_type_id(playlist_url)

        if link_type != "playlist":
            raise URLError(f"Invalid Spotify URL, expected 'playlist' but got '{link_type}'")

        return link_id

    @staticmethod
    def lint_soup(soup: BeautifulSoup) -> BeautifulSoup:

        # Validating
        if not Playlist.__is_public(soup):
            raise PlaylistException("Playlist not public")

        # If the web gui had redirected, get new soup from that new uri
        if not Playlist.__is_valid_soup(soup):
            soup = Playlist.__renew_soup_from_redirecturl(soup)

        return soup

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

    def export_attributes(self):
        return {
            'id': self.id,
            'url': self.url,
            'cover_image_url': self.cover_image_url,
            'title': self.title
        }


class PlaylistDAO:
    def __init__(self, connection: PooledMySQLConnection | MySQLConnectionAbstract):
        """
        Initialize the DAO with a database connection
        """
        self.connection = connection

    def put_instance(self, playlist: Playlist):
        """
        Inserts or updates a playlist in the database.
        :param playlist: A Playlist object containing the playlist data.
        """
        try:
            cursor = self.connection.cursor()

            # Check if the playlist exists
            cursor.execute("SELECT id FROM playlist WHERE id = %s", (playlist.id,))
            existing_playlist = cursor.fetchone()

            if existing_playlist:
                # Update the existing playlist
                update_query = "UPDATE playlist SET title = %s, cover_image_url = %s WHERE id = %s"
                cursor.execute(update_query, (playlist.title, playlist.cover_image_url, playlist.id))
            else:
                # Insert the new playlist
                insert_query = "INSERT INTO playlist (id, title, cover_image_url) VALUES (%s, %s, %s)"
                cursor.execute(insert_query, (playlist.id, playlist.title, playlist.cover_image_url))

            # Commit the transaction
            self.connection.commit()

        except Exception as e:
            print(f"Error: {e}")
            self.connection.rollback()
        finally:
            cursor.close()

    def get_instance(self, playlist_id: str) -> Playlist | None:
        """
        Retrieves a Playlist instance by its ID from the database.
        :param playlist_id: The ID of the playlist to retrieve.
        :return: A Playlist instance, or None if not found.
        """
        try:
            cursor = self.connection.cursor(dictionary = True)

            # Fetch artist data
            query = """
            SELECT id, title, cover_image_url
            FROM playlist
            WHERE id = %s
            """
            cursor.execute(query, (playlist_id,))
            playlist_data = cursor.fetchone()

            if not playlist_data:
                return None  # Artist not found

            # Construct and return the Artist instance
            return Playlist(
                id = playlist_data["id"],
                title = playlist_data["title"],
                cover_image_url = playlist_data["cover_image_url"]
            )

        except Exception as e:
            print(f"Error fetching user instance: {e}")
            return None
        finally:
            cursor.close()

    def get_instance_from_scan(self, playlist_scan_id: str) -> Playlist | None:
        try:
            cursor = self.connection.cursor(dictionary = True)

            # Fetch artist data
            query = """
            SELECT playlist_id
            FROM playlist_scan
            WHERE id = %s
            """
            cursor.execute(query, (playlist_scan_id,))
            playlist_scan_data = cursor.fetchone()

            if not playlist_scan_data:
                return None  # Scan not found

            return self.get_instance(playlist_scan_data['playlist_id'])

        except Exception as e:
            print(f"Error fetching user instance: {e}")
            return None
        finally:
            cursor.close()