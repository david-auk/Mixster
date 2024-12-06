from time import time

from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection
from spotify.artist import Artist, ArtistDAO


class Album:
    def __init__(self, album_id: str, title: str, release_year: int):
        self.id = album_id
        self.title = title
        self.release_year = release_year

    def __repr__(self):
        return f"<Album(id={self.id}, title={self.title}, release_year={self.release_year})>"

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
                INSERT INTO album (id, title, release_year)
                VALUES (%s, %s, %s)
                """
                cursor.execute(insert_query, (album.id, album.title, album.release_year))

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
            SELECT id, title, release_year
            FROM album
            WHERE id = %s
            """
            cursor.execute(query, (album_id,))
            album_data = cursor.fetchone()

            if not album_data:
                return None  # Album not found

            # Construct and return the Album instance
            return Album(
                album_id = album_data["id"],
                title = album_data["title"],
                release_year = album_data["release_year"]
            )

        except Exception as e:
            print(f"Error fetching album instance: {e}")
            return None
        finally:
            cursor.close()