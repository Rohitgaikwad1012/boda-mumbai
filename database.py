import mysql.connector
import streamlit as st
import config


# Why there is no connection pool any more:
# A pooled connection can be silently dropped by the network while it sits
# idle (Aiven, Wi-Fi, laptop sleep). Pinging it, or returning it to the pool
# (which resets the session), then waits on a dead socket with no timeout.
# That wait is the "page is faded and stuck, cards never come" problem.
# A short-lived connection per query cannot go stale, and connection_timeout
# makes a bad connect fail fast instead of hanging.
_DB_CONFIG = dict(
    host=config.MYSQL_HOST,
    port=config.MYSQL_PORT,
    user=config.MYSQL_USER,
    password=config.MYSQL_PASSWORD,
    database=config.MYSQL_DATABASE,
    connection_timeout=10,
)

# Also stop a query from waiting forever on a dead socket. Older versions of
# the connector do not know these two options, so we fall back without them.
_IO_TIMEOUTS = dict(read_timeout=20, write_timeout=20)


def _safe_close(obj):
    """Close a cursor/connection without letting a dead socket raise."""
    if obj is None:
        return
    try:
        obj.close()
    except Exception:
        pass


def get_connection():
    """Open a fresh MySQL connection (fails within about 10 seconds)."""
    try:
        return mysql.connector.connect(**_DB_CONFIG, **_IO_TIMEOUTS)
    except AttributeError:
        # This connector version does not support read/write timeouts.
        return mysql.connector.connect(**_DB_CONFIG)


def execute_query(query, params=(), fetch=False):
    """Run one SQL query and always close the connection afterwards.

    If it fails, try once more on a new connection. Reads are safe to
    repeat. A write is only retried if it failed before anything was sent,
    so it can never be saved twice. Returns None if both tries fail.
    """

    for attempt in (1, 2):
        conn = None
        cursor = None
        sent = False

        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)

            sent = True
            cursor.execute(query, params)

            if fetch:
                return cursor.fetchall()

            conn.commit()
            return cursor.lastrowid

        except (mysql.connector.Error, OSError) as e:
            print(f"Database Exception (attempt {attempt}): {e}")
            if attempt == 2 or (sent and not fetch):
                return None

        finally:
            _safe_close(cursor)
            _safe_close(conn)

    return None


@st.cache_data(ttl=300, show_spinner=False)
def _find_places_cached(category, area):
    clauses = []
    values = []

    if category:
        clauses.append("category = %s")
        values.append(category)

    if area:
        clauses.append("TRIM(area) = %s")
        values.append(area)

    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""

    rows = execute_query(
        f"SELECT * FROM places{where} LIMIT 24",
        tuple(values),
        fetch=True
    )
    if rows is None:
        # Raising means Streamlit does NOT cache the failure, so the next
        # click or refresh tries the database again.
        raise RuntimeError("database unavailable")
    return rows


def find_places(category=None, area=None):
    """Fetch places filtered by category or area.

    Good results are cached for 5 minutes, so switching moods is instant and
    the database is hit much less. Returns None if the database is down.
    """
    try:
        return _find_places_cached(category, area)
    except RuntimeError:
        return None


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