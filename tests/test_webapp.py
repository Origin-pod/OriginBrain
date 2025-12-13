import os
import json
import pytest
import shutil
from app import app, INBOX_DIR

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def setup_inbox():
    if os.path.exists(INBOX_DIR):
        shutil.rmtree(INBOX_DIR)
    os.makedirs(INBOX_DIR, exist_ok=True)
    yield
    if os.path.exists(INBOX_DIR):
        shutil.rmtree(INBOX_DIR)

def test_index_route(client):
    rv = client.get('/')
    assert rv.status_code == 200
    assert b"OriginSteward" in rv.data

def test_drop_route(client, setup_inbox):
    rv = client.post('/drop', data={
        'payload': 'https://example.com',
        'note': 'Test note'
    })
    
    assert rv.status_code == 200
    assert rv.json['success'] is True
    
    # Verify file created
    files = os.listdir(INBOX_DIR)
    assert len(files) == 1
    assert files[0].startswith("web_drop_")
    assert files[0].endswith(".json")
    
    # Verify content
    with open(os.path.join(INBOX_DIR, files[0]), 'r') as f:
        data = json.load(f)
        assert data['type'] == 'url'
        assert data['payload'] == 'https://example.com'
        assert data['note'] == 'Test note'

def test_search_route(client):
    rv = client.post('/search', 
        json={'query': 'test'},
        content_type='application/json'
    )
    
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert 'results' in data
    assert isinstance(data['results'], list)
    
    # Verify structure of results
    if data['results']:
        result = data['results'][0]
        assert 'score' in result
        assert 'source' in result
        assert 'content' in result
        assert isinstance(result['score'], float)

