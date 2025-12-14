import psycopg2
from psycopg2.extras import RealDictCursor, Json
import os
import uuid
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BrainDB:
    def __init__(self, db_name="brain_db", user=None):
        self.db_name = db_name
        self.user = user or os.environ.get("USER")
        self.conn = None

    def get_connection(self):
        if self.conn is None or self.conn.closed:
            try:
                self.conn = psycopg2.connect(
                    dbname=self.db_name,
                    user=self.user
                )
                self.conn.autocommit = True
            except Exception as e:
                logger.error(f"Failed to connect to DB: {e}")
                raise e
        return self.conn

    def close(self):
        if self.conn:
            self.conn.close()

    # --- Drops ---
    def insert_drop(self, type_, payload, note=None):
        conn = self.get_connection()
        drop_id = str(uuid.uuid4())
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO drops (id, type, payload, note, status)
                VALUES (%s, %s, %s, %s, 'pending')
                RETURNING id
                """,
                (drop_id, type_, payload, note)
            )
            return drop_id

    def get_pending_drops(self):
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM drops WHERE status = 'pending' ORDER BY created_at ASC")
            return cur.fetchall()

    def update_drop_status(self, drop_id, status, error_msg=None):
        conn = self.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE drops SET status = %s, error_msg = %s WHERE id = %s",
                (status, error_msg, drop_id)
            )

    # --- Artifacts ---
    def insert_artifact(self, drop_id, title, content, metadata):
        conn = self.get_connection()
        artifact_id = str(uuid.uuid4())
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO artifacts (id, drop_id, title, content, metadata)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (artifact_id, drop_id, title, content, Json(metadata))
            )
            return artifact_id

    def get_all_artifacts(self):
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM artifacts ORDER BY created_at DESC")
            return cur.fetchall()
            
    def get_artifact_count(self):
        conn = self.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM artifacts")
            return cur.fetchone()[0]

    # --- Embeddings ---
    def insert_embedding(self, artifact_id, vector, model):
        conn = self.get_connection()
        emb_id = str(uuid.uuid4())
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO embeddings (id, artifact_id, vector, model)
                VALUES (%s, %s, %s, %s)
                """,
                (emb_id, artifact_id, Json(vector), model)
            )
            return emb_id

    def get_all_embeddings(self):
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT e.vector, a.content, a.metadata, a.id as artifact_id 
                FROM embeddings e
                JOIN artifacts a ON e.artifact_id = a.id
            """)
            return cur.fetchall()

    # --- Stats & Dashboard ---
    def get_daily_stats(self, days=30):
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    TO_CHAR(created_at, 'YYYY-MM-DD') as date,
                    COUNT(*) as count
                FROM drops
                WHERE created_at >= NOW() - INTERVAL '%s days'
                GROUP BY date
                ORDER BY date ASC
            """, (days,))
            results = cur.fetchall()
            
            # Convert to dict for easy lookup
            data_map = {row['date']: row['count'] for row in results}
            
            # Generate full date range
            from datetime import timedelta
            stats = []
            for i in range(days):
                d = datetime.now() - timedelta(days=days-1-i)
                date_str = d.strftime('%Y-%m-%d')
                stats.append({
                    'date': date_str,
                    'count': data_map.get(date_str, 0)
                })
                
            return stats

    def get_recent_artifacts(self, limit=10):
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, title, content, metadata, created_at 
                FROM artifacts 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (limit,))
            return cur.fetchall()

    def get_random_artifacts(self, limit=5):
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, title, content, metadata, created_at 
                FROM artifacts 
                ORDER BY RANDOM() 
                LIMIT %s
            """, (limit,))
            return cur.fetchall()
