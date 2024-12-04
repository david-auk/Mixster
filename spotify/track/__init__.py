import datetime

from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection

import spotify.utilities as utilities
from spotify.album import Album, AlbumDAO
from spotify.artist import Artist, ArtistDAO
from typing_extensions import Self


class Track:

    @classmethod
    def build_from_id(cls, track_id: str, pull_tries: int = 5) -> Self:
        url = f"https://open.spotify.com/track/{track_id}"
        soup = None
        for attempt in range(pull_tries):
            attempt += 1
            try:
                soup = utilities.build_soup(url)
                break
            except Exception as e:
                if str(e) != "Failed to retrieve track page":
                    raise Exception(e)
                else:
                    if attempt == pull_tries:
                        raise Exception(e)

        # Getting artists data
        artists_id = []
        for artist_url in soup.findAll("meta", attrs = {"name": "music:musician"}):
            artist_id = artist_url["content"].split("/")[-1]
            artists_id.append(artist_id)

        artists_name = soup.find("meta", attrs = {"name": "music:musician_description"})["content"].split(", ")

        artists = [Artist(artist_id, artist_name) for artist_id, artist_name in zip(artists_id, artists_name)]

        # Getting album data
        album_url = soup.find("meta", attrs = {"name": "music:album"})["content"]
        album_id = album_url.split("/")[-1]
        release_date = soup.find("meta", attrs = {"name": "music:release_date"})["content"]
        release_date = datetime.datetime.strptime(release_date, "%Y-%m-%d")
        album = Album(album_id, release_date, artists)

        track_title = soup.find("meta", property = "og:title")["content"]

        return cls(track_id, track_title, album)

    def __init__(self, track_id: str, title: str, album: Album, artists: list[Artist]):
        self.id = track_id
        self.url = f"https://open.spotify.com/track/{self.id}"
        self.title = title
        self.album = album
        self.artists = artists

    def get_artist_name(self) -> str:
        artist_names = []
        for artist in self.artists:
            artist_names.append(artist.name)
        return ", ".join(artist_names)

    def __repr__(self):
        return f"<Track(id={self.id}, title={self.title}, album={self.album}, artists={self.get_artist_name()})>"


class TrackDAO:

    def __init__(self, connection: PooledMySQLConnection | MySQLConnectionAbstract, album_dao: AlbumDAO, artist_dao: ArtistDAO):
        """
        Initialize the DAO with a database connection and related DAOs.
        :param connection: A MySQL database connection object.
        :param album_dao: Instance of AlbumDAO to handle album-related operations.
        """
        self.artist_dao = artist_dao
        self.connection = connection
        self.album_dao = album_dao

    def put_instance(self, track: Track):
        """
        Inserts or updates a track and its related album/artist in the database.
        :param track: A Track object containing the track data.
        """
        try:
            cursor = self.connection.cursor()

            # Ensure the album and artist exist, using the AlbumDAO
            self.album_dao.put_instance(track.album)

            # Check if the track already exists
            cursor.execute("SELECT id FROM track WHERE id = %s", (track.id,))
            existing_track = cursor.fetchone()

            if not existing_track:
                # Insert the new track
                insert_query = """
                INSERT INTO track (id, title, album_id)
                VALUES (%s, %s, %s)
                """
                cursor.execute(insert_query, (track.id, track.title, track.album.id))

                for artist in track.artists:
                    # Make sure the artist exists
                    self.artist_dao.put_instance(artist)

                    # Link the artist to the album
                    relationship_query = """
                    INSERT INTO artist_track (artist_id, track_id)
                    VALUES (%s, %s)
                    """
                    cursor.execute(relationship_query, (artist.id, track.id))

            # Commit the transaction
            self.connection.commit()

        except Exception as e:
            print(f"Error: {e}")
            self.connection.rollback()
        finally:
            cursor.close()

    def get_instance(self, track_id: str) -> Track | None:
        """
        Retrieves a Track instance by its ID from the database.
        :param track_id: The ID of the track to retrieve.
        :return: A Track instance, or None if not found.
        """
        try:
            cursor = self.connection.cursor(dictionary = True)

            # Fetch album data
            query = """
            SELECT id, title, album_id
            FROM track
            WHERE id = %s
            """
            cursor.execute(query, (track_id,))
            track_data = cursor.fetchone()

            if not track_data:
                return None  # Track not found

            # Fetch associated artists
            query = """
            SELECT ar.id, ar.name
            FROM artist ar
            INNER JOIN artist_track at ON ar.id = at.artist_id
            WHERE at.track_id = %s
            """
            cursor.execute(query, (track_id,))
            artists = cursor.fetchall()

            # Construct artists
            artist_instances = [
                Artist(
                    artist_id = artist["id"],
                    name = artist["name"]
                ) for artist in artists
            ]

            # Construct and return the Track instance
            return Track(
                track_id = track_data["id"],
                title = track_data["title"],
                album = self.album_dao.get_instance(track_data["album_id"]),
                artists = artist_instances
            )

        except Exception as e:
            print(f"Error fetching album instance: {e}")
            return None
        finally:
            cursor.close()
