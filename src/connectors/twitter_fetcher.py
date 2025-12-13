import json
import subprocess
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def fetch_tweet(url):
    """
    Fetches Tweet content using yt-dlp.
    Returns a dictionary with metadata and content.
    """
    try:
        # specific args to get metadata without downloading video
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--skip-download",
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        # Extract relevant fields
        # yt-dlp maps tweet text to 'description' or 'title'
        content = data.get('description') or data.get('title') or ""
        author = data.get('uploader') or data.get('uploader_id') or "unknown"
        upload_date = data.get('upload_date') # YYYYMMDD
        
        return {
            "type": "tweet",
            "source_url": url,
            "author": author,
            "content": content,
            "created_at": datetime.now().isoformat(),
            "tweet_date": upload_date,
            "tags": ["twitter", "capture"]
        }

    except subprocess.CalledProcessError as e:
        logger.error(f"yt-dlp failed for {url}: {e.stderr}")
        raise Exception(f"Failed to fetch tweet: {e.stderr}")
    except Exception as e:
        logger.error(f"Error processing tweet {url}: {str(e)}")
        raise e
