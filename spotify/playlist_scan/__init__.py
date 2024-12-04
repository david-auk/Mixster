from datetime import time
from urllib import parse

import requests
from bs4 import BeautifulSoup
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection
from spotapi import PublicPlaylist

from spotify import utilities

from spotify.playlist import Playlist, PlaylistDAO
from spotify.artist import Artist
from spotify.album import Album
from spotify.track import Track, TrackDAO
from spotify.user import User, UserDAO
from spotify import exceptions as exceptions

from .interfaces import Update


class PlaylistScan:
    def __init__(self, playlist: Playlist, requested_by_user: User, amount_of_tracks: int, export_completed: bool,
                 extends_playlist_scan: 'PlaylistScan' = None,
                 id: str = None, tracks: list[Track] = None, items: dict = None):

        self.id = id

        if playlist:
            self.playlist = playlist
        else:
            raise RuntimeError("Cant initialise without a valid playlist instance")

        if requested_by_user:
            self.requested_by_user = requested_by_user
        else:
            raise RuntimeError("Cant initialise without a valid requested_by_user instance")

        self.export_completed = export_completed
        self.amount_of_tracks = amount_of_tracks
        self.extends_playlist_scan = extends_playlist_scan

        if tracks:
            self.tracks = tracks
        else:
            self.tracks = []

        self.items = items

        # get items if tracks are not loaded yet
        if not self.tracks and not self.items:
            self.items = None
            self.items = self.get_items()

    @classmethod
    def build_from_api(cls, playlist_id: str, access_token: str, requested_by_user: User):

        def get_data(access_token, playlist_id, next=None):

            # Base URL for the Spotify Get Playlist endpoint
            url = f"https://api.spotify.com/v1/playlists/{playlist_id}"

            headers = {
                "Authorization": f"Bearer {access_token}"
            }

            if next:
                """
                Handle spotify next to give faulty params which now have to be extracted, modified and resent...
                """

                # Extract
                params = parse.parse_qs(parse.urlparse(next).query)
                url = next.split("?")[0]

                offset = params['offset'][0]
                limit = params['limit'][0]

                params = {
                    "fields": 'items(track(is_local,id,name,images,artists(name,id),album(id,name,release_date))),next',
                    "offset": offset,
                    "limit": limit
                }
            else:
                # Specify fields to fetch only the required data
                fields = (
                    # Playlist info
                    "id,name,images,tracks.total,"
                    # Track info
                    "tracks.items(track(is_local,id,name,images,artists(name,id),album(id,name,release_date))),"
                    # API logistics
                    "tracks.next"
                )
                params = {"fields": fields}

            # Make the API request
            response = requests.get(url, headers = headers, params = params)

            if response.status_code != 200:
                raise Exception(f"Spotify API error: {response.status_code} - {response.text}")

            return response.json()

        data = get_data(access_token, playlist_id)

        playlist = Playlist(
            id = data['id'],
            title = data['name'],
            cover_image_url = data['images'][0]['url']  # Check for better way to get the best image
        )

        amount_of_tracks = data['tracks']['total']

        tracks = []
        tracks_data = data['tracks']
        if tracks_data['next']:
            next_url = tracks_data['next']
        else:
            next_url = True  # So while loop runs once if there is no need for a second page
        while next_url:
            for item in tracks_data['items']:

                # Skip local files
                if item["track"]["is_local"]:
                    continue

                # Convert the artist data into instances
                artists = []
                for artist in item['track']['artists']:
                    artists.append(Artist(
                        artist_id = artist['id'],
                        name = artist['name']
                    ))

                # Convert the album data into an instance
                album = Album(
                    album_id = item['track']['album']['id'],
                    title = item['track']['album']['name'],
                    release_year = int(item['track']['album']['release_date'][:4])
                )

                # Convert all the data into one track instance
                tracks.append(Track(
                    track_id = item['track']['id'],
                    title = item['track']['name'],
                    album = album,
                    artists = artists
                ))
            next_url = tracks_data['next']
            if next_url:
                tracks_data = get_data(access_token, playlist_id, next = next_url)

        return cls(
            playlist = playlist,
            amount_of_tracks = amount_of_tracks,
            export_completed = False,
            tracks = tracks,
            requested_by_user = requested_by_user
        )

    @classmethod
    def build_from_url(cls, playlist_url: str, requested_by_user: User, extends_playlist_scan: 'PlaylistScan' = None):

        # Do linting/validation
        link_id = Playlist.lint_url(playlist_url)

        soup = utilities.build_soup(playlist_url)

        # Do linting/validation
        soup = Playlist.lint_soup(soup)

        return cls.build_from_soup(soup, link_id, requested_by_user, extends_playlist_scan)

    @classmethod
    def build_from_soup(cls, soup: BeautifulSoup, playlist_id: str, requested_by_user: User,
                        extends_playlist_scan: 'PlaylistScan' = None):

        song_count = soup.find("meta", attrs = {"name": "music:song_count"})
        if song_count and song_count.has_attr("content"):
            amount_of_tracks = int(song_count["content"])
        else:
            raise RuntimeError("Invalid soup, value of song_count not found")

        return cls(
            id = None,
            playlist = Playlist.build_from_soup(soup, playlist_id),
            requested_by_user = requested_by_user,
            amount_of_tracks = amount_of_tracks,
            scan_completed = False,
            extends_playlist_scan = extends_playlist_scan
        )

    @classmethod
    def build_from_attributes(cls, attributes: dict):
        return cls(
            id = attributes['id'],
            playlist = Playlist(**attributes['playlist']),
            requested_by_user = User(**attributes['requested_by_user']),
            amount_of_tracks = attributes['amount_of_tracks'],
            items = attributes['items'],
            scan_completed = attributes['export_completed'],
            extends_playlist_scan = cls.build_from_attributes(attributes['extends_playlist_scan']) if attributes[
                'extends_playlist_scan'] else None
        )

    def export_attributes(self):
        return {
            'id': self.id,
            'playlist': vars(self.playlist),
            'requested_by_user': vars(self.requested_by_user),
            'amount_of_tracks': self.amount_of_tracks,
            'items': self.items,
            'export_completed': self.export_completed,
            'extends_playlist_scan': self.extends_playlist_scan.export_attributes() if self.extends_playlist_scan else None
        }

    def get_items(self) -> dict:

        if self.items:
            return self.items

        pub_list_obj = PublicPlaylist(self.playlist.url)

        # Check if the playlist is small enough for a direct get_playlist_info method call
        if self.amount_of_tracks > 343:
            items = []

            # TODO investigate why this line doesnt work within celery.
            for page in pub_list_obj.paginate_playlist():
                items += page['items']
        else:
            rawdata = pub_list_obj.get_playlist_info(limit = self.amount_of_tracks)

            if "errors" in rawdata:
                raise exceptions.PlaylistException(rawdata['errors'])

            items = rawdata['data']['playlistV2']['content']['items']

        return items

    def get_tracks(self, track_dao: TrackDAO = None, update_obj: Update = None) -> list[Track]:

        items = self.get_items()

        # Todo add resume from last scanned track if interrupted

        for iteration, item in enumerate(items, 1):

            if update_obj and update_obj.remote_stop():
                break

            track_uri = item['itemV2']['data']['uri']

            # Get the track object
            track_id = track_uri.split(':')[-1]

            if track_dao:
                track = track_dao.get_instance(track_id)  # Try to get the track from saved info
                if not track:
                    album_uri: str = item['itemV2']['data']['albumOfTrack']['uri']
                    album_id = album_uri.split(":")[-1]
                    album = track_dao.album_dao.get_instance(album_id)  # Try to get the release date from DB
                    if album:
                        track_title = item['itemV2']['data']['name']
                        track = Track(track_id, track_title, album)
                    else:
                        track = Track.build_from_id(track_id)

                    track_dao.put_instance(track)  # Save info to DB
            else:
                track = Track.build_from_id(track_id)  # Allways scrape

            self.tracks.append(track)

            if update_obj:
                update_obj.get_analytics(iteration, len(items), track)
                update_obj.update()

        self.export_completed = True


