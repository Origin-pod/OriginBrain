import time
import logging
import json
from datetime import datetime
from src.db.db import BrainDB as PostgresDB

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class IngestDaemon:
    def __init__(self):
        self.db = PostgresDB()
        try:
            from src.brain.vector_store import BrainDB
            self.brain = BrainDB()
        except Exception as e:
            logger.error(f"Failed to initialize BrainDB: {e}")
            self.brain = None

    def run(self):
        logger.info("OriginSteward Daemon started (DB Polling Mode)")
        while True:
            try:
                pending_drops = self.db.get_pending_drops()
                if pending_drops:
                    logger.info(f"Found {len(pending_drops)} pending drops")
                    for drop in pending_drops:
                        self.process_drop(drop)
                else:
                    time.sleep(1) # Poll interval
            except Exception as e:
                logger.error(f"Daemon loop error: {e}")
                time.sleep(5)

    def process_drop(self, drop):
        drop_id = drop['id']
        type_ = drop['type']
        payload = drop['payload']
        
        logger.info(f"Processing drop {drop_id} ({type_})")
        
        try:
            # Update status to processing
            self.db.update_drop_status(drop_id, 'processing')
            
            processed_data = None
            
            if type_ == 'url':
                if "twitter.com" in payload or "x.com" in payload:
                    from src.connectors.twitter_fetcher import fetch_tweet
                    processed_data = fetch_tweet(payload)
                else:
                    from src.connectors.web_scraper import fetch_url_content
                    processed_data = fetch_url_content(payload)
                    
            elif type_ == 'tweet':
                from src.connectors.twitter_fetcher import fetch_tweet
                processed_data = fetch_tweet(payload)
                
            elif type_ == 'text':
                processed_data = {
                    "type": "note",
                    "content": payload,
                    "created_at": datetime.now().isoformat(),
                    "tags": ["quick_capture"]
                }
            
            if processed_data:
                # Save Artifact
                title = processed_data.get('source_url', 'Untitled')
                content = processed_data.get('content', '')
                metadata = processed_data
                
                artifact_id = self.db.insert_artifact(drop_id, title, content, metadata)
                logger.info(f"Created Artifact: {artifact_id}")

                # Index in Brain
                if self.brain:
                    self.brain.add_artifact(content, metadata, artifact_id)

                # Initialize extended metadata for consumption tracking
                self.db.upsert_artifact_extended(
                    artifact_id,
                    consumption_score=0.0,
                    importance_score=0.5,  # Default score, will be updated by curator
                    consumption_status='unconsumed',
                    view_count=0,
                    engagement_score=0.0
                )
                logger.info(f"Initialized consumption tracking for {artifact_id}")

                # Mark completed
                self.db.update_drop_status(drop_id, 'completed')
            else:
                self.db.update_drop_status(drop_id, 'failed', "No data processed")
                
        except Exception as e:
            logger.error(f"Failed to process drop {drop_id}: {e}")
            self.db.update_drop_status(drop_id, 'failed', str(e))

if __name__ == "__main__":
    daemon = IngestDaemon()
    daemon.run()
