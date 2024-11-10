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

        # (dirty) Fix INSERT None to NULL translation (to be itterated)
        # if statement.upper().startswith('INSERT'):

        #	statement = re.sub(r'\(None\b', '(NULL', statement) # Replace with null value if begins with
        #	statement = re.sub(r',\s*None\b', ', NULL', statement) # Replace with null value if anywhere else

        with self.mysqlInterface.cursor(buffered = True) as cursor:
            cursor.execute(statement)

            try:
                return cursor.fetchall()

            except:
                self.mysqlInterface.commit()
                return None