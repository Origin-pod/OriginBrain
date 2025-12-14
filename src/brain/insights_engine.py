"""
Advanced Insights Engine for OriginBrain.
Generates sophisticated insights, trends, and patterns from captured knowledge.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from collections import Counter, defaultdict
from src.db.db import BrainDB
from src.brain.content_analyzer import ContentAnalyzer

logger = logging.getLogger(__name__)

class InsightsEngine:
    """Generates advanced insights and patterns from user's knowledge base."""

    def __init__(self):
        self.db = BrainDB()
        self.content_analyzer = ContentAnalyzer()

    def generate_personalized_insights(self, user_context: Dict = None) -> Dict:
        """
        Generate comprehensive insights personalized to the user.

        Args:
            user_context: User's current context, goals, and preferences

        Returns:
            Dictionary with various insights and recommendations
        """
        insights = {
            'trends': self.detect_trends(days=30),
            'knowledge_gaps': self.identify_knowledge_gaps(),
            'consumption_patterns': self.analyze_consumption_patterns(),
            'entity_network': self.build_entity_network(),
            'recommendations': self._generate_personalized_recommendations(user_context)
        }

        return insights

    def detect_trends(self, days: int = 30) -> List[Dict]:
        """
        Detect trending topics and patterns in recent captures.

        Args:
            days: Number of days to analyze

        Returns:
            List of trending topics with metadata
        """
        # Get recent artifacts
        artifacts = self.db.get_artifacts_with_extended(limit=None)
        cutoff_date = datetime.now() - timedelta(days=days)

        # Filter recent artifacts
        recent = [
            a for a in artifacts
            if a.get('created_at') and a['created_at'].replace(tzinfo=None) > cutoff_date
        ]

        if not recent:
            return []

        # Analyze entities and topics
        all_entities = defaultdict(int)
        all_tech_terms = defaultdict(int)
        all_business_terms = defaultdict(int)
        sources = defaultdict(int)

        for artifact in recent:
            entities = artifact.get('entities', {})
            if entities:
                for entity_type, entity_list in entities.items():
                    if entity_list and isinstance(entity_list, list):
                        for entity in entity_list:
                            all_entities[f"{entity_type}:{entity}"] += 1

                # Track specific term types
                tech_terms = entities.get('tech_terms', [])
                business_terms = entities.get('business_terms', [])

                for term in tech_terms:
                    all_tech_terms[term] += 1

                for term in business_terms:
                    all_business_terms[term] += 1

            # Track sources
            metadata = artifact.get('metadata', {})
            if metadata.get('source_type'):
                sources[metadata['source_type']] += 1

        # Identify trends (entities appearing in multiple artifacts)
        trends = []

        # Tech trends
        for term, count in sorted(all_tech_terms.items(), key=lambda x: x[1], reverse=True)[:10]:
            if count > 1:
                trends.append({
                    'type': 'tech',
                    'topic': term,
                    'frequency': count,
                    'growth_rate': self._calculate_growth_rate(term, 'tech_terms', days),
                    'related_artifacts': self._find_artifacts_with_term(term, 'tech_terms')
                })

        # Business trends
        for term, count in sorted(all_business_terms.items(), key=lambda x: x[1], reverse=True)[:10]:
            if count > 1:
                trends.append({
                    'type': 'business',
                    'topic': term,
                    'frequency': count,
                    'growth_rate': self._calculate_growth_rate(term, 'business_terms', days),
                    'related_artifacts': self._find_artifacts_with_term(term, 'business_terms')
                })

        # Sort by combined score (frequency + growth)
        trends.sort(key=lambda x: x['frequency'] * (1 + x['growth_rate']), reverse=True)

        return trends[:15]  # Top 15 trends

    def identify_knowledge_gaps(self) -> List[Dict]:
        """
        Identify areas where knowledge might be incomplete or missing.

        Returns:
            List of identified knowledge gaps with recommendations
        """
        artifacts = self.db.get_artifacts_with_extended(limit=None)

        # Analyze entity co-occurrence patterns
        entity_cooccurrence = defaultdict(lambda: defaultdict(int))
        all_entities = set()

        for artifact in artifacts:
            entities = artifact.get('entities', {})
            if entities:
                # Collect all entities in this artifact
                artifact_entities = []
                for entity_type, entity_list in entities.items():
                    if entity_list and isinstance(entity_list, list):
                        for entity in entity_list:
                            artifact_entities.append(entity)
                            all_entities.add(entity)

                # Update co-occurrence matrix
                for i, entity1 in enumerate(artifact_entities):
                    for entity2 in artifact_entities[i+1:]:
                        entity_cooccurrence[entity1][entity2] += 1
                        entity_cooccurrence[entity2][entity1] += 1

        # Identify potential gaps
        gaps = []

        # 1. Incomplete knowledge chains (concept mentioned but not explained)
        for entity in all_entities:
            # Find artifacts mentioning this entity
            related_artifacts = self._find_artifacts_with_term(entity)

            # Check if entity is often mentioned but rarely explained in depth
            mention_count = len(related_artifacts)
            detailed_count = sum(1 for a in related_artifacts
                               if a.get('content', '').count(entity) > 3)  # Appears multiple times = detailed

            if mention_count >= 3 and detailed_count < mention_count * 0.3:
                gaps.append({
                    'type': 'incomplete_explanation',
                    'entity': entity,
                    'mention_count': mention_count,
                    'detailed_count': detailed_count,
                    'recommendation': f"Look for in-depth explanations of {entity}",
                    'related_artifacts': related_artifacts[:3]
                })

        # 2. Missing connections between related concepts
        for entity1, related_entities in entity_cooccurrence.items():
            for entity2, cooccurrence_count in related_entities.items():
                if cooccurrence_count >= 2:  # They appear together often
                    # Check if there's a direct relationship recorded
                    has_relationship = self._check_existing_relationship(entity1, entity2)

                    if not has_relationship:
                        gaps.append({
                            'type': 'missing_connection',
                            'entity1': entity1,
                            'entity2': entity2,
                            'cooccurrence_count': cooccurrence_count,
                            'recommendation': f"Explore the relationship between {entity1} and {entity2}"
                        })

        # 3. Emerging topics with limited coverage
        recent_entities = self._get_recent_entities(days=7)
        for entity, count in recent_entities.items():
            if count >= 2 and count <= 3:  # Emerging but limited
                gaps.append({
                    'type': 'emerging_topic',
                    'entity': entity,
                    'recent_mentions': count,
                    'recommendation': f"{entity} appears to be emerging - gather more comprehensive information"
                })

        return gaps[:10]  # Top 10 gaps

    def analyze_consumption_patterns(self) -> Dict:
        """
        Analyze user's consumption patterns and behaviors.

        Returns:
            Dictionary with consumption insights
        """
        # Get consumption events
        events = self.db.get_consumption_events(limit=1000)
        artifacts = self.db.get_artifacts_with_extended(limit=None)

        # Time-based patterns
        hourly_activity = defaultdict(int)
        daily_activity = defaultdict(int)
        weekly_activity = defaultdict(int)

        # Engagement patterns
        event_types = defaultdict(int)
        avg_durations = defaultdict(list)

        for event in events:
            created_at = event.get('created_at')
            if created_at:
                # Convert to datetime if needed
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

                hourly_activity[created_at.hour] += 1
                daily_activity[created_at.strftime('%A')] += 1
                weekly_activity[created_at.isocalendar()[1]] += 1

            # Track event types
            event_type = event.get('event_type', 'unknown')
            event_types[event_type] += 1

            # Track durations
            duration = event.get('duration_seconds')
            if duration and duration > 0:
                avg_durations[event_type].append(duration)

        # Calculate average durations
        avg_duration_by_type = {
            event_type: sum(durations) / len(durations)
            for event_type, durations in avg_durations.items()
            if durations
        }

        # Content preferences
        consumed_status = defaultdict(int)
        importance_scores = []
        engagement_scores = []

        for artifact in artifacts:
            status = artifact.get('consumption_status', 'unconsumed')
            consumed_status[status] += 1

            importance = artifact.get('importance_score')
            if importance is not None:
                importance_scores.append(importance)

            engagement = artifact.get('engagement_score')
            if engagement is not None:
                engagement_scores.append(engagement)

        # Identify patterns
        peak_hour = max(hourly_activity.items(), key=lambda x: x[1])[0] if hourly_activity else None
        peak_day = max(daily_activity.items(), key=lambda x: x[1])[0] if daily_activity else None

        # Calculate consumption efficiency
        total_artifacts = len(artifacts)
        applied_count = consumed_status.get('applied', 0)
        consumption_rate = applied_count / total_artifacts if total_artifacts > 0 else 0

        return {
            'time_patterns': {
                'peak_hour': peak_hour,
                'peak_day': peak_day,
                'hourly_distribution': dict(hourly_activity),
                'daily_distribution': dict(daily_activity)
            },
            'engagement_patterns': {
                'event_type_distribution': dict(event_types),
                'average_durations_seconds': avg_duration_by_type,
                'average_engagement_score': sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0
            },
            'consumption_efficiency': {
                'total_artifacts': total_artifacts,
                'consumption_rate': consumption_rate,
                'status_distribution': dict(consumed_status)
            },
            'quality_indicators': {
                'average_importance_score': sum(importance_scores) / len(importance_scores) if importance_scores else 0,
                'high_importance_ratio': sum(1 for s in importance_scores if s > 0.7) / len(importance_scores) if importance_scores else 0
            }
        }

    def build_entity_network(self) -> Dict:
        """
        Build a network of entities and their relationships.

        Returns:
            Network representation of entities and connections
        """
        artifacts = self.db.get_artifacts_with_extended(limit=None)

        # Collect all entity relationships
        entity_connections = defaultdict(lambda: defaultdict(int))
        entity_metadata = defaultdict(lambda: {
            'count': 0,
            'types': set(),
            'artifacts': [],
            'sentiment_scores': []
        })

        for artifact in artifacts:
            entities = artifact.get('entities', {})
            if not entities:
                continue

            # Update entity metadata
            for entity_type, entity_list in entities.items():
                if entity_list and isinstance(entity_list, list):
                    for entity in entity_list:
                        entity_metadata[entity]['count'] += 1
                        entity_metadata[entity]['types'].add(entity_type)
                        entity_metadata[entity]['artifacts'].append(artifact['id'])

                        # Add sentiment if available
                        insights = artifact.get('insights', {})
                        sentiment = insights.get('sentiment')
                        if sentiment:
                            entity_metadata[entity]['sentiment_scores'].append(sentiment.get('compound', 0))

            # Update connections
            all_entities = []
            for entity_list in entities.values():
                if entity_list:
                    all_entities.extend(entity_list)

            for i, entity1 in enumerate(all_entities):
                for entity2 in all_entities[i+1:]:
                    entity_connections[entity1][entity2] += 1
                    entity_connections[entity2][entity1] += 1

        # Prepare network data
        nodes = []
        edges = []

        # Create nodes
        for entity, metadata in entity_metadata.items():
            if metadata['count'] > 1:  # Only include entities appearing in multiple artifacts
                avg_sentiment = sum(metadata['sentiment_scores']) / len(metadata['sentiment_scores']) if metadata['sentiment_scores'] else 0

                nodes.append({
                    'id': entity,
                    'label': entity,
                    'size': min(metadata['count'] * 5, 50),  # Scale node size
                    'types': list(metadata['types']),
                    'count': metadata['count'],
                    'sentiment': avg_sentiment
                })

        # Create edges
        for entity1, connections in entity_connections.items():
            for entity2, strength in connections.items():
                if strength > 1 and entity1 < entity2:  # Avoid duplicate edges
                    edges.append({
                        'source': entity1,
                        'target': entity2,
                        'strength': strength,
                        'weight': min(strength * 2, 10)
                    })

        # Calculate centrality metrics
        centrality = self._calculate_centrality(nodes, edges)

        # Update nodes with centrality
        for node in nodes:
            node['centrality'] = centrality.get(node['id'], 0)

        # Sort nodes by centrality
        nodes.sort(key=lambda x: x['centrality'], reverse=True)

        return {
            'nodes': nodes[:50],  # Top 50 most central entities
            'edges': edges[:100],  # Top 100 strongest connections
            'total_entities': len(entity_metadata),
            'network_density': len(edges) / (len(nodes) * (len(nodes) - 1) / 2) if len(nodes) > 1 else 0
        }

    def _generate_personalized_recommendations(self, user_context: Dict = None) -> List[Dict]:
        """
        Generate personalized recommendations based on user behavior and goals.

        Args:
            user_context: User's goals and preferences

        Returns:
            List of personalized recommendations
        """
        recommendations = []

        # Get user goals
        goals = self.db.get_active_goals()
        goal_topics = []
        for goal in goals:
            goal_topics.extend(goal.get('related_topics', []))
            goal_topics.append(goal.get('goal', '').lower())

        # Get unprocessed or low-engagement artifacts
        artifacts = self.db.get_artifacts_with_extended(limit=None)
        low_engagement = [
            a for a in artifacts
            if a.get('engagement_score', 0) < 2 or a.get('consumption_status') == 'unconsumed'
        ]

        # Generate recommendations based on different criteria
        for artifact in low_engagement[:20]:  # Check top 20
            score = 0
            reasons = []

            # Goal alignment
            entities = artifact.get('entities', {})
            all_terms = []
            for term_list in entities.values():
                if isinstance(term_list, list):
                    all_terms.extend([t.lower() for t in term_list])

            goal_alignment = len(set(all_terms) & set(goal_topics))
            if goal_alignment > 0:
                score += goal_alignment * 0.3
                reasons.append(f"Aligns with your goals: {goal_alignment} matching topics")

            # High importance but not consumed
            if artifact.get('importance_score', 0) > 0.7 and artifact.get('consumption_status') == 'unconsumed':
                score += 0.4
                reasons.append("High importance content not yet reviewed")

            # Trending topics
            if entities.get('tech_terms'):
                trending = ['AI', 'GPT', 'LLM', 'Machine Learning', 'Python']
                if any(term in entities['tech_terms'] for term in trending):
                    score += 0.2
                    reasons.append("Covers trending technology topics")

            # Source authority
            insights = artifact.get('insights', {})
            source_analysis = insights.get('source_analysis', {})
            if source_analysis.get('authority_score', 0) > 0.8:
                score += 0.1
                reasons.append("Highly authoritative source")

            if score > 0.3:  # Minimum threshold for recommendation
                recommendations.append({
                    'artifact_id': artifact['id'],
                    'title': artifact.get('title', 'Untitled'),
                    'score': min(score, 1.0),
                    'reasons': reasons,
                    'estimated_read_time': artifact.get('estimated_read_time', 0)
                })

        # Sort by score
        recommendations.sort(key=lambda x: x['score'], reverse=True)

        return recommendations[:10]  # Top 10 recommendations

    def _calculate_growth_rate(self, term: str, term_type: str, days: int) -> float:
        """Calculate the growth rate of a term over the given period."""
        # This is a simplified calculation
        # In a real implementation, you'd compare frequency in recent vs older periods
        return 0.1  # Placeholder

    def _find_artifacts_with_term(self, term: str, term_type: str = None) -> List[Dict]:
        """Find artifacts containing a specific term."""
        artifacts = self.db.get_artifacts_with_extended(limit=None)
        matching = []

        for artifact in artifacts:
            entities = artifact.get('entities', {})
            found = False

            if term_type and term_type in entities:
                found = term in entities[term_type]
            else:
                # Search all entity types
                for entity_list in entities.values():
                    if isinstance(entity_list, list) and term in entity_list:
                        found = True
                        break

            if found:
                matching.append(artifact)

        return matching

    def _check_existing_relationship(self, entity1: str, entity2: str) -> bool:
        """Check if a relationship already exists between two entities."""
        # This would query the relationships table
        # For now, return False as a placeholder
        return False

    def _get_recent_entities(self, days: int = 7) -> Dict[str, int]:
        """Get entities from recent artifacts."""
        artifacts = self.db.get_artifacts_with_extended(limit=None)
        cutoff_date = datetime.now() - timedelta(days=days)

        recent_entities = defaultdict(int)

        for artifact in artifacts:
            created_at = artifact.get('created_at')
            if created_at and created_at.replace(tzinfo=None) > cutoff_date:
                entities = artifact.get('entities', {})
                for entity_list in entities.values():
                    if isinstance(entity_list, list):
                        for entity in entity_list:
                            recent_entities[entity] += 1

        return recent_entities

    def _calculate_centrality(self, nodes: List[Dict], edges: List[Dict]) -> Dict[str, float]:
        """Calculate centrality scores for entities in the network."""
        centrality = {node['id']: 0 for node in nodes}

        # Simple degree centrality
        for edge in edges:
            source = edge['source']
            target = edge['target']
            weight = edge.get('weight', 1)

            centrality[source] += weight
            centrality[target] += weight

        # Normalize
        max_centrality = max(centrality.values()) if centrality else 1
        centrality = {k: v / max_centrality for k, v in centrality.items()}

        return centrality