from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection


class Artist:
    def __init__(self, artist_id: str, name: str):
        self.id = artist_id
        self.name = name

    def __repr__(self):
        return f"<Artist(id={self.id}, name={self.name})>"


class ArtistDAO:
    def __init__(self, connection: PooledMySQLConnection | MySQLConnectionAbstract):
        """
        Initialize the DAO with a database connection
        """
        self.connection = connection

    def put_instance(self, artist: Artist):
        """
        Inserts or updates an artist in the database.
        :param artist: An Artist object containing the artist data.
        """
        try:
            cursor = self.connection.cursor()

            # Check if the artist exists
            cursor.execute("SELECT id FROM artist WHERE id = %s", (artist.id,))
            existing_artist = cursor.fetchone()

            if existing_artist:
                # Update the existing artist
                update_query = "UPDATE artist SET name = %s WHERE id = %s"
                cursor.execute(update_query, (artist.name, artist.id))
            else:
                # Insert the new artist
                insert_query = "INSERT INTO artist (id, name) VALUES (%s, %s)"
                cursor.execute(insert_query, (artist.id, artist.name))

            # Commit the transaction
            self.connection.commit()

        except Exception as e:
            print(f"Error: {e}")
            self.connection.rollback()
        finally:
            cursor.close()

    def get_instance(self, artist_id: str) -> Artist | None:
        """
        Retrieves an Artist instance by its ID from the database.
        :param artist_id: The ID of the artist to retrieve.
        :return: An Artist instance, or None if not found.
        """
        try:
            cursor = self.connection.cursor(dictionary = True)

            # Fetch artist data
            query = """
            SELECT id, name
            FROM artist
            WHERE id = %s
            """
            cursor.execute(query, (artist_id,))
            artist_data = cursor.fetchone()

            if not artist_data:
                return None  # Artist not found

            # Construct and return the Artist instance
            return Artist(
                artist_id = artist_data["id"],
                name = artist_data["name"]
            )

        except Exception as e:
            print(f"Error fetching artist instance: {e}")
            return None
        finally:
            cursor.close()
