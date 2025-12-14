import os
import json
import logging
import uuid
import numpy as np
import time
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from src.db.db import BrainDB as PostgresDB

logger = logging.getLogger(__name__)

class BrainDB:
    def __init__(self, db_path=None):
        # db_path is ignored now, kept for compatibility
        self.pg_db = PostgresDB()
        
        # Initialize Embedding Model
        logger.info("Loading embedding model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # In-memory cache for search
        self.documents = []
        self.metadatas = []
        self.ids = []
        self.embeddings = np.empty((0, 384))
        
        self.last_count = 0
        self._load_db()
        logger.info("BrainDB initialized (Postgres-backed).")

    def _load_db(self):
        """Loads all embeddings from Postgres into memory."""
        try:
            rows = self.pg_db.get_all_embeddings()
            
            self.documents = []
            self.metadatas = []
            self.ids = []
            vectors = []
            
            for row in rows:
                self.documents.append(row['content'])
                self.metadatas.append(row['metadata'])
                self.ids.append(str(row['artifact_id']))
                vectors.append(row['vector'])
            
            if vectors:
                self.embeddings = np.array(vectors)
            else:
                self.embeddings = np.empty((0, 384))
                
            self.last_count = len(self.documents)
            logger.info(f"Loaded {self.last_count} embeddings from DB")
            
        except Exception as e:
            logger.error(f"Failed to load DB: {e}")

    def _check_for_updates(self):
        """Checks if DB has more items than memory."""
        try:
            current_count = self.pg_db.get_artifact_count()
            if current_count > self.last_count:
                logger.info(f"DB count ({current_count}) > Memory ({self.last_count}). Reloading...")
                self._load_db()
        except Exception as e:
            logger.error(f"Failed to check updates: {e}")

    def get_last_updated_at(self):
        """Returns the timestamp of the last update."""
        if self.last_count > 0:
            # Return current time to force frontend update if we have items
            # Ideally we'd store a 'last_sync_time' in the class
            return time.time()
        return 0

    def add_artifact(self, content, metadata, artifact_id=None):
        try:
            if not artifact_id:
                artifact_id = str(uuid.uuid4())
                
            # Generate Embedding
            embedding = self.model.encode(content).tolist() # Convert to list for JSON
            
            # Persist to DB
            # Note: IngestDaemon already inserts Artifact. We just need to insert Embedding.
            # But wait, IngestDaemon calls this.
            # If IngestDaemon inserts Artifact, we need to insert Embedding here.
            
            self.pg_db.insert_embedding(artifact_id, embedding, "all-MiniLM-L6-v2")
            
            # Update Memory
            self.documents.append(content)
            self.metadatas.append(metadata)
            self.ids.append(artifact_id)
            
            if self.embeddings.shape[0] == 0:
                self.embeddings = np.array([embedding])
            else:
                self.embeddings = np.vstack([self.embeddings, np.array(embedding)])
            
            self.last_count += 1
            logger.info(f"Indexed artifact: {artifact_id}")
            return artifact_id
            
        except Exception as e:
            logger.error(f"Failed to index artifact: {str(e)}")
            raise e

    def search(self, query, n_results=5):
        try:
            # Check for external updates before searching
            self._check_for_updates()
            
            if self.embeddings.shape[0] == 0:
                return None
                
            query_embedding = self.model.encode(query).reshape(1, -1)
            
            # Calculate Cosine Similarity
            scores = cosine_similarity(query_embedding, self.embeddings)[0]
            
            # Get Top N indices
            top_indices = np.argsort(scores)[::-1][:n_results]
            
            results = {
                'documents': [[self.documents[i] for i in top_indices]],
                'metadatas': [[self.metadatas[i] for i in top_indices]],
                'distances': [[scores[i] for i in top_indices]],
                'ids': [[self.ids[i] for i in top_indices]]
            }
            
            return results
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return None
