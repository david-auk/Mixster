import time

from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection

from datetime import datetime


class User:
    def __init__(self, id: str, name: str, profile_picture_image_url: str | None, last_login: datetime, registry_date: datetime):
        self.id = id
        self.name = name
        self.profile_picture_image_url = profile_picture_image_url
        self.last_login = last_login
        self.registry_date = registry_date

    def __repr__(self):
        return (f"<User(id={self.id}, name={self.name}, profile_picture_image_url={self.profile_picture_image_url}, "
                f"last_used={self.last_login}, registry_date={self.registry_date})>")


class UserDAO:
    def __init__(self, connection: PooledMySQLConnection | MySQLConnectionAbstract):
        self.connection = connection

    def update_last_login(self, user: User):
        try:
            cursor = self.connection.cursor()

            # Check if the artist exists
            cursor.execute("SELECT id FROM user WHERE id = %s", (user.id,))
            existing_user = cursor.fetchone()

            if existing_user:
                update_query = "UPDATE user SET last_login = %s WHERE id = %s"
                cursor.execute(update_query, (datetime.now(), user.id))  # Todo update timezone
            else:
                raise RuntimeError("User entry not found")

        except Exception as e:
            print(f"Error: {e}")
            self.connection.rollback()
        finally:
            cursor.close()

    def put_instance(self, user: User):
        """
        Inserts or updates a user in the database.
        :param user: A User object containing the user data.
        """
        try:
            cursor = self.connection.cursor()

            # Check if the artist exists
            cursor.execute("SELECT id FROM user WHERE id = %s", (user.id,))
            existing_user = cursor.fetchone()

            if existing_user:
                # Update the existing artist
                update_query = "UPDATE user SET name = %s, profile_picture_image_url = %s WHERE id = %s"
                cursor.execute(update_query, (user.name, user.profile_picture_image_url, user.last_login, user.id))
            else:
                # Insert the new artist
                insert_query = "INSERT INTO user (id, name, profile_picture_image_url) VALUES (%s, %s, %s)"
                cursor.execute(insert_query, (user.id, user.name, user.profile_picture_image_url))

            # Commit the transaction
            self.connection.commit()

        except Exception as e:
            print(f"Error: {e}")
            self.connection.rollback()
        finally:
            cursor.close()

    def get_instance(self, user_id: str) -> User | None:
        """
        Retrieves an Artist instance by its ID from the database.
        :param user_id: The ID of the user to retrieve.
        :return: An Artist instance, or None if not found.
        """
        try:
            cursor = self.connection.cursor(dictionary = True)

            # Fetch artist data
            query = """
            SELECT id, name, profile_picture_image_url, last_login, registry_date
            FROM user
            WHERE id = %s
            """
            cursor.execute(query, (user_id,))
            user_data = cursor.fetchone()

            if not user_data:
                return None  # Artist not found

            # Construct and return the Artist instance
            return User(
                id = user_data["id"],
                name = user_data["name"],
                profile_picture_image_url = user_data["profile_picture_image_url"],
                last_login = user_data["last_login"],
                registry_date = user_data["registry_date"]
            )

        except Exception as e:
            print(f"Error fetching user instance: {e}")
            return None
        finally:
            cursor.close()
