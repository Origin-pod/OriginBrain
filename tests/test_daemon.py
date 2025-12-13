import os
import shutil
import time
import json
import pytest
from datetime import datetime
from ingest_daemon import IngestHandler, BASE_DIR, INBOX_DIR, ARCHIVE_DIR, ERROR_DIR

@pytest.fixture
def setup_dirs():
    # Setup
    for d in [INBOX_DIR, ARCHIVE_DIR, ERROR_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)
    
    yield
    
    # Teardown
    for d in [INBOX_DIR, ARCHIVE_DIR, ERROR_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d)

def test_valid_json_ingest(setup_dirs):
    handler = IngestHandler()
    
    # Create valid payload
    payload = {
        "type": "url",
        "payload": "https://example.com",
        "timestamp": 1234567890,
        "note": "Test note"
    }
    
    test_file = os.path.join(INBOX_DIR, "valid.json")
    with open(test_file, "w") as f:
        json.dump(payload, f)
    
    # Trigger processing
    handler.process_file(test_file)
    
    # Check Archive
    date_str = datetime.now().strftime('%Y-%m-%d')
    expected_path = os.path.join(ARCHIVE_DIR, date_str, "valid.json")
    
    assert os.path.exists(expected_path)
    assert not os.path.exists(test_file)

def test_invalid_schema(setup_dirs):
    handler = IngestHandler()
    
    # Missing 'timestamp'
    payload = {
        "type": "url",
        "payload": "https://example.com"
    }
    
    test_file = os.path.join(INBOX_DIR, "invalid.json")
    with open(test_file, "w") as f:
        json.dump(payload, f)
        
    handler.process_file(test_file)
    
    # Check Error
    expected_path = os.path.join(ERROR_DIR, "invalid.json")
    log_path = expected_path + ".log"
    
    assert os.path.exists(expected_path)
    assert os.path.exists(log_path)
    
    with open(log_path, "r") as f:
        content = f.read()
        assert "Schema Validation Failed" in content
        assert "'timestamp' is a required property" in content

def test_non_json_file(setup_dirs):
    handler = IngestHandler()
    
    test_file = os.path.join(INBOX_DIR, "notes.txt")
    with open(test_file, "w") as f:
        f.write("Just some text")
        
    handler.process_file(test_file)
    
    expected_path = os.path.join(ERROR_DIR, "notes.txt")
    log_path = expected_path + ".log"
    
    assert os.path.exists(expected_path)
    with open(log_path, "r") as f:
        assert "Only .json allowed" in f.read()
