"""
Advanced Relationship Mapper for OriginBrain.
Discovers and creates sophisticated relationships between artifacts.
"""

import logging
import re
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
from datetime import datetime
from src.db.db import BrainDB
from src.brain.content_analyzer import ContentAnalyzer

logger = logging.getLogger(__name__)

class RelationshipMapper:
    """Maps advanced relationships between artifacts beyond simple similarity."""

    def __init__(self):
        self.db = BrainDB()
        self.content_analyzer = ContentAnalyzer()

    def discover_all_relationships(self, artifact_id: str = None) -> Dict:
        """
        Discover all types of relationships for artifacts.

        Args:
            artifact_id: Specific artifact to process, or None for all

        Returns:
            Statistics about discovered relationships
        """
        if artifact_id:
            artifacts = [self.db.get_artifact_extended(artifact_id)]
            artifacts = [a for a in artifacts if a]  # Filter out None
        else:
            artifacts = self.db.get_artifacts_with_extended(limit=None)

        stats = {
            'processed': 0,
            'relationships_created': 0,
            'relationship_types': defaultdict(int)
        }

        logger.info(f"Discovering relationships for {len(artifacts)} artifacts...")

        for artifact in artifacts:
            try:
                # Find different types of relationships
                relationships = []

                # 1. Reference relationships (URLs, citations)
                ref_relationships = self._find_reference_relationships(artifact)
                relationships.extend(ref_relationships)

                # 2. Entity co-occurrence relationships
                entity_relationships = self._find_entity_relationships(artifact)
                relationships.extend(entity_relationships)

                # 3. Temporal relationships (responses, updates)
                temporal_relationships = self._find_temporal_relationships(artifact)
                relationships.extend(temporal_relationships)

                # 4. Contradiction relationships
                contradiction_relationships = self._find_contradiction_relationships(artifact)
                relationships.extend(contradiction_relationships)

                # 5. Extension relationships (builds upon, extends)
                extension_relationships = self._find_extension_relationships(artifact)
                relationships.extend(extension_relationships)

                # Create relationships in database
                for rel in relationships:
                    rel_id = self.db.create_relationship(
                        source_artifact_id=artifact['id'],
                        target_artifact_id=rel['target_id'],
                        relationship_type=rel['type'],
                        strength=rel['strength'],
                        evidence=rel.get('evidence'),
                        created_by='auto'
                    )

                    if rel_id:
                        stats['relationships_created'] += 1
                        stats['relationship_types'][rel['type']] += 1

                stats['processed'] += 1

            except Exception as e:
                logger.error(f"Failed to process relationships for artifact {artifact['id']}: {e}")

        logger.info(f"Relationship discovery complete: {stats}")
        return dict(stats)

    def _find_reference_relationships(self, artifact: Dict) -> List[Dict]:
        """Find reference-based relationships (links, citations)."""
        relationships = []

        content = artifact.get('content', '')
        metadata = artifact.get('metadata', {})

        # Find URLs in content
        url_pattern = r'https?://[^\s<>"{}|\\^`[\]]+'
        urls = re.findall(url_pattern, content)

        # Check each URL against other artifacts
        for url in urls:
            # Find artifacts with this URL
            all_artifacts = self.db.get_all_artifacts()
            for other_artifact in all_artifacts:
                if other_artifact['id'] == artifact['id']:
                    continue

                other_metadata = other_artifact.get('metadata', {})

                # Check if URL matches source_url or is in content
                if (url == other_metadata.get('source_url') or
                    url in other_artifact.get('content', '')):
                    relationships.append({
                        'target_id': other_artifact['id'],
                        'type': 'references',
                        'strength': 0.9,
                        'evidence': f"Contains URL: {url}"
                    })

        # Check for citation patterns
        citation_patterns = [
            r'\[(\d+)\]',  # Numbered citations [1], [2]
            r'\([^)]*et al\., \d{4}\)',  # Academic citations (Smith et al., 2023)
            r'See also:\s*(https?://[^\s]+)',  # "See also: URL"
        ]

        for pattern in citation_patterns:
            matches = re.findall(pattern, content)
            if matches:
                # This indicates references to other works
                relationships.append({
                    'target_id': None,  # Will need manual linking
                    'type': 'cites',
                    'strength': 0.7,
                    'evidence': f"Contains citation pattern: {pattern}"
                })

        return relationships

    def _find_entity_relationships(self, artifact: Dict) -> List[Dict]:
        """Find relationships based on shared entities."""
        relationships = []

        artifact_entities = artifact.get('entities', {})
        if not artifact_entities:
            return relationships

        # Flatten all entities
        all_entities = set()
        for entity_list in artifact_entities.values():
            if isinstance(entity_list, list):
                all_entities.update(entity_list)

        # Find other artifacts with shared entities
        all_artifacts = self.db.get_artifacts_with_extended(limit=None)

        for other_artifact in all_artifacts:
            if other_artifact['id'] == artifact['id']:
                continue

            other_entities = other_artifact.get('entities', {})
            if not other_entities:
                continue

            # Flatten other artifact entities
            other_all_entities = set()
            for entity_list in other_entities.values():
                if isinstance(entity_list, list):
                    other_all_entities.update(entity_list)

            # Calculate entity overlap
            shared_entities = all_entities & other_all_entities

            if len(shared_entities) > 0:
                # Calculate relationship strength based on overlap ratio
                total_entities = len(all_entities | other_all_entities)
                overlap_ratio = len(shared_entities) / total_entities if total_entities > 0 else 0

                if overlap_ratio > 0.2:  # At least 20% overlap
                    relationship_type = self._determine_entity_relationship_type(
                        shared_entities, artifact_entities, other_entities
                    )

                    relationships.append({
                        'target_id': other_artifact['id'],
                        'type': relationship_type,
                        'strength': min(overlap_ratio * 2, 1.0),  # Scale to 0-1
                        'evidence': f"Shared {len(shared_entities)} entities: {', '.join(list(shared_entities)[:3])}"
                    })

        return relationships

    def _find_temporal_relationships(self, artifact: Dict) -> List[Dict]:
        """Find time-based relationships (responses, updates, follow-ups)."""
        relationships = []

        content = artifact.get('content', '').lower()
        artifact_date = artifact.get('created_at')
        if not artifact_date:
            return relationships

        # Patterns indicating responses or follow-ups
        response_patterns = [
            r'response to',
            r'reply to',
            r'following up on',
            r'builds on',
            r'updates previous',
            r'corrects earlier',
            r'clarifies'
        ]

        for pattern in response_patterns:
            if re.search(pattern, content):
                # This artifact references or responds to earlier content
                # Find artifacts created before this one
                all_artifacts = self.db.get_artifacts_with_extended(limit=None)
                earlier_artifacts = [
                    a for a in all_artifacts
                    if (a['id'] != artifact['id'] and
                        a.get('created_at') and
                        a['created_at'] < artifact_date)
                ]

                # Look for content similarity to find the referenced artifact
                for earlier in earlier_artifacts[:10]:  # Check last 10
                    similarity = self._calculate_text_similarity(
                        artifact['content'], earlier['content']
                    )

                    if similarity > 0.3:  # Some similarity indicates possible reference
                        relationships.append({
                            'target_id': earlier['id'],
                            'type': 'follows_up' if 'follow' in pattern else 'responds_to',
                            'strength': similarity,
                            'evidence': f"Contains response pattern: {pattern}"
                        })

        return relationships

    def _find_contradiction_relationships(self, artifact: Dict) -> List[Dict]:
        """Find contradiction relationships between artifacts."""
        relationships = []

        # Analyze sentiment and key claims
        artifact_sentiment = self._get_sentiment(artifact)
        artifact_claims = self._extract_key_claims(artifact)

        if not artifact_claims:
            return relationships

        # Compare with other artifacts
        all_artifacts = self.db.get_artifacts_with_extended(limit=None)

        for other_artifact in all_artifacts:
            if other_artifact['id'] == artifact['id']:
                continue

            other_sentiment = self._get_sentiment(other_artifact)
            other_claims = self._extract_key_claims(other_artifact)

            if not other_claims:
                continue

            # Check for contradictory claims
            contradictions = self._find_contradictions(artifact_claims, other_claims)

            if contradictions:
                # Check if sentiments are opposite
                sentiment_opposite = (
                    (artifact_sentiment > 0.2 and other_sentiment < -0.2) or
                    (artifact_sentiment < -0.2 and other_sentiment > 0.2)
                )

                strength = 0.8 if sentiment_opposite else 0.6

                relationships.append({
                    'target_id': other_artifact['id'],
                    'type': 'contradicts',
                    'strength': strength,
                    'evidence': f"Contradictory claims: {contradictions[0]}"
                })

        return relationships

    def _find_extension_relationships(self, artifact: Dict) -> List[Dict]:
        """Find extension relationships (builds upon, extends)."""
        relationships = []

        content = artifact.get('content', '').lower()

        # Patterns indicating extensions
        extension_patterns = [
            r'builds upon',
            r'extends the work',
            r'based on previous',
            r'inspired by',
            r'following the approach',
            r'using the method from'
        ]

        for pattern in extension_patterns:
            if re.search(pattern, content):
                # This artifact extends previous work
                # Find potentially related artifacts
                all_artifacts = self.db.get_artifacts_with_extended(limit=None)

                # Look for artifacts with similar technical content
                for other in all_artifacts:
                    if other['id'] == artifact['id']:
                        continue

                    # Check for technical similarity
                    tech_similarity = self._calculate_technical_similarity(artifact, other)

                    if tech_similarity > 0.5:
                        relationships.append({
                            'target_id': other['id'],
                            'type': 'extends',
                            'strength': tech_similarity,
                            'evidence': f"Contains extension pattern: {pattern}"
                        })

        return relationships

    def _determine_entity_relationship_type(self, shared_entities: Set,
                                           entities1: Dict, entities2: Dict) -> str:
        """Determine the type of relationship based on shared entities."""
        # Check for specific entity types to determine relationship
        if any('organization' in str(k) for k in entities1.keys()) or \
           any('organization' in str(k) for k in entities2.keys()):
            return 'related_organization'

        if any('person' in str(k) for k in entities1.keys()) or \
           any('person' in str(k) for k in entities2.keys()):
            return 'related_person'

        # Count tech term overlap
        tech1 = set(entities1.get('tech_terms', []))
        tech2 = set(entities2.get('tech_terms', []))
        if tech1 & tech2:
            return 'related_technology'

        # Count business term overlap
        biz1 = set(entities1.get('business_terms', []))
        biz2 = set(entities2.get('business_terms', []))
        if biz1 & biz2:
            return 'related_business'

        return 'related_topic'

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts."""
        # Simple word overlap similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0

    def _get_sentiment(self, artifact: Dict) -> float:
        """Get sentiment score for an artifact."""
        insights = artifact.get('insights', {})
        sentiment = insights.get('sentiment', {})
        return sentiment.get('compound', 0)

    def _extract_key_claims(self, artifact: Dict, limit: int = 5) -> List[str]:
        """Extract key claims from an artifact."""
        content = artifact.get('content', '')

        # Simple claim extraction patterns
        claim_patterns = [
            r'[A-Z][^.]*is [^.]*\.',  # X is Y pattern
            r'[A-Z][^.]*can [^.]*\.',  # X can Y pattern
            r'[A-Z][^.]*will [^.]*\.',  # X will Y pattern
        ]

        claims = []
        for pattern in claim_patterns:
            matches = re.findall(pattern, content)
            claims.extend(matches[:2])  # Take 2 claims per pattern

        return claims[:limit] if claims else []

    def _find_contradictions(self, claims1: List[str], claims2: List[str]) -> List[str]:
        """Find contradictory claims between two sets."""
        contradictions = []

        # Simple contradiction detection
        negation_words = ['not', 'no', 'never', 'cannot', 'impossible']

        for claim1 in claims1:
            for claim2 in claims2:
                # Check if claims are similar but have opposite sentiment
                if self._calculate_text_similarity(claim1, claim2) > 0.5:
                    has_negation1 = any(neg in claim1.lower() for neg in negation_words)
                    has_negation2 = any(neg in claim2.lower() for neg in negation_words)

                    if has_negation1 != has_negation2:  # One has negation, other doesn't
                        contradictions.append(f"'{claim1}' vs '{claim2}'")

        return contradictions

    def _calculate_technical_similarity(self, artifact1: Dict, artifact2: Dict) -> float:
        """Calculate technical similarity between two artifacts."""
        entities1 = artifact1.get('entities', {})
        entities2 = artifact2.get('entities', {})

        # Compare tech terms
        tech1 = set(entities1.get('tech_terms', []))
        tech2 = set(entities2.get('tech_terms', []))

        tech_overlap = len(tech1 & tech2)
        tech_union = len(tech1 | tech2)

        if tech_union == 0:
            return 0

        return tech_overlap / tech_union

    def build_knowledge_graph(self) -> Dict:
        """
        Build a comprehensive knowledge graph from all relationships.

        Returns:
            Knowledge graph structure with nodes and edges
        """
        # Get all relationships
        all_artifacts = self.db.get_artifacts_with_extended(limit=None)

        nodes = []
        edges = []
        node_map = {}

        # Create nodes
        for artifact in all_artifacts:
            node_id = artifact['id']
            node_map[node_id] = len(nodes)

            nodes.append({
                'id': node_id,
                'title': artifact.get('title', 'Untitled'),
                'type': artifact.get('metadata', {}).get('source_type', 'unknown'),
                'importance': artifact.get('importance_score', 0.5),
                'consumption_status': artifact.get('consumption_status', 'unconsumed'),
                'entities': artifact.get('entities', {}),
                'created_at': artifact.get('created_at')
            })

        # Create edges from relationships
        for artifact in all_artifacts:
            relationships = self.db.get_artifact_relationships(artifact['id'])

            for rel in relationships:
                source_idx = node_map.get(rel['source_artifact'])
                target_idx = node_map.get(rel['target_artifact'])

                if source_idx is not None and target_idx is not None:
                    edges.append({
                        'source': source_idx,
                        'target': target_idx,
                        'type': rel['relationship_type'],
                        'strength': rel['strength'],
                        'evidence': rel.get('evidence', '')
                    })

        return {
            'nodes': nodes,
            'edges': edges,
            'stats': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'density': len(edges) / (len(nodes) * (len(nodes) - 1) / 2) if len(nodes) > 1 else 0
            }
        }