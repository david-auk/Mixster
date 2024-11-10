import mysql.connector


class Database:
    _instance = None  # Class attribute to hold the single instance

    def __new__(cls, database, user, password, host='localhost'):
        if cls._instance is None or not cls._same_instance_params(cls._instance, database, user, password, host):
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialize(database, user, password, host)
        return cls._instance

    @classmethod
    def _same_instance_params(cls, instance, database, user, password, host):
        # Check if the existing instance has the same constructor values
        return (
                instance.database == database and
                instance.mysqlInterface._user == user and
                instance.mysqlInterface._password == password and
                instance.mysqlInterface._host == host
        )

    def _initialize(self, database, user, password, host):
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
