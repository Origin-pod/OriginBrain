import os
import json
import time
from flask import Flask, request, render_template_string

app = Flask(__name__)
INBOX_DIR = os.path.abspath("Inbox")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>OriginSteward Drop Zone</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, system-ui, sans-serif; max-width: 600px; margin: 2rem auto; padding: 1rem; background: #f4f4f5; }
        .card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        input[type="text"], textarea { width: 100%; padding: 0.75rem; margin-bottom: 1rem; border: 1px solid #e4e4e7; border-radius: 6px; box-sizing: border-box; }
        button { background: #18181b; color: white; padding: 0.75rem 1.5rem; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; width: 100%; }
        button:hover { background: #27272a; }
        .success { color: #16a34a; margin-top: 1rem; text-align: center; }
        h1 { margin-top: 0; font-size: 1.5rem; color: #18181b; }
    </style>
</head>
<body>
    <div class="card">
        <h1>OriginSteward Drop</h1>
        <form method="POST" action="/drop">
            <input type="text" name="payload" placeholder="Paste URL here..." required autofocus>
            <textarea name="note" placeholder="Optional note..." rows="3"></textarea>
            <button type="submit">Drop to Brain</button>
        </form>
        {% if success %}
            <div class="success">✓ Saved to Inbox</div>
        {% endif %}
    </div>
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
    filename = f"web_drop_{int(time.time())}.json"
    filepath = os.path.join(INBOX_DIR, filename)
    
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
        
    return render_template_string(HTML_TEMPLATE, success=True)

if __name__ == '__main__':
    os.makedirs(INBOX_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=5000)
