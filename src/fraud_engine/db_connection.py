import pyodbc


# ============================================================
# SQL SERVER CONNECTION CONFIGURATION
# ============================================================

SERVER = "localhost"

DATABASE = "PaySimFraudDB"

DRIVER = "ODBC Driver 18 for SQL Server"


# Windows Authentication
CONNECTION_STRING = (
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)


# ============================================================
# REUSABLE CONNECTION FUNCTION
# ============================================================

def get_connection(timeout=10):
    """
    Open and return a connection to PaySimFraudDB.
    """

    return pyodbc.connect(
        CONNECTION_STRING,
        timeout=timeout
    )


# ============================================================
# CONNECTION TEST
# ============================================================

def test_connection():

    connection = None

    try:
        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                @@SERVERNAME AS ServerName,
                DB_NAME() AS DatabaseName
        """)

        result = cursor.fetchone()

        print("SQL SERVER CONNECTION: SUCCESS")
        print("Server:", result[0])
        print("Database:", result[1])

        return True

    except pyodbc.Error as error:

        print("SQL SERVER CONNECTION: FAILED")
        print(error)

        raise

    finally:

        if connection is not None:
            connection.close()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    test_connection()
