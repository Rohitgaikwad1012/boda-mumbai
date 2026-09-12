import mysql.connector
from mysql.connector import pooling
import config


# MySQL connection pool
try:
    db_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="bodapool",
        pool_size=10,
        pool_reset_session=True,
        host=config.MYSQL_HOST,
        port=config.MYSQL_PORT,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        database=config.MYSQL_DATABASE
    )
except mysql.connector.Error as err:
    print(f"Error creating connection pool: {err}")
    db_pool = None


def get_connection():
    """Get a MySQL connection from the pool."""
    if db_pool:
        return db_pool.get_connection()

    return mysql.connector.connect(
        host=config.MYSQL_HOST,
        port=config.MYSQL_PORT,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        database=config.MYSQL_DATABASE
    )


def execute_query(query, params=(), fetch=False):
    """Execute SQL query safely and always return the connection to the pool."""

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(query, params)

        if fetch:
            return cursor.fetchall()

        conn.commit()
        return cursor.lastrowid

    except mysql.connector.Error as e:
        print(f"Database Exception: {e}")
        return None

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


def find_places(category=None, area=None):
    """Fetch places filtered by category or area."""

    clauses = []
    values = []

    if category:
        clauses.append("category = %s")
        values.append(category)

    if area:
        clauses.append("TRIM(area) = %s")
        values.append(area)

    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""

    return execute_query(
        f"SELECT * FROM places{where} LIMIT 24",
        tuple(values),
        fetch=True
    )


def create_preference(name, area, budget, mood, group_type, duration):
    """Save user session preferences to MySQL."""

    query = """
        INSERT INTO user_preferences
        (name, area, budget, mood, group_type, duration)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    return execute_query(
        query,
        (name, area, budget, mood, group_type, duration)
    )