# postgres_client.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor

class PostgresClient:
    def __init__(self):
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise ValueError("DATABASE_URL is not set in environment variables")

        # Render 내부 Postgres는 SSL 필요
        self.conn = psycopg2.connect(db_url, sslmode="require")
        self.cursor = self.conn.cursor()

    def close(self):
        self.cursor.close()
        self.conn.close()

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
        self.conn.commit()
        print("✅ purchases table ready")

    def insert_purchase(self, txhash, buyer, amount):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO purchases (txhash, buyer, amount) VALUES (%s, %s, %s) ON CONFLICT (txhash) DO NOTHING",
                (txhash, buyer, amount)
            )
            self.conn.commit()

    def top_buyers(self, limit=10):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT buyer, SUM(amount) as total FROM purchases GROUP BY buyer ORDER BY total DESC LIMIT %s",
                (limit,)
            )
            return cur.fetchall()
