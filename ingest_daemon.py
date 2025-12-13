import time
import os
import shutil
import logging
import json
import jsonschema
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INBOX_DIR = os.path.join(BASE_DIR, 'Inbox')
ARCHIVE_DIR = os.path.join(BASE_DIR, 'Archive')
ERROR_DIR = os.path.join(BASE_DIR, 'Error')

# JSON Schema Definition
INPUT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "type": {"enum": ["url", "tweet", "text"]},
        "payload": {"type": "string"},
        "timestamp": {"type": "number"},
        "note": {"type": "string"}
    },
    "required": ["type", "payload", "timestamp"]
}

class IngestHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        try:
            from src.brain.vector_store import BrainDB
            self.brain = BrainDB()
        except Exception as e:
            logger.error(f"Failed to initialize BrainDB: {e}")
            self.brain = None

    def on_created(self, event):
        if event.is_directory:
            return
        
        # Ignore hidden files
        filename = os.path.basename(event.src_path)
        if filename.startswith('.'):
            return

        logger.info(f"New file detected: {filename}")
        time.sleep(1) # Debounce
        self.process_file(event.src_path)

    def process_file(self, filepath):
        filename = os.path.basename(filepath)
        try:
            # 1. Check if it's a JSON file
            if not filename.endswith('.json'):
                raise ValueError(f"Invalid file type: {filename}. Only .json allowed.")

            # 2. Read and Validate JSON
            with open(filepath, 'r') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    raise ValueError("Invalid JSON format")

            # 3. Validate Schema
            try:
                jsonschema.validate(instance=data, schema=INPUT_SCHEMA)
            except jsonschema.exceptions.ValidationError as e:
                raise ValueError(f"Schema Validation Failed: {e.message}")

            # 4. Dispatch to Connectors
            logger.info(f"Processing payload type: {data['type']}")
            
            processed_data = None
            
            if data['type'] == 'url':
                url = data['payload']
                if "twitter.com" in url or "x.com" in url:
                    from src.connectors.twitter_fetcher import fetch_tweet
                    processed_data = fetch_tweet(url)
                else:
                    from src.connectors.web_scraper import fetch_url_content
                    processed_data = fetch_url_content(url)
                    
            elif data['type'] == 'tweet':
                from src.connectors.twitter_fetcher import fetch_tweet
                processed_data = fetch_tweet(data['payload'])
                
            elif data['type'] == 'text':
                processed_data = {
                    "type": "note",
                    "content": data['payload'],
                    "created_at": datetime.now().isoformat(),
                    "tags": ["quick_capture"]
                }
            
            # 5. Save as Markdown Artifact & Index
            if processed_data:
                self.save_artifact(processed_data, filename)
                
            # 6. Archive Original JSON
            self.archive_file(filepath)
            
        except Exception as e:
            logger.error(f"Failed to process {filename}: {str(e)}")
            self.move_to_error(filepath, str(e))

    def save_artifact(self, data, original_filename):
        """Saves processed data as a Markdown file in Archive"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        target_dir = os.path.join(ARCHIVE_DIR, date_str)
        os.makedirs(target_dir, exist_ok=True)
        
        # Create filename from title or ID
        base_name = os.path.splitext(original_filename)[0]
        md_filename = f"{base_name}.md"
        target_path = os.path.join(target_dir, md_filename)
        
        # Frontmatter
        content = "---\n"
        metadata = {}
        for key, value in data.items():
            if key != "content":
                content += f"{key}: {json.dumps(value)}\n"
                metadata[key] = str(value) # Chroma metadata must be strings/ints
        content += "---\n\n"
        
        body_content = data.get("content", "")
        content += body_content
        
        with open(target_path, "w") as f:
            f.write(content)
        
        logger.info(f"Created Artifact: {target_path}")
        
        # Index in Brain
        if self.brain:
            try:
                self.brain.add_artifact(
                    content=body_content,
                    metadata=metadata,
                    artifact_id=base_name
                )
            except Exception as e:
                logger.error(f"Failed to index artifact: {e}")

    def archive_file(self, filepath):
        """Moves file to Archive/YYYY-MM-DD/"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        target_dir = os.path.join(ARCHIVE_DIR, date_str)
        os.makedirs(target_dir, exist_ok=True)
        
        filename = os.path.basename(filepath)
        target_path = os.path.join(target_dir, filename)
        
        if os.path.exists(target_path):
            name, ext = os.path.splitext(filename)
            timestamp = int(time.time())
            target_path = os.path.join(target_dir, f"{name}_{timestamp}{ext}")

        shutil.move(filepath, target_path)
        logger.info(f"Archived {filename} to {target_path}")

    def move_to_error(self, filepath, error_msg):
        """Moves file to Error/ and writes a log"""
        filename = os.path.basename(filepath)
        target_path = os.path.join(ERROR_DIR, filename)
        
        if os.path.exists(target_path):
             name, ext = os.path.splitext(filename)
             timestamp = int(time.time())
             target_path = os.path.join(ERROR_DIR, f"{name}_{timestamp}{ext}")

        shutil.move(filepath, target_path)
        
        # Write error log
        log_path = target_path + ".log"
        with open(log_path, "w") as f:
            f.write(f"Error processing {filename}:\n{error_msg}")
            
        logger.info(f"Moved {filename} to Error/")

def start_daemon():
    # Ensure directories exist
    for d in [INBOX_DIR, ARCHIVE_DIR, ERROR_DIR]:
        os.makedirs(d, exist_ok=True)

    event_handler = IngestHandler()
    observer = Observer()
    observer.schedule(event_handler, INBOX_DIR, recursive=False)
    observer.start()
    
    logger.info(f"OriginSteward Daemon watching: {INBOX_DIR}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_daemon()
