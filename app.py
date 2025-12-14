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
        
        // Poll for status updates
        function pollStatus() {
            fetch('/status?t=' + new Date().getTime())
                .then(response => response.json())
                .then(data => {
                    const syncStatusDiv = document.getElementById('syncStatus');
                    if (data.last_updated) {
                        const date = new Date(data.last_updated * 1000);
                        syncStatusDiv.textContent = 'Last synced: ' + date.toLocaleString() + ' (' + data.doc_count + ' items)';
                    }
                })
                .catch(console.error);
        }
        
        // Poll every 2 seconds
        setInterval(pollStatus, 2000);
        pollStatus(); // Initial call
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
    
    # Save to DB
    try:
        from src.db.db import BrainDB as PostgresDB
        db = PostgresDB()
        drop_id = db.insert_drop(type_, payload, note)
        db.close()
        return jsonify({'success': True, 'id': drop_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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

@app.route('/status', methods=['GET'])
def status():
    # Check for updates to ensure we have the latest stats
    brain._check_for_updates()
    return jsonify({
        'last_updated': brain.get_last_updated_at(),
        'doc_count': len(brain.documents)
    })

# --- API Routes for React Frontend ---

@app.route('/api/stats', methods=['GET'])
def api_stats():
    try:
        from src.db.db import BrainDB as PostgresDB
        db = PostgresDB()
        
        # Get daily stats
        daily_stats = db.get_daily_stats(days=30)
        
        # Get total count
        total_count = db.get_artifact_count()
        
        db.close()
        
        return jsonify({
            'total_count': total_count,
            'daily_activity': daily_stats,
            'last_updated': brain.get_last_updated_at()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recent', methods=['GET'])
def api_recent():
    try:
        from src.db.db import BrainDB as PostgresDB
        db = PostgresDB()
        recent = db.get_recent_artifacts(limit=20)
        db.close()
        return jsonify({'results': recent})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/themes', methods=['GET'])
def api_themes():
    try:
        from src.brain.curator import Curator
        curator = Curator()
        themes = curator.get_themes(n_clusters=5)
        return jsonify({'themes': themes})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/resurface', methods=['GET'])
def api_resurface():
    try:
        from src.db.db import BrainDB as PostgresDB
        db = PostgresDB()
        # Get 3 random items to resurface
        random_items = db.get_random_artifacts(limit=3)
        db.close()
        return jsonify({'results': random_items})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- New API Routes for Insights & Curation ---

@app.route('/api/consumption/track', methods=['POST'])
def api_track_consumption():
    """Track a consumption event for an artifact"""
    try:
        from src.db.db import BrainDB as PostgresDB

        data = request.get_json()
        artifact_id = data.get('artifact_id')
        event_type = data.get('event_type', 'view')

        if not artifact_id:
            return jsonify({'error': 'Missing artifact_id'}), 400

        db = PostgresDB()

        # Track the consumption event
        event_id = db.track_consumption_event(
            artifact_id=artifact_id,
            event_type=event_type,
            duration_seconds=data.get('duration_seconds'),
            engagement_score=data.get('engagement_score'),
            scroll_depth=data.get('scroll_depth'),
            session_id=data.get('session_id'),
            source=data.get('source', 'dashboard'),
            metadata=data.get('metadata', {})
        )

        db.close()

        return jsonify({
            'success': True,
            'event_id': event_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/consumption/queue', methods=['GET'])
def api_consumption_queue():
    """Get personalized consumption queue"""
    try:
        from src.db.db import BrainDB as PostgresDB
        from src.brain.curator import Curator

        queue_type = request.args.get('type', 'daily')
        limit = int(request.args.get('limit', 10))

        # Generate fresh queue
        curator = Curator()
        queue_items = curator.generate_consumption_queue(queue_type, limit)

        # Also get existing queue items
        db = PostgresDB()
        db_queue = db.get_consumption_queue(queue_type, limit)
        db.close()

        return jsonify({
            'queue': queue_items,
            'existing_queue': db_queue,
            'queue_type': queue_type
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/relationships/detect', methods=['POST'])
def api_detect_relationships():
    """Find and create relationships for an artifact"""
    try:
        from src.brain.curator import Curator

        data = request.get_json()
        artifact_id = data.get('artifact_id')

        if not artifact_id:
            return jsonify({'error': 'Missing artifact_id'}), 400

        curator = Curator()
        relationships_created = curator.update_artifact_relationships(artifact_id)

        return jsonify({
            'success': True,
            'relationships_created': relationships_created
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/artifacts/<artifact_id>/extended', methods=['GET'])
def api_artifact_extended(artifact_id):
    """Get artifact with extended metadata and insights"""
    try:
        from src.db.db import BrainDB as PostgresDB

        db = PostgresDB()

        # Get artifact with extended metadata
        artifact = db.get_artifact_extended(artifact_id)

        if not artifact:
            return jsonify({'error': 'Artifact not found'}), 404

        # Get relationships
        relationships = db.get_artifact_relationships(artifact_id)

        # Get consumption events
        consumption_events = db.get_consumption_events(artifact_id, limit=10)

        db.close()

        return jsonify({
            'artifact': artifact,
            'relationships': relationships,
            'consumption_events': consumption_events
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/insights/basic', methods=['POST'])
def api_basic_insights():
    """Get basic insights for an artifact (creates them if needed)"""
    try:
        from src.brain.curator import Curator

        data = request.get_json()
        artifact_id = data.get('artifact_id')

        if not artifact_id:
            return jsonify({'error': 'Missing artifact_id'}), 400

        curator = Curator()
        insights = curator.analyze_artifact(artifact_id)

        return jsonify({
            'success': True,
            'insights': insights
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/goals', methods=['GET', 'POST'])
def api_goals():
    """Manage user goals"""
    try:
        from src.db.db import BrainDB as PostgresDB

        db = PostgresDB()

        if request.method == 'GET':
            goals = db.get_active_goals()
            return jsonify({'goals': goals})

        elif request.method == 'POST':
            data = request.get_json()
            goal_id = db.create_goal(
                goal=data.get('goal'),
                description=data.get('description'),
                priority=data.get('priority', 5),
                tags=data.get('tags', []),
                related_topics=data.get('related_topics', [])
            )
            db.close()
            return jsonify({'success': True, 'goal_id': goal_id})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/process-all', methods=['POST'])
def api_process_all_artifacts():
    """Process all unprocessed artifacts with insights"""
    try:
        from src.brain.curator import Curator

        curator = Curator()
        stats = curator.process_all_artifacts()

        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- New API Routes for Milestone 2: Intelligence Layer ---

@app.route('/api/insights/personalized', methods=['GET'])
def api_personalized_insights():
    """Get personalized insights for the user"""
    try:
        from src.brain.insights_engine import InsightsEngine

        engine = InsightsEngine()
        insights = engine.generate_personalized_insights()

        return jsonify({
            'success': True,
            'insights': insights
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/insights/trends', methods=['GET'])
def api_trends():
    """Get trending topics in user's knowledge base"""
    try:
        from src.brain.insights_engine import InsightsEngine

        days = int(request.args.get('days', 30))
        engine = InsightsEngine()
        trends = engine.detect_trends(days)

        return jsonify({
            'success': True,
            'trends': trends
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/insights/knowledge-gaps', methods=['GET'])
def api_knowledge_gaps():
    """Get identified knowledge gaps"""
    try:
        from src.brain.insights_engine import InsightsEngine

        engine = InsightsEngine()
        gaps = engine.identify_knowledge_gaps()

        return jsonify({
            'success': True,
            'gaps': gaps
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/insights/consumption-patterns', methods=['GET'])
def api_consumption_patterns():
    """Get user's consumption patterns analysis"""
    try:
        from src.brain.insights_engine import InsightsEngine

        engine = InsightsEngine()
        patterns = engine.analyze_consumption_patterns()

        return jsonify({
            'success': True,
            'patterns': patterns
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/insights/entity-network', methods=['GET'])
def api_entity_network():
    """Get entity network visualization data"""
    try:
        from src.brain.insights_engine import InsightsEngine

        engine = InsightsEngine()
        network = engine.build_entity_network()

        return jsonify({
            'success': True,
            'network': network
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recommendations/personalized', methods=['GET'])
def api_personalized_recommendations():
    """Get personalized recommendations"""
    try:
        from src.brain.recommendation_engine import RecommendationEngine

        limit = int(request.args.get('limit', 10))
        engine = RecommendationEngine()
        recommendations = engine.get_personalized_queue(limit=limit)

        return jsonify({
            'success': True,
            'recommendations': recommendations
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recommendations/similar', methods=['GET'])
def api_similar_recommendations():
    """Get recommendations based on consumed content"""
    try:
        from src.brain.recommendation_engine import RecommendationEngine

        limit = int(request.args.get('limit', 5))
        engine = RecommendationEngine()
        recommendations = engine.get_similar_to_consumed(limit)

        return jsonify({
            'success': True,
            'recommendations': recommendations
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recommendations/goal-focused', methods=['POST'])
def api_goal_focused_recommendations():
    """Get recommendations aligned with specific goal"""
    try:
        from src.brain.recommendation_engine import RecommendationEngine

        data = request.get_json()
        goal_id = data.get('goal_id')
        limit = data.get('limit', 5)

        if not goal_id:
            return jsonify({'error': 'Missing goal_id'}), 400

        engine = RecommendationEngine()
        recommendations = engine.get_goal_focused_recommendations(goal_id, limit)

        return jsonify({
            'success': True,
            'recommendations': recommendations
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recommendations/discover', methods=['GET'])
def api_discover_topics():
    """Discover new and emerging topics"""
    try:
        from src.brain.recommendation_engine import RecommendationEngine

        limit = int(request.args.get('limit', 5))
        engine = RecommendationEngine()
        discoveries = engine.discover_new_topics(limit)

        return jsonify({
            'success': True,
            'discoveries': discoveries
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/relationships/discover-all', methods=['POST'])
def api_discover_all_relationships():
    """Discover all types of relationships for artifacts"""
    try:
        from src.brain.relationship_mapper import RelationshipMapper

        data = request.get_json()
        artifact_id = data.get('artifact_id')  # Optional: process specific artifact

        mapper = RelationshipMapper()
        stats = mapper.discover_all_relationships(artifact_id)

        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/relationships/knowledge-graph', methods=['GET'])
def api_knowledge_graph():
    """Get complete knowledge graph data"""
    try:
        from src.brain.relationship_mapper import RelationshipMapper

        mapper = RelationshipMapper()
        graph = mapper.build_knowledge_graph()

        return jsonify({
            'success': True,
            'graph': graph
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/dashboard', methods=['GET'])
def api_dashboard_analytics():
    """Get comprehensive dashboard analytics"""
    try:
        from src.db.db import BrainDB
        from src.brain.insights_engine import InsightsEngine

        db = BrainDB()
        engine = InsightsEngine()

        # Basic stats
        total_artifacts = db.get_artifact_count()

        # Consumption stats
        artifacts = db.get_artifacts_with_extended()
        consumption_stats = {
            'unconsumed': sum(1 for a in artifacts if a.get('consumption_status') == 'unconsumed'),
            'reading': sum(1 for a in artifacts if a.get('consumption_status') == 'reading'),
            'reviewed': sum(1 for a in artifacts if a.get('consumption_status') == 'reviewed'),
            'applied': sum(1 for a in artifacts if a.get('consumption_status') == 'applied')
        }

        # Trending topics
        trends = engine.detect_trends(days=7)[:5]  # Top 5 from last week

        # Recent queue
        queue = db.get_consumption_queue('daily', limit=5)

        return jsonify({
            'success': True,
            'analytics': {
                'total_artifacts': total_artifacts,
                'consumption_stats': consumption_stats,
                'trending_topics': trends,
                'queue_items': queue,
                'consumption_rate': consumption_stats['applied'] / total_artifacts if total_artifacts > 0 else 0
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- New API Routes for Milestone 4: Optimization & Polish ---

@app.route('/api/ai/summarize', methods=['POST'])
def api_summarize_artifact():
    """Generate AI-powered summary for an artifact"""
    try:
        from src.brain.summarizer import AISummarizer

        data = request.get_json()
        artifact_id = data.get('artifact_id')
        summary_type = data.get('type', 'short')

        if not artifact_id:
            return jsonify({'error': 'Missing artifact_id'}), 400

        summarizer = AISummarizer()
        result = summarizer.generate_summary(artifact_id, summary_type)

        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/ask', methods=['POST'])
def api_ask_question():
    """Ask a question and get AI-powered answer from knowledge base"""
    try:
        from src.brain.summarizer import AISummarizer

        data = request.get_json()
        question = data.get('question')
        artifact_id = data.get('artifact_id')  # Optional: search specific artifact

        if not question:
            return jsonify({'error': 'Missing question'}), 400

        summarizer = AISummarizer()
        result = summarizer.answer_question(question, artifact_id)

        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/insights-report', methods=['GET'])
def api_insights_report():
    """Generate comprehensive insights report"""
    try:
        from src.brain.summarizer import AISummarizer

        limit = int(request.args.get('limit', 20))
        summarizer = AISummarizer()
        report = summarizer.generate_insights_report(limit)

        return jsonify({
            'success': True,
            'report': report
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/artifacts', methods=['POST'])
def api_export_artifacts():
    """Export artifacts in specified format"""
    try:
        from src.brain.export_service import ExportService

        data = request.get_json()
        format_type = data.get('format', 'json')
        artifact_ids = data.get('artifact_ids', [])
        filters = data.get('filters', {})

        export_service = ExportService()
        result = export_service.export_artifacts(format_type, artifact_ids, filters)

        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/knowledge-graph', methods=['POST'])
def api_export_knowledge_graph():
    """Export knowledge graph data"""
    try:
        from src.brain.export_service import ExportService

        data = request.get_json()
        format_type = data.get('format', 'json')

        export_service = ExportService()
        result = export_service.export_knowledge_graph(format_type)

        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Accelerated Search Endpoints ---

# Initialize accelerated search service
from src.brain.accelerated_search import AcceleratedSearch
accelerated_search = AcceleratedSearch()

@app.route('/api/search/rebuild-index', methods=['POST'])
def api_rebuild_search_index():
    """Rebuild the accelerated search index"""
    try:
        data = request.get_json()
        force = data.get('force', False)

        result = accelerated_search.rebuild_index(force=force)

        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/similar', methods=['POST'])
def api_search_similar():
    """Search for similar artifacts using accelerated vector search"""
    try:
        data = request.get_json()
        query_embedding = data.get('embedding')
        k = data.get('k', 10)
        filters = data.get('filters', {})

        if not query_embedding:
            return jsonify({'error': 'Query embedding is required'}), 400

        results = accelerated_search.search_similar(query_embedding, k, filters)

        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/hybrid', methods=['POST'])
def api_search_hybrid():
    """Hybrid search combining text and vector similarity"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        query_embedding = data.get('embedding')
        k = data.get('k', 10)
        text_weight = data.get('text_weight', 0.3)
        vector_weight = data.get('vector_weight', 0.7)
        filters = data.get('filters', {})

        if not query_embedding:
            return jsonify({'error': 'Query embedding is required'}), 400

        results = accelerated_search.search_hybrid(
            query, query_embedding, k, text_weight, vector_weight, filters
        )

        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/recommendations/<artifact_id>', methods=['GET'])
def api_get_recommendations(artifact_id):
    """Get artifact recommendations based on similarity"""
    try:
        k = request.args.get('k', 5, type=int)
        exclude_consumed = request.args.get('exclude_consumed', 'true').lower() == 'true'

        recommendations = accelerated_search.recommend_similar_artifacts(
            artifact_id, k, exclude_consumed
        )

        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'count': len(recommendations)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/stats', methods=['GET'])
def api_search_stats():
    """Get search index statistics"""
    try:
        stats = accelerated_search.get_index_stats()

        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/optimize', methods=['POST'])
def api_optimize_search_index():
    """Optimize the search index for better performance"""
    try:
        result = accelerated_search.optimize_index()

        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    os.makedirs(INBOX_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=5002)

