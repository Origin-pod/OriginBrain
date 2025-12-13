import os
import shutil
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from src.brain.vector_store import BrainDB

TEST_DB_PATH = "./test_brain_db"

@pytest.fixture
def setup_db():
    if os.path.exists(TEST_DB_PATH):
        shutil.rmtree(TEST_DB_PATH)
    yield TEST_DB_PATH
    if os.path.exists(TEST_DB_PATH):
        shutil.rmtree(TEST_DB_PATH)

@patch('src.brain.vector_store.SentenceTransformer')
def test_add_and_search(mock_model_cls, setup_db):
    # Mock the model
    mock_model = MagicMock()
    mock_model.encode.side_effect = lambda x: np.array([0.1, 0.2, 0.3]) if x == "content" else np.array([0.1, 0.2, 0.3])
    mock_model_cls.return_value = mock_model
    
    db = BrainDB(db_path=setup_db)
    
    # Add Artifact
    content = "This is a test note about AI."
    metadata = {"source": "test", "date": "2025-01-01"}
    
    artifact_id = db.add_artifact(content, metadata)
    
    assert os.path.exists(os.path.join(setup_db, "data.json"))
    assert os.path.exists(os.path.join(setup_db, "embeddings.npy"))
    
    # Search
    results = db.search("AI query")
    
    assert results is not None
    assert len(results['documents'][0]) == 1
    assert results['documents'][0][0] == content
    assert results['metadatas'][0][0] == metadata
