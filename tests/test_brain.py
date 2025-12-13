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
    
    # Verify search finds it
    results = db.search("AI query") # Changed from "test" to "AI query" to match original intent
    
    assert results is not None
    assert len(results['documents'][0]) == 1
    assert results['documents'][0][0] == content # Changed from "This is a test artifact" to content
    assert results['metadatas'][0][0] == metadata

@patch('src.brain.vector_store.SentenceTransformer')
def test_auto_reload(mock_model_cls, setup_db):
    # Mock the model
    mock_model = MagicMock()
    mock_model.encode.side_effect = lambda x: np.array([0.1, 0.2, 0.3]) # Simple mock for encoding
    mock_model_cls.return_value = mock_model

    # Initialize DB 1
    db1 = BrainDB(db_path=setup_db)
    db1.add_artifact("Content 1", {"source": "test1"})
    
    # Initialize DB 2 (simulating another process like the daemon)
    # We need to wait a bit to ensure mtime changes if filesystem is fast
    import time
    time.sleep(0.1)
    
    db2 = BrainDB(db_path=setup_db)
    db2.add_artifact("Content 2", {"source": "test2"})
    
    # DB 1 should not see Content 2 yet (in memory)
    # But search() triggers _check_for_updates()
    results = db1.search("Content 2")
    
    assert results is not None
    # Should find both documents now
    found_content = [doc for sublist in results['documents'] for doc in sublist]
    assert "Content 2" in found_content
    assert "Content 1" in found_content
