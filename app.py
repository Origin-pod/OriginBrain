import os
import json
import time
from flask import Flask, request, render_template_string, jsonify
from flask_cors import CORS
from src.brain.vector_store import BrainDB

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

INBOX_DIR = os.path.abspath("Inbox")
BRAIN_DB_DIR = os.path.abspath("brain_db")

# Initialize BrainDB
brain = BrainDB(BRAIN_DB_DIR)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>OriginSteward</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; 
            margin: 0;
            padding: 2rem; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container { max-width: 800px; margin: 0 auto; }
        .header { text-align: center; color: white; margin-bottom: 2rem; }
        .header h1 { margin: 0; font-size: 2.5rem; font-weight: 700; }
        .header p { margin: 0.5rem 0 0; opacity: 0.9; }
        
        .card { 
            background: white; 
            padding: 2rem; 
            border-radius: 16px; 
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        .card h2 { margin-top: 0; font-size: 1.25rem; color: #18181b; }
        
        input[type="text"], textarea { 
            width: 100%; 
            padding: 0.875rem; 
            margin-bottom: 1rem; 
            border: 2px solid #e4e4e7; 
            border-radius: 8px; 
            font-size: 1rem;
            transition: border-color 0.2s;
        }
        input[type="text"]:focus, textarea:focus { 
            outline: none; 
            border-color: #667eea; 
        }
        
        button { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            padding: 0.875rem 1.5rem; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-weight: 600; 
            width: 100%;
            font-size: 1rem;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover { 
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
        }
        button:active { transform: translateY(0); }
        
        .results { margin-top: 1.5rem; }
        .result-item { 
            background: #f9fafb; 
            padding: 1rem; 
            border-radius: 8px; 
            margin-bottom: 1rem;
            border-left: 4px solid #667eea;
        }
        .result-item .score { 
            color: #667eea; 
            font-weight: 600; 
            font-size: 0.875rem;
        }
        .result-item .source { 
            color: #6b7280; 
            font-size: 0.875rem; 
            margin: 0.25rem 0;
        }
        .result-item .content { 
            color: #374151; 
            margin-top: 0.5rem;
            line-height: 1.5;
        }
        .no-results { 
            text-align: center; 
            color: #6b7280; 
            padding: 2rem;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 OriginSteward</h1>
            <p>Your Personal Knowledge Companion</p>
        </div>
        
        <div class="card">
            <h2>🔍 Search Brain</h2>
            <div id="syncStatus" style="font-size: 0.8rem; color: #6b7280; margin-bottom: 1rem; text-align: right;"></div>
            <form id="searchForm" onsubmit="return handleSearch(event)">
                <input type="text" id="searchQuery" placeholder="Search your knowledge..." required>
                <button type="submit">Search</button>
            </form>
            <div id="searchResults" class="results"></div>
        </div>
    </div>
    
    <script>
        async function handleSearch(event) {
            event.preventDefault();
            const query = document.getElementById('searchQuery').value;
            const resultsDiv = document.getElementById('searchResults');
            const syncStatusDiv = document.getElementById('syncStatus');
            
            resultsDiv.innerHTML = '<div class="no-results">Searching...</div>';
            
            try {
                const response = await fetch('/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query })
                });
                
                const data = await response.json();
                
                if (data.last_updated) {
                    const date = new Date(data.last_updated * 1000);
                    syncStatusDiv.textContent = 'Last synced: ' + date.toLocaleString();
                }
                
                if (data.results && data.results.length > 0) {
                    resultsDiv.innerHTML = data.results.map(r => {
                        let sourceHtml = `<div class="source">${r.source}</div>`;
                        let actionHtml = '';
                        
                        // Check if source is a URL
                        if (r.source.startsWith('http')) {
                            sourceHtml = `<div class="source"><a href="${r.source}" target="_blank" style="color: #667eea; text-decoration: none; hover: underline;">${r.source}</a></div>`;
                            actionHtml = `
                                <div style="margin-top: 0.5rem;">
                                    <a href="${r.source}" target="_blank" style="
                                        display: inline-block;
                                        background: #f3f4f6;
                                        color: #374151;
                                        padding: 0.25rem 0.75rem;
                                        border-radius: 4px;
                                        text-decoration: none;
                                        font-size: 0.875rem;
                                        font-weight: 500;
                                        transition: background 0.2s;
                                    ">Open Link ↗</a>
                                </div>
                            `;
                        }
                        
                        return `
                        <div class="result-item">
                            <div style="display: flex; justify-content: space-between; align-items: baseline;">
                                <div class="score">Score: ${r.score.toFixed(3)}</div>
                                <div style="font-size: 0.75rem; color: #9ca3af;">${r.date}</div>
                            </div>
                            ${sourceHtml}
                            <div class="content">${r.content.substring(0, 300)}...</div>
                            ${actionHtml}
                        </div>
                    `}).join('');
                } else {
                    resultsDiv.innerHTML = '<div class="no-results">No results found</div>';
                }
            } catch (error) {
                resultsDiv.innerHTML = '<div class="no-results">Error: ' + error.message + '</div>';
            }
            
            return false;
        }
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/drop', methods=['POST'])
def drop():
    payload = request.form.get('payload')
    note = request.form.get('note')
    
    if not payload:
        return "Missing payload", 400
        
    # Determine type
    type_ = "url" if payload.startswith("http") else "text"
    
    data = {
        "type": type_,
        "payload": payload,
        "timestamp": time.time(),
        "note": note
    }
    
    # Save to Inbox
    os.makedirs(INBOX_DIR, exist_ok=True)
    filename = f"web_drop_{int(time.time())}.json"
    filepath = os.path.join(INBOX_DIR, filename)
    
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
        
    return jsonify({'success': True, 'id': filename})

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    query = data.get('query', '')
    
    if not query:
        return jsonify({'error': 'Missing query'}), 400
    
    # Search the brain
    results = brain.search(query, n_results=5)
    last_updated = brain.get_last_updated_at()
    
    # Format results
    formatted_results = []
    if results and results['documents']:
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        distances = results['distances'][0]
        
        for i, doc in enumerate(documents):
            meta = metadatas[i]
            formatted_results.append({
                'score': float(distances[i]),  # Convert numpy float32 to Python float
                'source': meta.get('source_url', 'Unknown'),
                'date': meta.get('created_at', 'Unknown'),
                'content': doc
            })
    
    return jsonify({
        'results': formatted_results,
        'last_updated': last_updated
    })

if __name__ == '__main__':
    os.makedirs(INBOX_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=5002)

