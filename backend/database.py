"""
Database connection management with connection pooling.
Using ConnectionPool to reuse connections across requests.
"""
import os
from contextlib import contextmanager
import psycopg
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv

load_dotenv()

# Create connection pool on module import (happens once at startup)
# Min 1 connection, max 10 connections
connection_pool = ConnectionPool(
    os.getenv("DATABASE_URL"),
    min_size=1,
    max_size=10
)


@contextmanager
def get_db_connection():
    """
    Context manager for database connections.
    Automatically returns connection to pool after use.
    
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ...")
    """
    conn = connection_pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        connection_pool.putconn(conn)


def get_document_list():
    """Get list of all uploaded documents with chunk counts"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT filename, COUNT(*) as chunk_count
            FROM documents
            GROUP BY filename
            ORDER BY filename
        """)
        rows = cursor.fetchall()
        return [{"filename": r[0], "chunk_count": r[1]} for r in rows]


def delete_document(filename: str):
    """Delete all chunks for a given document"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents WHERE filename = %s", (filename,))
        deleted_count = cursor.rowcount
        return deleted_count