from datetime import time, datetime
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
    def __init__(self, playlist: Playlist, requested_by_user: User, export_completed: bool, created_at: datetime = None,
                 extends_playlist_scan: 'PlaylistScan' = None,
                 id: str = None, tracks: list[Track] = None):

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
        self.extends_playlist_scan = extends_playlist_scan

        if tracks:
            self.tracks = tracks
        else:
            self.tracks = []

        self.created_at = created_at

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
                    "fields": 'items(added_at,track(is_local,added_at,id,name,images,artists(name,id),album(id,name,release_date))),next',
                    "offset": offset,
                    "limit": limit
                }
            else:
                # Specify fields to fetch only the required data
                fields = (
                    # Playlist info
                    "id,name,images,"
                    # Track info
                    "tracks.items(added_at,track(is_local,id,name,images,artists(name,id),album(id,name,release_date))),"
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
                    artists = artists,
                    added_at = datetime.strptime(item['added_at'], "%Y-%m-%dT%H:%M:%SZ")
                ))
            next_url = tracks_data['next']
            if next_url:
                tracks_data = get_data(access_token, playlist_id, next = next_url)

        return cls(
            playlist = playlist,
            export_completed = False,
            tracks = tracks,
            requested_by_user = requested_by_user
        )

    def get_inherited_tracks(self) -> list[Track]:
        tracks = []

        if self.extends_playlist_scan:
            for track in self.extends_playlist_scan.get_inherited_tracks():
                tracks.append(track)

        return tracks



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
            cursor = self.connection.cursor(dictionary = True)

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

            to_return = None

            if existing_playlist_scan:

                # Update the existing playlist
                update_query = ("UPDATE playlist_scan SET extends_playlist_scan = %s, playlist_id = %s, "
                                "requested_by_user_id = %s, export_completed = %s WHERE id = %s")
                cursor.execute(update_query, (
                    playlist_scan.extends_playlist_scan.id if playlist_scan.extends_playlist_scan else None,
                    playlist_scan.playlist.id,
                    playlist_scan.requested_by_user.id, int(playlist_scan.export_completed),
                    playlist_scan.id))

                # Fetch current tracks
                cursor.execute("""
                    SELECT track_id 
                    FROM playlist_scan_track 
                    WHERE playlist_scan_id = %s
                """, (playlist_scan.id,))
                existing_tracks = set(row["track_id"] for row in cursor.fetchall())

                # Identify removed tracks
                new_tracks = set(track.id for track in playlist_scan.tracks)
                tracks_to_remove = existing_tracks - new_tracks

                # Remove obsolete tracks
                if tracks_to_remove:
                    cursor.executemany("""
                        DELETE FROM playlist_scan_track 
                        WHERE playlist_scan_id = %s AND track_id = %s
                    """, [(playlist_scan.id, track_id) for track_id in tracks_to_remove])

                # Insert new tracks
                for index, track in enumerate(playlist_scan.tracks):
                    if track.id not in existing_tracks:
                        self.track_dao.put_instance(track)
                        cursor.execute("""
                            INSERT INTO playlist_scan_track (playlist_scan_id, track_playlist_scan_index, track_id, track_added_at)
                            VALUES (%s, %s, %s, %s)
                        """, (playlist_scan.id, index, track.id, track.added_at))

            else:
                # Insert the new playlist
                insert_query = (
                    "INSERT INTO playlist_scan (playlist_id, requested_by_user_id, export_completed, extends_playlist_scan) "
                    "VALUES (%s, %s, %s, %s)")
                cursor.execute(insert_query, (
                    playlist_scan.playlist.id, playlist_scan.requested_by_user.id, int(playlist_scan.export_completed),
                    playlist_scan.extends_playlist_scan.id if playlist_scan.extends_playlist_scan else None)
                    )

                # Get the just created instance id
                playlist_scan.id = self.get_latest_id()

                # Ensure all the tracks exist, using TrackDAO
                if playlist_scan.tracks:

                    # only get unique tracks
                    for index, track in enumerate(playlist_scan.tracks):
                        self.track_dao.put_instance(track)

                        # Link the tracks to the scan
                        relationship_query = """
                        INSERT INTO playlist_scan_track (playlist_scan_id, track_playlist_scan_index, track_id, track_added_at)
                        VALUES (%s, %s, %s, %s)
                        """
                        cursor.execute(relationship_query, (playlist_scan.id, index, track.id, track.added_at))

            # Commit the transaction
            self.connection.commit()

            # Return the ID if the playlist_scan ID was just generated
            if not playlist_scan.id:
                to_return = self.get_latest_id()

            return to_return

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

    def get_attributes(self, playlist_scan_id: str, attributes: tuple) -> dict | None:
        try:
            cursor = self.connection.cursor(dictionary = True)
            # Fetch artist data
            query = f"""
            SELECT {", ".join(attributes)}
            FROM playlist_scan as ps
            JOIN mixster.playlist p on p.id = ps.playlist_id
            WHERE ps.id = %s
            """
            cursor.execute(query, (playlist_scan_id,))
            playlist_scan_data = cursor.fetchone()

            if not playlist_scan_data:
                return None  # Scan not found

            # Construct and return the Track instance
            return playlist_scan_data

        except Exception as e:
            print(f"Error fetching user instance: {e}")
            return None
        finally:
            cursor.close()

    def get_track_attributes(self, playlist_scan_id: str, attributes: tuple, newer_than: datetime = None) -> dict | None:
        try:
            cursor = self.connection.cursor(dictionary = True)
            # Fetch artist data
            query = f"""
            SELECT {", ".join(attributes)}
            FROM playlist_scan_track
            WHERE playlist_scan_id = %s
            {f"AND track_added_at > %s" if newer_than else ""}
            """

            params = [playlist_scan_id]
            if newer_than:
                params.append(newer_than)

            cursor.execute(query, tuple(params))
            playlist_scan_track_data = cursor.fetchone()

            if not playlist_scan_track_data:
                return None  # Scan not found

            # Construct and return the Track instance
            return playlist_scan_track_data

        except Exception as e:
            print(f"Error fetching user instance: {e}")
            return None
        finally:
            cursor.close()

    def get_instance(self, playlist_scan_id: str, tracks_only_unique: bool = False, tracks_newer_than: datetime = None) -> PlaylistScan | None:
        """
        Retrieves an Artist instance by its ID from the database.
        :param tracks_newer_than: The date the tracks to be initialized must be newer of
        :param tracks_only_unique:
        :param playlist_scan_id: The ID of the playlist_scan to retrieve.
        :return: An PlaylistScan instance, or None if not found.
        """
        try:
            cursor = self.connection.cursor(dictionary = True)

            # Fetch artist data
            query = """
            SELECT id, playlist_id, extends_playlist_scan, requested_by_user_id, export_completed, timestamp
            FROM playlist_scan
            WHERE id = %s
            """
            cursor.execute(query, (playlist_scan_id,))
            playlist_scan_data = cursor.fetchone()

            if not playlist_scan_data:
                return None  # Track not found

            # Fetch associated tracks
            query = f"""
            SELECT {'DISTINCT t.id' if tracks_only_unique else 't.id'}
            FROM track t
            INNER JOIN playlist_scan_track pst ON t.id = pst.track_id
            WHERE pst.playlist_scan_id = %s
            {f"AND pst.track_added_at > %s" if tracks_newer_than else ""}
            ORDER BY pst.track_playlist_scan_index
            """

            params = [playlist_scan_id]
            if tracks_newer_than:
                params.append(tracks_newer_than)

            cursor.execute(query, tuple(params))
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
                export_completed = bool(playlist_scan_data["export_completed"]),
                tracks = track_instances,
                extends_playlist_scan = self.get_instance(playlist_scan_data[
                                                              "extends_playlist_scan"], False) if "extends_playlist_scan" in playlist_scan_data else None,
                created_at = playlist_scan_data["timestamp"]
            )

        except Exception as e:
            print(f"Error fetching user instance: {e}")
            return None
        finally:
            cursor.close()
