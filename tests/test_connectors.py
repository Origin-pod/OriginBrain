import os
import json
import pytest
import glob
from unittest.mock import patch, MagicMock
from ingest_daemon import IngestHandler, INBOX_DIR, ARCHIVE_DIR, ERROR_DIR

@pytest.fixture
def setup_dirs():
    # Setup
    for d in [INBOX_DIR, ARCHIVE_DIR, ERROR_DIR]:
        os.makedirs(d, exist_ok=True)
    yield
    # No teardown to allow inspection if needed

@patch('src.connectors.web_scraper.fetch_url_content')
def test_web_connector_dispatch(mock_fetch, setup_dirs):
    handler = IngestHandler()
    
    # Mock return value
    mock_fetch.return_value = {
        "type": "article",
        "title": "Test Page",
        "content": "# Test Page\n\nContent here.",
        "source_url": "http://example.com"
    }
    
    # Create payload
    payload = {
        "type": "url",
        "payload": "http://example.com",
        "timestamp": 123
    }
    
    test_file = os.path.join(INBOX_DIR, "web_test.json")
    with open(test_file, "w") as f:
        json.dump(payload, f)
        
    handler.process_file(test_file)
    
    # Verify Mock called
    mock_fetch.assert_called_with("http://example.com")
    
    # Verify Markdown created
    # We need to find the date folder
    import glob
    md_files = glob.glob(os.path.join(ARCHIVE_DIR, "*", "web_test.md"))
    assert len(md_files) > 0
    
    with open(md_files[0], "r") as f:
        content = f.read()
        assert "Test Page" in content
        assert "source_url" in content

@patch('src.connectors.twitter_fetcher.fetch_tweet')
def test_twitter_connector_dispatch(mock_fetch, setup_dirs):
    handler = IngestHandler()
    
    mock_fetch.return_value = {
        "type": "tweet",
        "author": "jack",
        "content": "just setting up my twttr",
        "source_url": "https://twitter.com/jack/status/20"
    }
    
    payload = {
        "type": "url",
        "payload": "https://twitter.com/jack/status/20",
        "timestamp": 123
    }
    
    test_file = os.path.join(INBOX_DIR, "tweet_test.json")
    with open(test_file, "w") as f:
        json.dump(payload, f)
        
    handler.process_file(test_file)
    
    mock_fetch.assert_called_with("https://twitter.com/jack/status/20")
    
    md_files = glob.glob(os.path.join(ARCHIVE_DIR, "*", "tweet_test.md"))
    assert len(md_files) > 0
    
    with open(md_files[0], "r") as f:
        content = f.read()
        assert "just setting up my twttr" in content
