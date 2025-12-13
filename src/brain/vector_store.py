import os
import json
import logging
import uuid
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

class BrainDB:
    def __init__(self, db_path="./brain_db"):
        self.db_path = db_path
        self.data_file = os.path.join(db_path, "data.json")
        self.embeddings_file = os.path.join(db_path, "embeddings.npy")
        
        os.makedirs(db_path, exist_ok=True)
        
        # Initialize Embedding Model
        logger.info("Loading embedding model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Load existing data
        self.documents = []
        self.metadatas = []
        self.ids = []
        self.embeddings = None
        
        self._load_db()
        logger.info("BrainDB initialized (SimpleVectorStore).")

    def _load_db(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.documents = data.get('documents', [])
                self.metadatas = data.get('metadatas', [])
                self.ids = data.get('ids', [])
        
        if os.path.exists(self.embeddings_file):
            self.embeddings = np.load(self.embeddings_file)
        else:
            self.embeddings = np.empty((0, 384)) # 384 is dim of all-MiniLM-L6-v2

    def _save_db(self):
        data = {
            'documents': self.documents,
            'metadatas': self.metadatas,
            'ids': self.ids
        }
        with open(self.data_file, 'w') as f:
            json.dump(data, f)
        
        np.save(self.embeddings_file, self.embeddings)

    def add_artifact(self, content, metadata, artifact_id=None):
        try:
            if not artifact_id:
                artifact_id = str(uuid.uuid4())
                
            # Generate Embedding
            embedding = self.model.encode(content)
            
            # Update Memory
            self.documents.append(content)
            self.metadatas.append(metadata)
            self.ids.append(artifact_id)
            
            if self.embeddings.shape[0] == 0:
                self.embeddings = np.array([embedding])
            else:
                self.embeddings = np.vstack([self.embeddings, embedding])
            
            # Persist
            self._save_db()
            
            logger.info(f"Indexed artifact: {artifact_id}")
            return artifact_id
            
        except Exception as e:
            logger.error(f"Failed to index artifact: {str(e)}")
            raise e

    def search(self, query, n_results=5):
        try:
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
