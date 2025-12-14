"""
Accelerated Search Service for OriginBrain.
Implements Faiss-based vector search for improved performance.
"""

import numpy as np
import faiss
import pickle
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import threading
from src.db.db import BrainDB

logger = logging.getLogger(__name__)

class AcceleratedSearch:
    """High-performance vector search using Faiss."""

    def __init__(self, embedding_dim: int = None):
        self.db = BrainDB()
        self.index = None
        self.id_map = []  # Maps index position to artifact_id
        self.last_updated = None
        self.update_lock = threading.Lock()

        # Auto-detect embedding dimension if not provided
        if embedding_dim is None:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT jsonb_array_length(vector) as dim
                    FROM embeddings
                    WHERE vector IS NOT NULL
                    LIMIT 1
                """)
                result = cur.fetchone()
                self.embedding_dim = result[0] if result else 1536
        else:
            self.embedding_dim = embedding_dim

        # Initialize index
        self._initialize_index()

    def _initialize_index(self):
        """Initialize Faiss index."""
        # For small datasets, use a simple flat index
        # For larger datasets, use IVF (Inverted File) index
        if self.embedding_dim and self.embedding_dim > 0:
            # Start with a flat index - will switch to IVF if dataset grows
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            self.index_type = "Flat"
        else:
            raise ValueError("Invalid embedding dimension")

    def rebuild_index(self, force: bool = False) -> Dict:
        """
        Rebuild the search index from database artifacts.

        Args:
            force: Force rebuild even if recently updated

        Returns:
            Dictionary with rebuild statistics
        """
        # Check if rebuild is needed
        if not force and self.last_updated:
            # Only rebuild if data has changed significantly
            recent_count = self.db.get_artifact_count_since(self.last_updated)
            if recent_count < 50:  # Threshold for incremental updates
                return {"message": "Index up to date", "new_artifacts": recent_count}

        with self.update_lock:
            try:
                # Get all artifacts with embeddings
                artifacts = self.db.get_artifacts_for_indexing()

                if not artifacts:
                    return {"message": "No artifacts to index"}

                # Prepare embeddings matrix
                embeddings = []
                self.id_map = []

                for artifact in artifacts:
                    if artifact.get('embedding'):
                        # Handle both list and JSON string embeddings
                        embedding_data = artifact['embedding']
                        if isinstance(embedding_data, str):
                            import json
                            embedding_data = json.loads(embedding_data)

                        embedding = np.array(embedding_data, dtype=np.float32)
                        # Only include embeddings with matching dimensions
                        if len(embedding) == self.embedding_dim:
                            embeddings.append(embedding)
                            self.id_map.append(artifact['id'])

                if not embeddings:
                    return {"message": "No valid embeddings found"}

                embeddings = np.vstack(embeddings)

                # Rebuild index
                self._initialize_index()

                # For Flat index, no training needed
                # For IVF index, training would be required
                if hasattr(self.index, 'is_trained') and not self.index.is_trained:
                    self.index.train(embeddings)

                # Add vectors to index
                batch_size = 1000
                for i in range(0, len(embeddings), batch_size):
                    batch = embeddings[i:i+batch_size]
                    self.index.add(batch)

                self.last_updated = datetime.now()

                return {
                    "success": True,
                    "indexed_artifacts": len(embeddings),
                    "index_size": self.index.ntotal,
                    "last_updated": self.last_updated.isoformat()
                }

            except Exception as e:
                logger.error(f"Failed to rebuild index: {e}")
                return {"error": str(e)}

    def search_similar(self, query_embedding: List[float],
                      k: int = 10,
                      filters: Optional[Dict] = None) -> List[Dict]:
        """
        Search for similar artifacts using accelerated vector search.

        Args:
            query_embedding: Embedding vector to search for
            k: Number of results to return
            filters: Optional filters to apply

        Returns:
            List of similar artifacts with scores
        """
        if self.index is None or self.index.ntotal == 0:
            # Fallback to database search
            return self._fallback_search(query_embedding, k, filters)

        try:
            # Convert query to numpy array
            query = np.array([query_embedding], dtype=np.float32)

            # Search index
            scores, indices = self.index.search(query, min(k, self.index.ntotal))

            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and idx < len(self.id_map):
                    artifact_id = self.id_map[idx]
                    artifact = self.db.get_artifact_extended(artifact_id)

                    if artifact and self._passes_filters(artifact, filters):
                        results.append({
                            "artifact": artifact,
                            "similarity_score": float(score),
                            "distance": float(np.sqrt(score))  # Convert to Euclidean distance
                        })

            # Sort by similarity (lower distance = more similar)
            results.sort(key=lambda x: x["distance"])

            return results[:k]

        except Exception as e:
            logger.error(f"Accelerated search failed: {e}")
            return self._fallback_search(query_embedding, k, filters)

    def search_hybrid(self, query: str, query_embedding: List[float],
                     k: int = 10,
                     text_weight: float = 0.3,
                     vector_weight: float = 0.7,
                     filters: Optional[Dict] = None) -> List[Dict]:
        """
        Hybrid search combining text and vector similarity.

        Args:
            query: Text query for keyword matching
            query_embedding: Vector embedding for semantic search
            k: Number of results
            text_weight: Weight for text search results
            vector_weight: Weight for vector search results
            filters: Optional filters

        Returns:
            Combined search results
        """
        # Get text search results
        text_results = self.db.search_artifacts(query, limit=k*2, filters=filters)

        # Get vector search results
        vector_results = self.search_similar(query_embedding, k*2, filters)

        # Combine and score results
        combined_scores = {}

        # Score text results
        for i, artifact in enumerate(text_results):
            artifact_id = artifact["id"]
            # Text score based on position (1/N ranking)
            text_score = 1.0 / (i + 1)
            combined_scores[artifact_id] = {
                "artifact": artifact,
                "text_score": text_score,
                "vector_score": 0.0,
                "combined_score": text_score * text_weight
            }

        # Score vector results
        for result in vector_results:
            artifact = result["artifact"]
            artifact_id = artifact["id"]
            # Convert distance to similarity (lower distance = higher similarity)
            max_distance = 2.0  # Typical maximum for normalized vectors
            vector_score = max(0, 1 - result["distance"] / max_distance)

            if artifact_id in combined_scores:
                combined_scores[artifact_id]["vector_score"] = vector_score
                combined_scores[artifact_id]["combined_score"] += vector_score * vector_weight
            else:
                combined_scores[artifact_id] = {
                    "artifact": artifact,
                    "text_score": 0.0,
                    "vector_score": vector_score,
                    "combined_score": vector_score * vector_weight
                }

        # Sort by combined score
        results = sorted(combined_scores.values(),
                        key=lambda x: x["combined_score"],
                        reverse=True)

        return results[:k]

    def recommend_similar_artifacts(self, artifact_id: str,
                                  k: int = 5,
                                  exclude_consumed: bool = True) -> List[Dict]:
        """
        Find artifacts similar to a given artifact.

        Args:
            artifact_id: ID of reference artifact
            k: Number of recommendations
            exclude_consumed: Exclude already consumed artifacts

        Returns:
            List of recommended artifacts
        """
        artifact = self.db.get_artifact_extended(artifact_id)
        if not artifact or not artifact.get('embedding'):
            return []

        filters = {}
        if exclude_consumed:
            filters["consumption_status"] = ["unconsumed", "reading"]

        results = self.search_similar(artifact['embedding'], k+1, filters)

        # Remove the reference artifact itself
        return [r for r in results if r["artifact"]["id"] != artifact_id][:k]

    def get_index_stats(self) -> Dict:
        """Get information about the search index."""
        return {
            "index_size": self.index.ntotal if self.index else 0,
            "embedding_dimension": self.embedding_dim,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "index_type": getattr(self, 'index_type', 'Unknown'),
            "nlist": 100 if hasattr(self, 'index_type') and self.index_type == 'IVF-Flat' else None,
            "nprobe": getattr(self.index, 'nprobe', None) if self.index and hasattr(self.index, 'nprobe') else None
        }

    def optimize_index(self):
        """Optimize index for better performance."""
        if not self.index or self.index.ntotal == 0:
            return {"message": "No index to optimize"}

        try:
            # For IVF indexes, we can optimize nprobe
            if hasattr(self.index, 'nprobe'):
                self.index.nprobe = min(20, getattr(self.index, 'nlist', 100))
                return {
                    "success": True,
                    "message": "Index optimized",
                    "nprobe": self.index.nprobe
                }
            else:
                return {
                    "success": True,
                    "message": "Flat index - no optimization needed",
                    "index_type": "Flat"
                }
        except Exception as e:
            logger.error(f"Failed to optimize index: {e}")
            return {"error": str(e)}

    def save_index(self, filepath: str):
        """Save index to disk."""
        if not self.index:
            raise ValueError("No index to save")

        try:
            # Save Faiss index
            faiss.write_index(self.index, f"{filepath}.faiss")

            # Save metadata
            metadata = {
                "id_map": self.id_map,
                "last_updated": self.last_updated,
                "embedding_dim": self.embedding_dim
            }

            with open(f"{filepath}.meta", "wb") as f:
                pickle.dump(metadata, f)

            logger.info(f"Index saved to {filepath}")

        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            raise

    def load_index(self, filepath: str):
        """Load index from disk."""
        try:
            # Load Faiss index
            self.index = faiss.read_index(f"{filepath}.faiss")

            # Load metadata
            with open(f"{filepath}.meta", "rb") as f:
                metadata = pickle.load(f)

            self.id_map = metadata["id_map"]
            self.last_updated = metadata["last_updated"]
            self.embedding_dim = metadata["embedding_dim"]

            logger.info(f"Index loaded from {filepath}")

        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            raise

    def _fallback_search(self, query_embedding: List[float],
                        k: int,
                        filters: Optional[Dict] = None) -> List[Dict]:
        """Fallback to database search when index is unavailable."""
        # Use database's vector search as fallback
        artifacts = self.db.get_artifacts_with_extended(limit=100)

        results = []
        for artifact in artifacts:
            if artifact.get('embedding') and self._passes_filters(artifact, filters):
                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_embedding, artifact['embedding'])
                results.append({
                    "artifact": artifact,
                    "similarity_score": similarity,
                    "distance": 1 - similarity  # Convert to distance
                })

        # Sort by similarity
        results.sort(key=lambda x: x["distance"])

        return results[:k]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a = np.array(a)
        b = np.array(b)

        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0

        return dot_product / (norm_a * norm_b)

    def _passes_filters(self, artifact: Dict, filters: Optional[Dict]) -> bool:
        """Check if artifact passes the provided filters."""
        if not filters:
            return True

        # Consumption status filter
        if "consumption_status" in filters:
            allowed = filters["consumption_status"]
            if isinstance(allowed, str):
                allowed = [allowed]
            if artifact.get("consumption_status") not in allowed:
                return False

        # Import score filter
        if "min_importance" in filters:
            if artifact.get("importance_score", 0) < filters["min_importance"]:
                return False

        # Date range filter
        if "date_from" in filters:
            if artifact.get("created_at") and artifact["created_at"] < filters["date_from"]:
                return False

        if "date_to" in filters:
            if artifact.get("created_at") and artifact["created_at"] > filters["date_to"]:
                return False

        return True