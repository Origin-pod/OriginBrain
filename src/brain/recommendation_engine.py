"""
Personalized Recommendation Engine for OriginBrain.
Provides intelligent content recommendations based on user behavior and preferences.
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict
from src.db.db import BrainDB
from src.brain.vector_store import BrainDB as VectorStore

logger = logging.getLogger(__name__)

class RecommendationEngine:
    """Generates personalized recommendations for content consumption."""

    def __init__(self):
        self.db = BrainDB()
        self.vector_store = VectorStore()
        self.user_model = UserBehaviorModel()

    def get_personalized_queue(self, user_context: Dict = None, limit: int = 10) -> List[Dict]:
        """
        Get a personalized consumption queue for the user.

        Args:
            user_context: User's current goals and preferences
            limit: Maximum number of recommendations

        Returns:
            List of recommended artifacts with scores and reasons
        """
        # Get all artifacts
        artifacts = self.db.get_artifacts_with_extended(limit=None)

        # Score each artifact
        scored_artifacts = []
        for artifact in artifacts:
            score = self._calculate_recommendation_score(artifact, user_context)
            if score > 0:
                scored_artifacts.append({
                    **artifact,
                    'recommendation_score': score,
                    'reasons': self._generate_reasons(artifact, score)
                })

        # Sort by score
        scored_artifacts.sort(key=lambda x: x['recommendation_score'], reverse=True)

        # Add to consumption queue
        for item in scored_artifacts[:limit]:
            self.db.add_to_consumption_queue(
                item['id'],
                'personalized',
                item['recommendation_score'],
                '; '.join(item['reasons']),
                expires_in_hours=24
            )

        return scored_artifacts[:limit]

    def get_similar_to_consumed(self, limit: int = 5) -> List[Dict]:
        """
        Get recommendations based on content similar to what user has consumed.

        Args:
            limit: Maximum number of recommendations

        Returns:
            List of similar artifacts
        """
        # Get consumed artifacts
        consumed = self.db.get_artifacts_with_extended(consumption_status='reviewed')

        if not consumed:
            return []

        # Find similar artifacts to consumed content
        similar_artifacts = defaultdict(float)

        for consumed_artifact in consumed[:10]:  # Use last 10 consumed artifacts
            similar = self._find_similar_artifacts(consumed_artifact['id'], limit=3)
            for similar_item in similar:
                if similar_item['similarity_score'] > 0.6:
                    similar_artifacts[similar_item['id']] = max(
                        similar_artifacts[similar_item['id']],
                        similar_item['similarity_score'] * 0.8  # Slightly lower score
                    )

        # Get full artifact data for similar items
        recommendations = []
        for artifact_id, score in similar_artifacts.items():
            artifact = next((a for a in self.db.get_artifacts_with_extended() if a['id'] == artifact_id), None)
            if artifact:
                recommendations.append({
                    **artifact,
                    'recommendation_score': score,
                    'reason': ['Similar to content you\'ve recently consumed']
                })

        # Sort by score and limit
        recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        return recommendations[:limit]

    def get_goal_focused_recommendations(self, goal_id: str, limit: int = 5) -> List[Dict]:
        """
        Get recommendations aligned with a specific goal.

        Args:
            goal_id: ID of the goal
            limit: Maximum number of recommendations

        Returns:
            List of goal-aligned recommendations
        """
        # Get goal details
        goals = self.db.get_active_goals()
        goal = next((g for g in goals if g['id'] == goal_id), None)

        if not goal:
            return []

        # Get goal topics and keywords
        goal_text = goal['goal'].lower()
        goal_description = goal.get('description', '').lower()
        related_topics = [t.lower() for t in goal.get('related_topics', [])]

        # Search for relevant artifacts
        all_artifacts = self.db.get_artifacts_with_extended(limit=None)
        relevant = []

        for artifact in all_artifacts:
            # Skip already consumed
            if artifact.get('consumption_status') == 'applied':
                continue

            score = 0
            reasons = []

            # Check content relevance
            content_lower = artifact['content'].lower()

            # Direct keyword matching
            if goal_text in content_lower:
                score += 0.5
                reasons.append("Directly relevant to your goal")

            # Related topics
            topic_matches = sum(1 for topic in related_topics if topic in content_lower)
            if topic_matches > 0:
                score += topic_matches * 0.3
                reasons.append(f"Matches {topic_matches} of your goal topics")

            # Entity matching
            entities = artifact.get('entities', {})
            entity_text = ' '.join([' '.join(e) if isinstance(e, list) else str(e)
                                   for e in entities.values() if e]).lower()

            for topic in related_topics:
                if topic in entity_text:
                    score += 0.2
                    reasons.append(f"Contains relevant entity: {topic}")

            # High importance bonus
            if artifact.get('importance_score', 0) > 0.7:
                score += 0.1
                reasons.append("High importance content")

            if score > 0.3:
                relevant.append({
                    **artifact,
                    'recommendation_score': min(score, 1.0),
                    'reasons': reasons,
                    'goal_alignment': score
                })

        # Sort by goal alignment
        relevant.sort(key=lambda x: x['goal_alignment'], reverse=True)

        return relevant[:limit]

    def discover_new_topics(self, limit: int = 5) -> List[Dict]:
        """
        Discover emerging topics the user might be interested in.

        Args:
            limit: Maximum number of discoveries

        Returns:
            List of topic discoveries with artifact recommendations
        """
        # Get recent artifacts
        artifacts = self.db.get_artifacts_with_extended(limit=None)
        recent_cutoff = datetime.now() - timedelta(days=14)
        recent = [
            a for a in artifacts
            if a.get('created_at') and a['created_at'].replace(tzinfo=None) > recent_cutoff
        ]

        # Identify entities in recent content
        recent_entities = defaultdict(list)
        user_entities = set()

        # Get entities from user's consumed content
        consumed = self.db.get_artifacts_with_extended(consumption_status='reviewed')
        for artifact in consumed:
            entities = artifact.get('entities', {})
            for entity_list in entities.values():
                if isinstance(entity_list, list):
                    user_entities.update(entity_list)

        # Find new entities in recent content
        for artifact in recent:
            entities = artifact.get('entities', {})
            for entity_type, entity_list in entities.items():
                if isinstance(entity_list, list):
                    for entity in entity_list:
                        if entity not in user_entities:
                            recent_entities[entity].append({
                                'artifact_id': artifact['id'],
                                'type': entity_type,
                                'title': artifact.get('title', ''),
                                'importance': artifact.get('importance_score', 0)
                            })

        # Filter and score new topics
        new_topics = []
        for entity, occurrences in recent_entities.items():
            if len(occurrences) >= 2:  # Appears in multiple recent artifacts
                avg_importance = sum(o['importance'] for o in occurrences) / len(occurrences)
                diversity = len(set(o['type'] for o in occurrences))

                score = (len(occurrences) * 0.3 + avg_importance * 0.4 + diversity * 0.3)

                # Get best artifact representing this topic
                best_artifact = max(occurrences, key=lambda x: x['importance'])

                new_topics.append({
                    'topic': entity,
                    'score': min(score, 1.0),
                    'occurrences': len(occurrences),
                    'types': list(set(o['type'] for o in occurrences)),
                    'recommendation_artifact_id': best_artifact['artifact_id'],
                    'recommendation_artifact_title': best_artifact['title'],
                    'reason': f"New emerging topic you haven't explored yet"
                })

        # Sort by score
        new_topics.sort(key=lambda x: x['score'], reverse=True)

        return new_topics[:limit]

    def _calculate_recommendation_score(self, artifact: Dict, user_context: Dict = None) -> float:
        """Calculate overall recommendation score for an artifact."""
        score = 0.0

        # Factor 1: Behavioral patterns (40%)
        behavior_score = self.user_model.predict_engagement(artifact)
        score += behavior_score * 0.4

        # Factor 2: Content similarity (30%)
        similarity_score = self._calculate_content_similarity(artifact)
        score += similarity_score * 0.3

        # Factor 3: Goal alignment (20%)
        goal_score = self._calculate_goal_alignment(artifact)
        score += goal_score * 0.2

        # Factor 4: Temporal factors (10%)
        temporal_score = self._calculate_temporal_score(artifact)
        score += temporal_score * 0.1

        return min(score, 1.0)

    def _find_similar_artifacts(self, artifact_id: str, limit: int = 5) -> List[Dict]:
        """Find artifacts similar to the given artifact."""
        artifact = next((a for a in self.db.get_artifacts_with_extended() if a['id'] == artifact_id), None)
        if not artifact:
            return []

        # Use vector store for similarity search
        similar = self.vector_store.search(artifact['content'][:500], limit=limit)

        # Add artifact data
        results = []
        for item in similar:
            if item['id'] != artifact_id:
                full_artifact = next((a for a in self.db.get_artifacts_with_extended() if a['id'] == item['id']), None)
                if full_artifact:
                    results.append({
                        **full_artifact,
                        'similarity_score': item['score']
                    })

        return results

    def _generate_reasons(self, artifact: Dict, score: float) -> List[str]:
        """Generate human-readable reasons for recommendation."""
        reasons = []

        # Importance-based
        if artifact.get('importance_score', 0) > 0.8:
            reasons.append("Very important content")

        # Trend-based
        entities = artifact.get('entities', {})
        if entities.get('tech_terms'):
            trending = ['AI', 'GPT', 'LLM', 'Machine Learning']
            if any(term in entities['tech_terms'] for term in trending):
                reasons.append("Covers trending technology topics")

        # Freshness
        created_at = artifact.get('created_at')
        if created_at and (datetime.now() - created_at.replace(tzinfo=None)).days < 7:
            reasons.append("Recently captured")

        # Consumption status
        if artifact.get('consumption_status') == 'unconsumed':
            reasons.append("Not yet reviewed")

        # High engagement potential
        if artifact.get('engagement_score', 0) < 2:  # Low current engagement
            reasons.append("Potential for new insights")

        return reasons[:3]  # Top 3 reasons

    def _calculate_content_similarity(self, artifact: Dict) -> float:
        """Calculate similarity to user's consumed content."""
        # Get consumed artifacts
        consumed = self.db.get_artifacts_with_extended(consumption_status='reviewed')

        if not consumed:
            return 0.5  # Default neutral score

        # Simple entity overlap calculation
        artifact_entities = set()
        entities = artifact.get('entities', {})
        for entity_list in entities.values():
            if isinstance(entity_list, list):
                artifact_entities.update(entity_list)

        max_similarity = 0
        for consumed_artifact in consumed[:5]:  # Check against last 5 consumed
            consumed_entities = set()
            consumed_entities_data = consumed_artifact.get('entities', {})
            for entity_list in consumed_entities_data.values():
                if isinstance(entity_list, list):
                    consumed_entities.update(entity_list)

            # Calculate Jaccard similarity
            intersection = len(artifact_entities & consumed_entities)
            union = len(artifact_entities | consumed_entities)

            if union > 0:
                similarity = intersection / union
                max_similarity = max(max_similarity, similarity)

        return max_similarity

    def _calculate_goal_alignment(self, artifact: Dict) -> float:
        """Calculate alignment with user's active goals."""
        goals = self.db.get_active_goals()
        if not goals:
            return 0.3  # Default neutral score

        alignment_scores = []

        for goal in goals:
            goal_text = goal['goal'].lower()
            goal_topics = [t.lower() for t in goal.get('related_topics', [])]

            # Check content alignment
            content_lower = artifact['content'].lower()
            artifact_score = 0

            # Direct goal matching
            if goal_text in content_lower:
                artifact_score += 0.5

            # Topic matching
            topic_matches = sum(1 for topic in goal_topics if topic in content_lower)
            artifact_score += topic_matches * 0.2

            # Entity matching
            entities = artifact.get('entities', {})
            entity_text = ' '.join([' '.join(e) if isinstance(e, list) else str(e)
                                   for e in entities.values() if e]).lower()

            for topic in goal_topics:
                if topic in entity_text:
                    artifact_score += 0.1

            alignment_scores.append(min(artifact_score, 1.0))

        # Return maximum alignment with any goal
        return max(alignment_scores) if alignment_scores else 0.3

    def _calculate_temporal_score(self, artifact: Dict) -> float:
        """Calculate temporal relevance score."""
        created_at = artifact.get('created_at')
        if not created_at:
            return 0.5

        days_old = (datetime.now() - created_at.replace(tzinfo=None)).days

        if days_old < 1:
            return 1.0  # Very recent
        elif days_old < 7:
            return 0.8  # Recent
        elif days_old < 30:
            return 0.6  # Moderately recent
        elif days_old < 90:
            return 0.4  # Old
        else:
            return 0.2  # Very old


