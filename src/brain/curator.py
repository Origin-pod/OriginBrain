import logging
import numpy as np
from sklearn.cluster import KMeans
from collections import Counter
from src.db.db import BrainDB

logger = logging.getLogger(__name__)

class Curator:
    def __init__(self):
        self.db = BrainDB()

    def get_themes(self, n_clusters=5):
        """
        Clusters artifacts into themes based on their embeddings.
        Returns a list of themes with labels and artifact counts.
        """
        try:
            # 1. Fetch all embeddings
            rows = self.db.get_all_embeddings()
            if not rows or len(rows) < n_clusters:
                return []

            ids = [row['artifact_id'] for row in rows]
            vectors = np.array([row['vector'] for row in rows])
            metadatas = [row['metadata'] for row in rows]
            
            # 2. Perform K-Means Clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(vectors)
            
            # 3. Group by Cluster
            clusters = {}
            for i, label in enumerate(labels):
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(metadatas[i])
            
            # 4. Generate Theme Labels
            themes = []
            for label, items in clusters.items():
                theme_name = self._generate_label(items)
                themes.append({
                    "id": int(label),
                    "name": theme_name,
                    "count": len(items),
                    "sample_titles": [item.get('title', 'Untitled') for item in items[:3]]
                })
                
            # Sort by count
            themes.sort(key=lambda x: x['count'], reverse=True)
            return themes

        except Exception as e:
            logger.error(f"Failed to generate themes: {e}")
            return []

    def _generate_label(self, items):
        """
        Generates a label for a cluster based on frequent tags or words.
        """
        # 1. Try Tags first
        all_tags = []
        for item in items:
            tags = item.get('tags', [])
            if isinstance(tags, list):
                all_tags.extend(tags)
        
        if all_tags:
            most_common = Counter(all_tags).most_common(1)
            if most_common:
                return most_common[0][0].title()
        
        # 2. Fallback to Source Domain
        domains = []
        for item in items:
            url = item.get('source_url', '')
            if '://' in url:
                domain = url.split('://')[1].split('/')[0].replace('www.', '')
                domains.append(domain)
        
        if domains:
            most_common = Counter(domains).most_common(1)
            if most_common:
                return f"From {most_common[0][0]}"
                
        return "Miscellaneous"
