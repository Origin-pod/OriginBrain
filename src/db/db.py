import psycopg2
from psycopg2.extras import RealDictCursor, Json
import os
import uuid
import json
import logging
from datetime import datetime, timedelta

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

    # --- Search Support Methods ---
    def get_artifacts_for_indexing(self, limit: int = None) -> list:
        """Get artifacts with embeddings for search indexing."""
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT a.id, e.vector as embedding, a.title, a.content
                FROM artifacts a
                LEFT JOIN embeddings e ON a.id = e.artifact_id
                WHERE e.vector IS NOT NULL
                ORDER BY a.created_at DESC
                LIMIT %s
            """, (limit,))
            return [dict(row) for row in cur.fetchall()]

    def get_artifact_count_since(self, since_date: datetime) -> int:
        """Get count of artifacts created since given date."""
        conn = self.get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM artifacts
                WHERE created_at > %s
            """, (since_date,))
            return cur.fetchone()[0]

    def search_artifacts(self, query: str, limit: int = 10, filters: Dict = None) -> List[Dict]:
        """Search artifacts using text search."""
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Build search query
            sql = """
                SELECT DISTINCT a.id, a.title, a.content, a.created_at,
                       ae.consumption_status, ae.importance_score
                FROM artifacts a
                LEFT JOIN artifacts_extended ae ON a.id = ae.artifact_id
                WHERE a.title ILIKE %s OR a.content ILIKE %s
            """
            params = [f"%{query}%", f"%{query}%"]

            # Apply filters
            if filters:
                if "consumption_status" in filters:
                    status_list = filters["consumption_status"]
                    if isinstance(status_list, str):
                        status_list = [status_list]
                    placeholders = ",".join(["%s"] * len(status_list))
                    sql += f" AND ae.consumption_status IN ({placeholders})"
                    params.extend(status_list)

                if "min_importance" in filters:
                    sql += " AND COALESCE(ae.importance_score, 0) >= %s"
                    params.append(filters["min_importance"])

            sql += " ORDER BY a.created_at DESC LIMIT %s"
            params.append(limit)

            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

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

    # --- Artifacts Extended (for Insights & Curation) ---
    def upsert_artifact_extended(self, artifact_id, **kwargs):
        """Insert or update artifact extended metadata"""
        conn = self.get_connection()

        # Check if record exists
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM artifacts_extended WHERE artifact_id = %s", (artifact_id,))
            exists = cur.fetchone() is not None

        if exists:
            # Update existing record
            set_clauses = []
            values = []

            for key, value in kwargs.items():
                if key in ['consumption_score', 'importance_score', 'consumption_status', 'last_consumed_at',
                          'consumption_count', 'estimated_read_time', 'auto_tags', 'entities', 'insights',
                          'summary', 'related_artifacts', 'parent_artifact', 'view_count', 'engagement_score']:
                    set_clauses.append(f"{key} = %s")
                    values.append(value)

            if set_clauses:
                values.append(artifact_id)
                query = f"""
                    UPDATE artifacts_extended
                    SET {', '.join(set_clauses)}
                    WHERE artifact_id = %s
                """
                with conn.cursor() as cur:
                    cur.execute(query, values)
        else:
            # Insert new record
            columns = ['artifact_id']
            values = [artifact_id]
            placeholders = ['%s']

            # Add all provided fields
            for key, value in kwargs.items():
                if key in ['consumption_score', 'importance_score', 'consumption_status', 'last_consumed_at',
                          'consumption_count', 'estimated_read_time', 'auto_tags', 'entities', 'insights',
                          'summary', 'related_artifacts', 'parent_artifact', 'view_count', 'engagement_score']:
                    columns.append(key)
                    values.append(value)
                    placeholders.append('%s')

            query = f"""
                INSERT INTO artifacts_extended ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
            """
            with conn.cursor() as cur:
                cur.execute(query, values)

    def get_artifact_extended(self, artifact_id):
        """Get artifact extended metadata"""
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT ae.*, a.title, a.content, a.metadata, a.created_at as artifact_created_at
                FROM artifacts_extended ae
                JOIN artifacts a ON ae.artifact_id = a.id
                WHERE ae.artifact_id = %s
            """, (artifact_id,))
            return cur.fetchone()

    def get_artifacts_with_extended(self, limit=None, consumption_status=None):
        """Get artifacts with their extended metadata"""
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT a.*, ae.consumption_score, ae.importance_score, ae.consumption_status,
                       ae.last_consumed_at, ae.consumption_count, ae.estimated_read_time,
                       ae.auto_tags, ae.entities, ae.insights, ae.summary, ae.view_count,
                       ae.engagement_score, ae.related_artifacts
                FROM artifacts a
                LEFT JOIN artifacts_extended ae ON a.id = ae.artifact_id
            """
            params = []

            if consumption_status:
                query += " WHERE ae.consumption_status = %s"
                params.append(consumption_status)

            query += " ORDER BY a.created_at DESC"

            if limit:
                query += " LIMIT %s"
                params.append(limit)

            cur.execute(query, params)
            return cur.fetchall()

    # --- Consumption Events ---
    def track_consumption_event(self, artifact_id, event_type, duration_seconds=None,
                               engagement_score=None, scroll_depth=None, session_id=None,
                               source=None, metadata=None):
        """Track a consumption event for an artifact"""
        conn = self.get_connection()
        event_id = str(uuid.uuid4())

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO consumption_events
                (id, artifact_id, event_type, duration_seconds, engagement_score,
                 scroll_depth, session_id, source, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (event_id, artifact_id, event_type, duration_seconds, engagement_score,
                  scroll_depth, session_id, source, Json(metadata or {})))

        # Update artifact consumption stats
        self._update_consumption_stats(artifact_id, event_type, duration_seconds, engagement_score)

        return event_id

    def _update_consumption_stats(self, artifact_id, event_type, duration_seconds, engagement_score):
        """Update artifact consumption statistics"""
        conn = self.get_connection()

        # Determine engagement delta based on event type
        engagement_delta = {
            'view': 0.1,
            'skim': 0.3,
            'read': 0.7,
            'highlight': 0.2,
            'note': 0.5,
            'apply': 1.0,
            'share': 0.8
        }.get(event_type, 0.1)

        with conn.cursor() as cur:
            # Check if artifact_extended record exists
            cur.execute("SELECT id FROM artifacts_extended WHERE artifact_id = %s", (artifact_id,))
            exists = cur.fetchone() is not None

            if exists:
                cur.execute("""
                    UPDATE artifacts_extended
                    SET consumption_count = consumption_count + 1,
                        view_count = view_count + CASE WHEN %s = 'view' THEN 1 ELSE 0 END,
                        engagement_score = LEAST(engagement_score + %s, 10.0),
                        consumption_status = CASE
                            WHEN %s = 'applied' THEN 'applied'
                            WHEN %s = 'read' AND consumption_status != 'applied' THEN 'reviewed'
                            WHEN %s = 'skim' AND consumption_status NOT IN ('reviewed', 'applied') THEN 'reading'
                            ELSE consumption_status
                        END,
                        last_consumed_at = NOW()
                    WHERE artifact_id = %s
                """, (event_type, engagement_delta, event_type, event_type, event_type, artifact_id))

    def get_consumption_events(self, artifact_id=None, event_type=None, limit=None):
        """Get consumption events, optionally filtered"""
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = "SELECT * FROM consumption_events WHERE 1=1"
            params = []

            if artifact_id:
                query += " AND artifact_id = %s"
                params.append(artifact_id)

            if event_type:
                query += " AND event_type = %s"
                params.append(event_type)

            query += " ORDER BY created_at DESC"

            if limit:
                query += " LIMIT %s"
                params.append(limit)

            cur.execute(query, params)
            return cur.fetchall()

    # --- Artifact Relationships ---
    def create_relationship(self, source_artifact_id, target_artifact_id, relationship_type,
                           strength, evidence=None, created_by='auto'):
        """Create a relationship between two artifacts"""
        conn = self.get_connection()
        relationship_id = str(uuid.uuid4())

        with conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO artifact_relationships
                    (id, source_artifact, target_artifact, relationship_type, strength, evidence, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (relationship_id, source_artifact_id, target_artifact_id,
                      relationship_type, strength, evidence, created_by))

                # Update related_artifacts arrays
                self._update_related_artifacts(source_artifact_id, target_artifact_id)

                return relationship_id
            except psycopg2.IntegrityError:
                # Relationship already exists
                return None

    def _update_related_artifacts(self, artifact1_id, artifact2_id):
        """Update the related_artifacts arrays for both artifacts"""
        conn = self.get_connection()

        with conn.cursor() as cur:
            # Update artifact1
            cur.execute("""
                INSERT INTO artifacts_extended (artifact_id, related_artifacts)
                VALUES (%s, ARRAY[%s])
                ON CONFLICT (artifact_id)
                DO UPDATE SET
                    related_artifacts = array_distinct(
                        artifacts_extended.related_artifacts || ARRAY[%s::uuid]
                    ),
                    updated_at = NOW()
            """, (artifact1_id, artifact2_id, artifact2_id))

            # Update artifact2
            cur.execute("""
                INSERT INTO artifacts_extended (artifact_id, related_artifacts)
                VALUES (%s, ARRAY[%s])
                ON CONFLICT (artifact_id)
                DO UPDATE SET
                    related_artifacts = array_distinct(
                        artifacts_extended.related_artifacts || ARRAY[%s::uuid]
                    ),
                    updated_at = NOW()
            """, (artifact2_id, artifact1_id, artifact1_id))

    def get_artifact_relationships(self, artifact_id, relationship_type=None):
        """Get relationships for an artifact"""
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT ar.*,
                       sa.title as source_title,
                       ta.title as target_title
                FROM artifact_relationships ar
                JOIN artifacts sa ON ar.source_artifact = sa.id
                JOIN artifacts ta ON ar.target_artifact = ta.id
                WHERE (ar.source_artifact = %s OR ar.target_artifact = %s)
            """
            params = [artifact_id, artifact_id]

            if relationship_type:
                query += " AND ar.relationship_type = %s"
                params.append(relationship_type)

            query += " ORDER BY ar.strength DESC"

            cur.execute(query, params)
            return cur.fetchall()

    # --- User Goals ---
    def create_goal(self, goal, description=None, priority=5, tags=None, related_topics=None):
        """Create a new user goal"""
        conn = self.get_connection()
        goal_id = str(uuid.uuid4())

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_goals (id, goal, description, priority, tags, related_topics)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (goal_id, goal, description, priority, tags or [], related_topics or []))

        return goal_id

    def get_active_goals(self):
        """Get all active user goals"""
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM user_goals
                WHERE active = true
                ORDER BY priority DESC, created_at ASC
            """)
            return cur.fetchall()

    def update_goal_progress(self, goal_id, progress):
        """Update goal progress"""
        conn = self.get_connection()

        with conn.cursor() as cur:
            cur.execute("""
                UPDATE user_goals
                SET progress = %s,
                    updated_at = NOW(),
                    completed_at = CASE WHEN %s >= 1.0 THEN NOW() ELSE completed_at END,
                    active = CASE WHEN %s >= 1.0 THEN false ELSE active END
                WHERE id = %s
            """, (progress, progress, progress, goal_id))

    # --- Consumption Queue ---
    def add_to_consumption_queue(self, artifact_id, queue_type, score, reason=None, related_goal_id=None, expires_in_hours=24):
        """Add an artifact to the consumption queue"""
        conn = self.get_connection()
        queue_id = str(uuid.uuid4())

        expires_at = datetime.now() + timedelta(hours=expires_in_hours)

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO consumption_queue
                (id, artifact_id, queue_type, score, reason, related_goal_id, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (queue_id, artifact_id, queue_type, score, reason, related_goal_id, expires_at))

        return queue_id

    def get_consumption_queue(self, queue_type=None, limit=20):
        """Get items from the consumption queue"""
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT cq.*, a.title, a.content, a.metadata, a.created_at as artifact_created_at,
                       ae.consumption_status, ae.importance_score
                FROM consumption_queue cq
                JOIN artifacts a ON cq.artifact_id = a.id
                LEFT JOIN artifacts_extended ae ON a.id = ae.artifact_id
                WHERE cq.expires_at > NOW() AND cq.consumed_at IS NULL
            """
            params = []

            if queue_type:
                query += " AND cq.queue_type = %s"
                params.append(queue_type)

            query += " ORDER BY cq.score DESC LIMIT %s"
            params.append(limit)

            cur.execute(query, params)
            return cur.fetchall()

    def mark_queue_item_consumed(self, queue_id):
        """Mark a queue item as consumed"""
        conn = self.get_connection()

        with conn.cursor() as cur:
            cur.execute("""
                UPDATE consumption_queue
                SET consumed_at = NOW()
                WHERE id = %s
            """, (queue_id,))

    def cleanup_expired_queue(self):
        """Remove expired items from the queue"""
        conn = self.get_connection()

        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM consumption_queue
                WHERE expires_at <= NOW() AND consumed_at IS NULL
            """)

    # --- Migration Helper ---
    def run_migration(self, migration_file):
        """Run a SQL migration file"""
        conn = self.get_connection()

        with open(migration_file, 'r') as f:
            migration_sql = f.read()

        with conn.cursor() as cur:
            cur.execute(migration_sql)

        logger.info(f"Migration {migration_file} completed successfully")