class UserBehaviorModel:
    """Models user behavior for personalized recommendations."""

    def __init__(self):
        self.consumption_patterns = self._learn_consumption_patterns()

    def predict_engagement(self, artifact: Dict) -> float:
        """
        Predict user engagement likelihood for an artifact.

        Args:
            artifact: Artifact data

        Returns:
            Predicted engagement score (0-1)
        """
        score = 0.5  # Base score

        # Content length preference
        content_length = len(artifact.get('content', ''))
        if 500 <= content_length <= 2000:
            score += 0.1  # Medium-length content
        elif content_length > 3000:
            score -= 0.1  # Very long content

        # Source preference
        metadata = artifact.get('metadata', {})
        source_type = metadata.get('source_type', '')
        if source_type in ['research_paper', 'article']:
            score += 0.1  # Educational content

        # Tech preference (if user has consumed tech content before)
        entities = artifact.get('entities', {})
        tech_terms = entities.get('tech_terms', [])
        if tech_terms:
            score += 0.1 * min(len(tech_terms) / 5, 1)  # More tech terms = higher score

        # Importance consideration
        importance = artifact.get('importance_score', 0.5)
        score += (importance - 0.5) * 0.2  # Adjust based on importance

        return min(max(score, 0), 1)

    def _learn_consumption_patterns(self) -> Dict:
        """Learn from user's consumption history."""
        # This would analyze historical consumption data
        # For now, return default patterns
        return {
            'preferred_length_range': (500, 2000),
            'preferred_sources': ['article', 'research_paper'],
            'tech_affinity': 0.7,
            'business_interest': 0.5
        }