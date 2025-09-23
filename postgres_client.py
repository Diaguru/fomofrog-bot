# postgres_client.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor

class PostgresClient:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        self.conn.autocommit = True

    def ensure_table(self):
        with self.conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id SERIAL PRIMARY KEY,
                txhash TEXT UNIQUE,
                buyer TEXT,
                amount NUMERIC,
                created_at TIMESTAMP DEFAULT NOW()
            )
            """)
        print("✅ purchases table ready")

    def insert_purchase(self, txhash, buyer, amount):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO purchases (txhash, buyer, amount) VALUES (%s, %s, %s) ON CONFLICT (txhash) DO NOTHING",
                (txhash, buyer, amount)
            )

    def top_buyers(self, limit=10):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT buyer, SUM(amount) as total FROM purchases GROUP BY buyer ORDER BY total DESC LIMIT %s",
                (limit,)
            )
            return cur.fetchall()
