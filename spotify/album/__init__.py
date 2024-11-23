from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection
from spotify.artist import Artist, ArtistDAO


class Album:
    def __init__(self, album_id: str, release_date: str, artists: list[Artist]):
        self.id = album_id
        self.release_date = release_date
        self.artists = artists

    def get_artist_name(self) -> str:
        artist_names = []
        for artist in self.artists:
            artist_names.append(artist.name)
        return ", ".join(artist_names)

    def __repr__(self):
        return f"<Artist(id={self.id}, name={self.release_date}, artists={self.artists})>"

class AlbumDAO:
    def __init__(self, connection: PooledMySQLConnection | MySQLConnectionAbstract, artist_dao: ArtistDAO):
        self.connection = connection
        self.artist_dao = artist_dao

    def put_instance(self, album: Album):
        """
        Inserts or updates an album and its related artist in the database.
        :param album: An Album object containing the album data.
        """
        try:
            cursor = self.connection.cursor()

            # Ensure the artist exists, using the ArtistDAO
            self.artist_dao.put_artist(album.artist)

            # Check if the album exists
            cursor.execute("SELECT id FROM album WHERE id = %s", (album.id,))
            existing_album = cursor.fetchone()

            if existing_album:
                # Update the existing album
                update_query = """
                UPDATE album
                SET title = %s, release_date = %s, artist_id = %s
                WHERE id = %s
                """
                cursor.execute(update_query, (album.title, album.release_date, album.artist.id, album.id))
            else:
                # Insert the new album
                insert_query = """
                INSERT INTO album (id, title, release_date, artist_id)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(insert_query, (album.id, album.title, album.release_date, album.artist.id))

            # Commit the transaction
            self.connection.commit()

        except Exception as e:
            print(f"Error: {e}")
            self.connection.rollback()
        finally:
            cursor.close()

    def get_instance(self, album_id: str) -> Album:
        """
        Retrieves an Album instance by its ID from the database.
        :param album_id: The ID of the album to retrieve.
        :return: An Album instance, or None if not found.
        """
        try:
            cursor = self.connection.cursor(dictionary = True)

            # Fetch album data
            query = """
            SELECT id, title, release_date, artist_id
            FROM album
            WHERE id = %s
            """
            cursor.execute(query, (album_id,))
            album_data = cursor.fetchone()

            if not album_data:
                return None  # Album not found

            # Fetch the associated artist instance
            artist = self.artist_dao.get_instance(album_data["artist_id"])

            # Construct and return the Album instance
            return Album(
                album_id = album_data["id"],
                title = album_data["title"],
                release_date = album_data["release_date"],
                artist = artist
            )

        except Exception as e:
            print(f"Error fetching album instance: {e}")
            return None
        finally:
            cursor.close()