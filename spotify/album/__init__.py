from time import time

from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection
from spotify.artist import Artist, ArtistDAO


class Album:
    def __init__(self, album_id: str, title: str, release_date: time):
        self.id = album_id
        self.title = title
        self.release_date = release_date

    def __repr__(self):
        return f"<Album(id={self.id}, title={self.title}, release_date={self.release_date})>"

class AlbumDAO:
    def __init__(self, connection: PooledMySQLConnection | MySQLConnectionAbstract, artist_dao: ArtistDAO):
        """
        Initialize the DAO with a database connection and related dao's
        :param artist_dao Instance of ArtistDAO to handle artist (data) related operations
        """
        self.connection = connection
        self.artist_dao = artist_dao

    def put_instance(self, album: Album):
        """
        Inserts or updates an Album and its related album in the database.
        :param album: An Album object containing the album data.
        """
        try:
            cursor = self.connection.cursor()

            # Check if the album exists
            cursor.execute("SELECT id FROM album WHERE id = %s", (album.id,))
            existing_album = cursor.fetchone()

            # No "update" functionality because the only thing that can be updated is the release date,
            # which is not logical
            if not existing_album:
                # Insert the new album
                insert_query = """
                INSERT INTO album (id, release_date)
                VALUES (%s, %s)
                """
                cursor.execute(insert_query, (album.id, album.release_date))

                for artist in album.artists:

                    # Make sure the artist exists
                    self.artist_dao.put_instance(artist)

                    # Link the artist to the album
                    relationship_query = """
                    INSERT INTO artist_album (artist_id, album_id)
                    VALUES (%s, %s)
                    """
                    cursor.execute(relationship_query, (artist.id, album.id))

            # Commit the transaction
            self.connection.commit()

        except Exception as e:
            print(f"Error: {e}")
            self.connection.rollback()
        finally:
            cursor.close()

    def get_instance(self, album_id: str) -> Album | None:
        """
        Retrieves an Album instance by its ID from the database.
        :param album_id: The ID of the album to retrieve.
        :return: An Album instance, or None if not found.
        """
        try:
            cursor = self.connection.cursor(dictionary = True)

            # Fetch album data
            query = """
            SELECT id, release_date
            FROM album
            WHERE id = %s
            """
            cursor.execute(query, (album_id,))
            album_data = cursor.fetchone()

            if not album_data:
                return None  # Album not found

            # Fetch associated artists
            query = """
                    SELECT ar.id, ar.name
                    FROM artist ar
                    INNER JOIN artist_album aa ON ar.id = aa.artist_id
                    WHERE aa.album_id = %s
                    """
            cursor.execute(query, (album_id,))
            artists = cursor.fetchall()

            # Construct artists
            artist_instances = [
                Artist(
                    artist_id = artist["id"],
                    name = artist["name"]
                ) for artist in artists
            ]

            # Construct and return the Album instance
            album = Album(
                album_id = album_data["id"],
                release_date = album_data["release_date"],
                artists = artist_instances  # Updated to handle multiple artists
            )
            return album

        except Exception as e:
            print(f"Error fetching album instance: {e}")
            return None
        finally:
            cursor.close()