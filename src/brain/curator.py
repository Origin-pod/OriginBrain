import logging
import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import Counter
from src.db.db import BrainDB
from src.brain.content_analyzer import ContentAnalyzer

logger = logging.getLogger(__name__)

class Curator:
    def __init__(self):
        self.db = BrainDB()
        self.content_analyzer = ContentAnalyzer()
        self.vectorizer = TfidfVectorizer(
            max_features=100,
            stop_words='english',
            ngram_range=(1, 2)
        )

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

    def analyze_artifact(self, artifact_id: str) -> dict:
        """
        Analyze a single artifact and extract insights.

        Args:
            artifact_id: ID of the artifact to analyze

        Returns:
            Dictionary with analysis results
        """
        # Get artifact data
        artifacts = self.db.get_artifacts_with_extended(limit=None)
        artifact = next((a for a in artifacts if a['id'] == artifact_id), None)

        if not artifact:
            logger.error(f"Artifact {artifact_id} not found")
            return {}

        # Extract insights using content analyzer
        insights = self.content_analyzer.extract_insights(
            artifact['content'],
            artifact.get('metadata', {})
        )

        # Generate importance score based on various factors
        importance_score = self._calculate_importance_score(artifact, insights)

        # Update artifact with extended metadata
        self.db.upsert_artifact_extended(
            artifact_id,
            consumption_score=0.0,  # Will be updated based on user interaction
            importance_score=importance_score,
            consumption_status='unconsumed',
            estimated_read_time=insights.get('read_time_minutes', 0),
            auto_tags=insights['entities']['tech_terms'] + insights['entities']['business_terms'],
            entities=insights['entities'],
            insights={
                'sentiment': insights['sentiment'],
                'key_phrases': insights['key_phrases'][:10],
                'source_analysis': insights.get('source_analysis', {})
            },
            summary=insights.get('summary'),
            view_count=artifact.get('view_count', 0),
            engagement_score=0.0
        )

        return insights

    def _calculate_importance_score(self, artifact: dict, insights: dict) -> float:
        """
        Calculate importance score for an artifact.

        Args:
            artifact: Artifact data
            insights: Content analysis insights

        Returns:
            Importance score between 0 and 1
        """
        score = 0.5  # Base score

        # Factors that increase importance:

        # 1. Source authority
        source_analysis = insights.get('source_analysis', {})
        if source_analysis.get('authority_score'):
            score += source_analysis['authority_score'] * 0.2

        # 2. Content length (longer content often more valuable)
        word_count = insights.get('content_stats', {}).get('word_count', 0)
        if word_count > 500:
            score += 0.1
        elif word_count > 1000:
            score += 0.2

        # 3. Entity density (more entities = more informational)
        entities = insights.get('entities', {})
        entity_count = sum(len(v) for v in entities.values() if isinstance(v, list))
        if entity_count > 5:
            score += 0.1
        elif entity_count > 10:
            score += 0.2

        # 4. Has URLs (references to other content)
        if insights.get('content_stats', {}).get('has_urls'):
            score += 0.1

        # 5. Has numbers (data-driven content)
        if insights.get('content_stats', {}).get('has_numbers'):
            score += 0.1

        # 6. Key uniqueness (unique phrases)
        key_phrases = insights.get('key_phrases', [])
        if len(key_phrases) > 10:
            score += 0.1

        # Cap the score at 1.0
        return min(1.0, max(0.0, score))

    def find_similar_artifacts(self, artifact_id: str, limit: int = 5) -> list:
        """
        Find artifacts similar to the given artifact.

        Args:
            artifact_id: ID of the reference artifact
            limit: Maximum number of similar artifacts to return

        Returns:
            List of similar artifacts with similarity scores
        """
        # Get all artifacts with content
        artifacts = self.db.get_artifacts_with_extended(limit=None)

        # Find the target artifact
        target = next((a for a in artifacts if a['id'] == artifact_id), None)
        if not target:
            return []

        # Use existing vector store for similarity search
        from src.brain.vector_store import VectorStore
        vector_store = VectorStore()

        # Search for similar artifacts
        similar = vector_store.search(target['content'][:500], limit=limit)

        # Convert to artifact format with additional info
        results = []
        for item in similar:
            if item['id'] != artifact_id:  # Exclude self
                # Find full artifact data
                full_artifact = next((a for a in artifacts if a['id'] == item['id']), None)
                if full_artifact:
                    results.append({
                        **full_artifact,
                        'similarity_score': item['score']
                    })

        return results

    def update_artifact_relationships(self, artifact_id: str) -> int:
        """
        Update relationships for an artifact by finding similar and related content.

        Args:
            artifact_id: ID of the artifact to process

        Returns:
            Number of relationships created
        """
        # Find similar artifacts
        similar = self.find_similar_artifacts(artifact_id, limit=10)

        relationships_created = 0

        for similar_artifact in similar:
            # Only create relationship if similarity is above threshold
            if similar_artifact['similarity_score'] > 0.7:
                # Create bidirectional relationship
                rel_id = self.db.create_relationship(
                    artifact_id,
                    similar_artifact['id'],
                    'similar',
                    similar_artifact['similarity_score'],
                    f"Semantic similarity: {similar_artifact['similarity_score']:.2f}"
                )

                if rel_id:
                    relationships_created += 1

        return relationships_created

    def generate_consumption_queue(self, queue_type: str = 'daily', limit: int = 10) -> list:
        """
        Generate a personalized consumption queue.

        Args:
            queue_type: Type of queue (daily, weekly, priority, trending)
            limit: Maximum number of items

        Returns:
            List of artifacts for consumption
        """
        # Get all artifacts with extended metadata
        artifacts = self.db.get_artifacts_with_extended(limit=None)

        # Clear old queue items
        self.db.cleanup_expired_queue()

        scored_artifacts = []

        for artifact in artifacts:
            # Skip already consumed items for daily queue
            if queue_type == 'daily' and artifact.get('consumption_status') == 'applied':
                continue

            score = self._calculate_queue_score(artifact, queue_type)

            if score > 0:
                scored_artifacts.append({
                    **artifact,
                    'queue_score': score,
                    'queue_reason': self._get_queue_reason(artifact, score, queue_type)
                })

        # Sort by score
        scored_artifacts.sort(key=lambda x: x['queue_score'], reverse=True)

        # Add to queue
        for item in scored_artifacts[:limit]:
            self.db.add_to_consumption_queue(
                item['id'],
                queue_type,
                item['queue_score'],
                item['queue_reason'],
                expires_in_hours=24 if queue_type == 'daily' else 168  # 1 week for weekly
            )

        return scored_artifacts[:limit]

    def _calculate_queue_score(self, artifact: dict, queue_type: str) -> float:
        """
        Calculate score for queue placement.

        Args:
            artifact: Artifact data
            queue_type: Type of queue

        Returns:
            Score between 0 and 1
        """
        score = 0.0

        # Base importance
        importance = artifact.get('importance_score', 0.5)
        score += importance * 0.3

        # Recency factor
        from datetime import datetime, timedelta
        created_at = artifact.get('created_at')
        if created_at:
            days_old = (datetime.now() - created_at).days
            if days_old < 1:
                score += 0.3  # Very recent
            elif days_old < 7:
                score += 0.2  # Recent
            elif days_old < 30:
                score += 0.1  # Moderately recent

        # Consumption status
        status = artifact.get('consumption_status', 'unconsumed')
        if status == 'unconsumed':
            score += 0.3
        elif status == 'reading':
            score += 0.2

        # Engagement score
        engagement = artifact.get('engagement_score', 0)
        score += min(engagement / 10, 0.1)

        # Queue-specific adjustments
        if queue_type == 'priority':
            # Focus on high importance items
            score += importance * 0.5
        elif queue_type == 'trending':
            # Check if artifact has entities from current tech trends
            entities = artifact.get('entities', {})
            tech_terms = entities.get('tech_terms', [])
            trending_terms = ['AI', 'GPT', 'LLM', 'Transformer', 'React']
            if any(term in tech_terms for term in trending_terms):
                score += 0.2

        return min(1.0, score)

    def _get_queue_reason(self, artifact: dict, score: float, queue_type: str) -> str:
        """
        Generate a human-readable reason for queue inclusion.

        Args:
            artifact: Artifact data
            score: Calculated score
            queue_type: Type of queue

        Returns:
            Reason string
        """
        reasons = []

        if artifact.get('importance_score', 0) > 0.7:
            reasons.append("High importance")

        from datetime import datetime, timedelta
        created_at = artifact.get('created_at')
        if created_at and (datetime.now() - created_at).days < 1:
            reasons.append("Recently captured")

        entities = artifact.get('entities', {})
        if entities.get('tech_terms'):
            reasons.append(f"Tech topics: {', '.join(entities['tech_terms'][:3])}")

        if artifact.get('consumption_status') == 'unconsumed':
            reasons.append("Not yet reviewed")

        return "; ".join(reasons) if reasons else "Recommended for review"

    def process_all_artifacts(self) -> dict:
        """
        Process all artifacts that haven't been analyzed yet.

        Returns:
            Statistics about processing results
        """
        # Get artifacts that don't have extended metadata yet
        all_artifacts = self.db.get_artifacts_with_extended()
        unprocessed = [a for a in all_artifacts if a.get('consumption_score') is None]

        stats = {
            'total': len(all_artifacts),
            'unprocessed': len(unprocessed),
            'processed': 0,
            'errors': 0
        }

        logger.info(f"Processing {len(unprocessed)} unprocessed artifacts...")

        for artifact in unprocessed:
            try:
                # Analyze artifact
                self.analyze_artifact(artifact['id'])

                # Update relationships
                relationships = self.update_artifact_relationships(artifact['id'])

                stats['processed'] += 1
                logger.info(f"Processed {artifact['title'][:50]}... (created {relationships} relationships)")

            except Exception as e:
                stats['errors'] += 1
                logger.error(f"Failed to process artifact {artifact['id']}: {e}")

        return stats