class PlaylistScanDAO:
    def __init__(self, connection: PooledMySQLConnection | MySQLConnectionAbstract, playlist_dao: PlaylistDAO,
                 user_dao: UserDAO, track_dao: TrackDAO):
        """
        Initialize the DAO with a database connection and related DAOs.
        :param connection: A MySQL database connection object.
        :param playlist_dao: Instance of PlaylistDAO to handle playlist (data) related operations.
        :param user_dao: Instance of UserDAO to handle user-related operations.
        :param track_dao: Instance of TrackDAO to handle track-related operations.
        """
        self.connection = connection
        self.playlist_dao = playlist_dao
        self.user_dao = user_dao
        self.track_dao = track_dao

    def put_instance(self, playlist_scan: PlaylistScan) -> str | None:
        """
        Inserts or updates the data of a scan capturing playlist in the database.
        :param playlist_scan: A PlaylistScan object containing the playlist scan data.
        """
        try:
            cursor = self.connection.cursor()

            # Ensure the playlist exist, using the PlaylistDAO
            self.playlist_dao.put_instance(playlist_scan.playlist)

            # Ensure the user exist, using the UserDAO
            self.user_dao.put_instance(playlist_scan.requested_by_user)

            if playlist_scan.id:
                # Check if the playlist exists
                cursor.execute("SELECT id FROM playlist_scan WHERE id = %s", (playlist_scan.id,))
                existing_playlist_scan = cursor.fetchone()
            else:
                existing_playlist_scan = None

            if existing_playlist_scan:
                # Update the existing playlist
                update_query = ("UPDATE playlist_scan SET extends_playlist_scan = %s, playlist_id = %s, "
                                "requested_by_user_id = %s, amount_of_tracks = %s, export_completed = %s WHERE id = %s")
                cursor.execute(update_query, (
                    playlist_scan.extends_playlist_scan.id, playlist_scan.playlist.id,
                    playlist_scan.requested_by_user.id,
                    playlist_scan.amount_of_tracks, int(playlist_scan.export_completed),
                    playlist_scan.id))
            else:
                if playlist_scan.extends_playlist_scan:
                    # Insert the new playlist with additional extends_playlist_scan id value
                    insert_query = ("INSERT INTO playlist_scan (extends_playlist_scan, playlist_id, "
                                    "requested_by_user_id, amount_of_tracks, export_completed) VALUES (%s, %s, %s, %s, %s)")
                    cursor.execute(insert_query, (playlist_scan.extends_playlist_scan.id, playlist_scan.playlist.id,
                                                  playlist_scan.requested_by_user.id, playlist_scan.amount_of_tracks,
                                                  int(playlist_scan.export_completed)))
                else:
                    # Insert the new playlist
                    insert_query = (
                        "INSERT INTO playlist_scan (playlist_id, requested_by_user_id, amount_of_tracks, export_completed, extends_playlist_scan) "
                        "VALUES (%s, %s, %s, %s, %s)")
                    cursor.execute(insert_query, (
                        playlist_scan.playlist.id, playlist_scan.requested_by_user.id, playlist_scan.amount_of_tracks, int(playlist_scan.export_completed),
                        playlist_scan.extends_playlist_scan.id if playlist_scan.extends_playlist_scan else None)
                        )

            # Get the just created instance id
            playlist_scan.id = self.get_latest_id()

            # Ensure all the tracks exist, using TrackDAO
            if playlist_scan.tracks:

                # only get unique tracks
                for index, track in enumerate(playlist_scan.tracks):
                    self.track_dao.put_instance(track)

                    # Link the track to the scan
                    relationship_query = """
                    INSERT INTO playlist_scan_track (playlist_scan_id, track_playlist_scan_index, track_id)
                    VALUES (%s, %s, %s)
                    """
                    cursor.execute(relationship_query, (playlist_scan.id, index, track.id))

            # Commit the transaction
            self.connection.commit()

            # Return the most recently generated id (This instance's id)
            return playlist_scan.id

        except Exception as e:
            print(f"Error: {e}")
            self.connection.rollback()
        finally:
            cursor.close()

    def get_latest_id(self) -> str | None:
        try:
            cursor = self.connection.cursor(dictionary = True)

            # Fetch artist data
            query = """
            SELECT id
            FROM playlist_scan 
            ORDER BY timestamp DESC 
            LIMIT 1;
            """
            cursor.execute(query)
            playlist_scan_id = cursor.fetchone()

            if not playlist_scan_id:
                return None  # No scan created yet

            return playlist_scan_id['id']

        except Exception as e:
            print(f"Error fetching playlist_scan instance: {e}")
            return None
        finally:
            cursor.close()

    def get_instance(self, playlist_scan_id: str) -> PlaylistScan | None:
        """
        Retrieves an Artist instance by its ID from the database.
        :param playlist_scan_id: The ID of the playlist_scan to retrieve.
        :return: An PlaylistScan instance, or None if not found.
        """
        try:
            cursor = self.connection.cursor(dictionary = True)

            # Fetch artist data
            query = """
            SELECT id, playlist_id, extends_playlist_scan, requested_by_user_id, amount_of_tracks, export_completed
            FROM playlist_scan
            WHERE id = %s
            """
            cursor.execute(query, (playlist_scan_id,))
            playlist_scan_data = cursor.fetchone()

            if not playlist_scan_data:
                return None  # Track not found

            # Fetch associated tracks
            query = """
            SELECT t.id
            FROM track t
            INNER JOIN playlist_scan_track pst ON t.id = pst.track_id
            WHERE pst.playlist_scan_id = %s
            ORDER BY track_playlist_scan_index
            """
            cursor.execute(query, (playlist_scan_id,))
            tracks = cursor.fetchall()

            # Construct artists
            track_instances = [
                self.track_dao.get_instance(track_id = track["id"]) for track in tracks
            ]

            # Construct and return the Track instance
            return PlaylistScan(
                id = playlist_scan_id,
                playlist = self.playlist_dao.get_instance(playlist_scan_data["playlist_id"]),
                requested_by_user = self.user_dao.get_instance(playlist_scan_data["requested_by_user_id"]),
                amount_of_tracks = playlist_scan_data["amount_of_tracks"],
                export_completed = bool(playlist_scan_data["export_completed"]),
                tracks = track_instances,
                extends_playlist_scan = self.get_instance(playlist_scan_data[
                                                              "extends_playlist_scan"]) if "extends_playlist_scan" in playlist_scan_data else None,
            )

        except Exception as e:
            print(f"Error fetching user instance: {e}")
            return None
        finally:
            cursor.close()
