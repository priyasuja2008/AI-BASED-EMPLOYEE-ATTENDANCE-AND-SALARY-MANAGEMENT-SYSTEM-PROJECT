import mysql.connector

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Priya123@",
            database="attendance_system"
        )

        if connection.is_connected():
            print("✅ Connected to MySQL Database")

        return connection

    except mysql.connector.Error as err:
        print("❌ Database Connection Error:", err)
        return None