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
        # Use yt-dlp from the same environment
        import sys
        import os
        venv_bin = os.path.dirname(sys.executable)
        ytdlp_path = os.path.join(venv_bin, "yt-dlp")
        
        cmd = [
            ytdlp_path,
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
        
        # Fallback: Try oEmbed to get HTML content
        try:
            import requests
            oembed_url = f"https://publish.twitter.com/oembed?url={url}"
            response = requests.get(oembed_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                html = data.get('html', '')
                author_name = data.get('author_name', 'unknown')
                
                return {
                    "type": "tweet",
                    "source_url": url,
                    "author": author_name,
                    "content": html, # Store the embed HTML
                    "created_at": datetime.now().isoformat(),
                    "tags": ["twitter", "capture", "oembed"]
                }
        except Exception as oembed_error:
            logger.error(f"oEmbed fallback failed: {oembed_error}")

        # Final Fallback
        return {
            "type": "tweet",
            "source_url": url,
            "author": "unknown",
            "content": f"Failed to fetch tweet content. URL: {url}",
            "created_at": datetime.now().isoformat(),
            "tags": ["twitter", "capture", "failed_fetch"]
        }
    except Exception as e:
        logger.error(f"Error processing tweet {url}: {str(e)}")
        # Fallback for generic errors
        return {
            "type": "tweet",
            "source_url": url,
            "author": "unknown",
            "content": f"Error processing tweet. URL: {url}",
            "created_at": datetime.now().isoformat(),
            "tags": ["twitter", "capture", "error"]
        }
