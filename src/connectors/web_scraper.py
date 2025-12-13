import requests
from readability import Document
from markdownify import markdownify as md
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def fetch_url_content(url):
    """
    Fetches a URL and converts it to Markdown.
    Returns a dictionary with metadata and content.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        doc = Document(response.text)
        title = doc.title()
        html_content = doc.summary()
        
        # Convert to Markdown
        markdown_content = md(html_content, heading_style="ATX")
        
        return {
            "type": "article",
            "source_url": url,
            "title": title,
            "content": markdown_content,
            "created_at": datetime.now().isoformat(),
            "tags": ["web_capture"]
        }
        
    except Exception as e:
        logger.error(f"Error fetching URL {url}: {str(e)}")
        raise e
