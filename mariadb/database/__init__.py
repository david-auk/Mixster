import mysql.connector


class Database:
    def __init__(self, database, user, password, host='localhost'):
        self.database = database

        self.mysqlInterface = mysql.connector.connect(
            database = self.database,
            user = user,
            password = password,
            host = host,
            converter_class = mysql.connector.conversion.MySQLConverter
        )

    @staticmethod
    def escape_sql_string(s):
        return s.replace("'", "''")

    def disconnect(self):
        self.mysqlInterface.disconnect()

    def run(self, statement):
        if not self.mysqlInterface.is_connected():
            self.mysqlInterface.reconnect()

        with self.mysqlInterface.cursor(buffered = True) as cursor:
            cursor.execute(statement)

            try:
                return cursor.fetchall()

            except:
                self.mysqlInterface.commit()
                return None