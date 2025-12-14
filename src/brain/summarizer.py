"""
Advanced Summarization and Q&A Module for OriginBrain.
Provides AI-powered content summarization and question answering capabilities.
"""

import logging
from typing import List, Dict, Optional, Tuple
from collections import Counter
import re
from datetime import datetime
from src.db.db import BrainDB
from src.brain.content_analyzer import ContentAnalyzer

logger = logging.getLogger(__name__)

class AISummarizer:
    """AI-powered content summarization and analysis."""

    def __init__(self):
        self.db = BrainDB()
        self.content_analyzer = ContentAnalyzer()

    def generate_summary(self, artifact_id: str, summary_type: str = 'short') -> Dict:
        """
        Generate an AI-powered summary for an artifact.

        Args:
            artifact_id: ID of the artifact to summarize
            summary_type: Type of summary ('short', 'medium', 'bullet', 'executive')

        Returns:
            Dictionary with summary and metadata
        """
        # Get artifact data
        artifact = self.db.get_artifact_extended(artifact_id)
        if not artifact:
            logger.error(f"Artifact {artifact_id} not found")
            return {}

        content = artifact.get('content', '')
        if not content:
            return {'error': 'No content to summarize'}

        # Generate different types of summaries
        if summary_type == 'short':
            summary = self._generate_short_summary(content)
        elif summary_type == 'medium':
            summary = self._generate_medium_summary(content)
        elif summary_type == 'bullet':
            summary = self._generate_bullet_summary(content)
        elif summary_type == 'executive':
            summary = self._generate_executive_summary(content, artifact)
        else:
            summary = self._generate_short_summary(content)

        # Extract key insights for all summary types
        key_insights = self._extract_key_insights(content, artifact)

        result = {
            'artifact_id': artifact_id,
            'summary_type': summary_type,
            'summary': summary,
            'word_count': len(content.split()),
            'summary_word_count': len(summary.split()) if isinstance(summary, str) else 0,
            'compression_ratio': len(content.split()) / max(len(summary.split()), 1) if isinstance(summary, str) else 1,
            'key_insights': key_insights,
            'generated_at': datetime.now().isoformat(),
            'confidence_score': self._calculate_confidence_score(content, summary)
        }

        # Store summary in database
        self.db.upsert_artifact_extended(
            artifact_id,
            summary=summary if isinstance(summary, str) else '\n'.join(summary)
        )

        return result

    def _generate_short_summary(self, content: str) -> str:
        """Generate a concise 2-3 sentence summary."""
        # Extract key sentences using a scoring algorithm
        sentences = self._split_into_sentences(content)

        if len(sentences) <= 2:
            return ' '.join(sentences)

        # Score sentences based on importance indicators
        scored_sentences = []
        for sentence in sentences:
            score = 0

            # Length preference (not too short, not too long)
            word_count = len(sentence.split())
            if 10 <= word_count <= 25:
                score += 2
            elif 5 <= word_count <= 9 or 26 <= word_count <= 35:
                score += 1

            # Contains numbers or data
            if re.search(r'\d+', sentence):
                score += 1

            # Contains important keywords
            important_words = ['conclusion', 'result', 'finding', 'key', 'important', 'main', 'primary']
            if any(word in sentence.lower() for word in important_words):
                score += 2

            # Position scoring (first and last sentences often important)
            if sentence == sentences[0]:
                score += 2
            elif sentence == sentences[-1]:
                score += 1

            # Contains entities (proper nouns, capitalized words)
            if re.search(r'[A-Z][a-z]+ [A-Z][a-z]+', sentence):
                score += 1

            scored_sentences.append((sentence, score))

        # Sort by score and pick top 2-3
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [s[0] for s in scored_sentences[:min(3, len(scored_sentences))]]

        return ' '.join(top_sentences)

    def _generate_medium_summary(self, content: str) -> str:
        """Generate a more detailed 3-5 paragraph summary."""
        sentences = self._split_into_sentences(content)

        if len(sentences) <= 5:
            return ' '.join(sentences)

        # Group sentences into logical chunks
        chunks = self._group_sentences_by_topic(sentences)

        # Generate summary for each chunk
        chunk_summaries = []
        for chunk in chunks:
            chunk_summary = self._generate_short_summary(' '.join(chunk))
            chunk_summaries.append(chunk_summary)

        return ' '.join(chunk_summaries)

    def _generate_bullet_summary(self, content: str) -> List[str]:
        """Generate a bullet-point summary."""
        sentences = self._split_into_sentences(content)

        # Extract sentences that look like bullet points or contain key information
        bullets = []

        # Look for sentences starting with bullet indicators
        for sentence in sentences:
            sentence_stripped = sentence.strip()

            # Check if it's a bullet point
            if (sentence_stripped.startswith(('-', '*', '•', '–')) or
                re.match(r'^\d+[\.\)]', sentence_stripped) or
                self._contains_action_items(sentence_stripped)):
                bullets.append(sentence_stripped)
            # Check for important statements
            elif self._is_important_statement(sentence_stripped):
                bullets.append(sentence_stripped)

        # If no clear bullets found, create them from important sentences
        if not bullets:
            scored_sentences = []
            for sentence in sentences:
                score = 0
                if self._is_important_statement(sentence):
                    score += 3
                if re.search(r'\d+(?:\.\d+)?%|\$\d+', sentence):
                    score += 2
                if len(sentence.split()) > 8:
                    score += 1
                scored_sentences.append((sentence, score))

            scored_sentences.sort(key=lambda x: x[1], reverse=True)
            bullets = [s[0] for s in scored_sentences[:5]]

        return bullets[:5]  # Limit to 5 bullet points

    def _generate_executive_summary(self, content: str, artifact: Dict) -> str:
        """Generate an executive summary with business context."""
        sentences = self._split_into_sentences(content)

        # Extract business-relevant information
        executive_sentences = []

        for sentence in sentences:
            if self._is_executive_relevant(sentence, artifact):
                executive_sentences.append(sentence)

        if not executive_sentences:
            return self._generate_short_summary(content)

        # Format as executive summary
        summary = self._generate_short_summary(' '.join(executive_sentences))

        # Add executive summary prefix if appropriate
        if any(word in content.lower() for word in ['report', 'analysis', 'findings', 'recommendation']):
            summary = f"Executive Summary: {summary}"

        return summary

    def answer_question(self, question: str, artifact_id: str = None) -> Dict:
        """
        Answer a question based on the knowledge base.

        Args:
            question: The question to answer
            artifact_id: Optional specific artifact to search

        Returns:
            Dictionary with answer and sources
        """
        # If artifact_id is provided, search within that artifact
        if artifact_id:
            artifact = self.db.get_artifact_extended(artifact_id)
            if artifact:
                answer = self._answer_from_artifact(question, artifact)
                return {
                    'question': question,
                    'answer': answer,
                    'sources': [artifact_id],
                    'confidence': 'high'
                }

        # Search across all artifacts
        all_artifacts = self.db.get_artifacts_with_extended(limit=None)

        # Find relevant artifacts using keyword matching
        relevant_artifacts = self._find_relevant_artifacts(question, all_artifacts)

        if not relevant_artifacts:
            return {
                'question': question,
                'answer': "I couldn't find relevant information in your knowledge base to answer this question.",
                'sources': [],
                'confidence': 'low'
            }

        # Generate answer from most relevant artifacts
        answer_parts = []
        sources = []

        for artifact in relevant_artifacts[:3]:  # Use top 3 most relevant
            artifact_answer = self._extract_relevant_content(question, artifact)
            if artifact_answer:
                answer_parts.append(artifact_answer['content'])
                sources.append({
                    'artifact_id': artifact['id'],
                    'title': artifact.get('title', 'Untitled'),
                    'relevance_score': artifact_answer['score'],
                    'snippet': artifact_answer['snippet']
                })

        if not answer_parts:
            return {
                'question': question,
                'answer': "I found some potentially relevant artifacts but couldn't extract a direct answer.",
                'sources': sources,
                'confidence': 'medium'
            }

        # Combine answers
        combined_answer = self._combine_answers(answer_parts, question)

        return {
            'question': question,
            'answer': combined_answer,
            'sources': sources,
            'confidence': 'high' if len(sources) > 1 else 'medium'
        }

    def generate_insights_report(self, limit: int = 10) -> Dict:
        """
        Generate a comprehensive insights report from recent captures.

        Args:
            limit: Number of recent artifacts to analyze

        Returns:
            Dictionary with insights report
        """
        # Get recent artifacts
        recent_artifacts = self.db.get_artifacts_with_extended(limit=limit)

        if not recent_artifacts:
            return {'error': 'No artifacts found'}

        # Analyze trends and patterns
        insights = {
            'summary': {
                'total_artifacts': len(recent_artifacts),
                'date_range': self._get_date_range(recent_artifacts),
                'report_generated': datetime.now().isoformat()
            },
            'key_themes': self._analyze_themes(recent_artifacts),
            'sentiment_analysis': self._analyze_sentiment_trends(recent_artifacts),
            'entity_analysis': self._analyze_entity_trends(recent_artifacts),
            'recommendations': self._generate_recommendations(recent_artifacts),
            'consumption_gaps': self._identify_consumption_gaps(recent_artifacts)
        }

        return insights

    def _split_into_sentences(self, content: str) -> List[str]:
        """Split content into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', content)
        return [s.strip() for s in sentences if s.strip()]

    def _group_sentences_by_topic(self, sentences: List[str], chunk_size: int = 5) -> List[List[str]]:
        """Group sentences by semantic similarity."""
        chunks = []
        current_chunk = []

        for sentence in sentences:
            current_chunk.append(sentence)
            if len(current_chunk) >= chunk_size:
                chunks.append(current_chunk)
                current_chunk = []

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _contains_action_items(self, sentence: str) -> bool:
        """Check if sentence contains action items."""
        action_words = ['should', 'must', 'need to', 'recommend', 'suggest', 'propose', 'consider']
        return any(word in sentence.lower() for word in action_words)

    def _is_important_statement(self, sentence: str) -> bool:
        """Determine if a sentence contains important information."""
        importance_indicators = [
            'conclusion', 'finding', 'result', 'key', 'main', 'primary',
            'significant', 'important', 'critical', 'essential',
            'discovery', 'innovation', 'breakthrough', 'achievement',
            '%', '$', 'increase', 'decrease', 'improve', 'reduce'
        ]
        return any(indicator in sentence.lower() for indicator in importance_indicators)

    def _is_executive_relevant(self, sentence: str, artifact: Dict) -> bool:
        """Determine if content is relevant for executive summary."""
        executive_keywords = [
            'revenue', 'profit', 'cost', 'budget', 'investment', 'roi',
            'strategy', 'market', 'competition', 'growth', 'performance',
            'risk', 'opportunity', 'challenge', 'recommendation',
            'quarterly', 'annual', 'forecast', 'projection'
        ]

        # Check for executive keywords
        if any(keyword in sentence.lower() for keyword in executive_keywords):
            return True

        # Check if artifact metadata suggests business content
        metadata = artifact.get('metadata', {})
        source_type = metadata.get('source_type', '').lower()

        if source_type in ['business', 'financial', 'market', 'strategy']:
            return True

        return False

    def _extract_key_insights(self, content: str, artifact: Dict) -> List[str]:
        """Extract key insights from content."""
        insights = []
        sentences = self._split_into_sentences(content)

        for sentence in sentences:
            if self._is_important_statement(sentence):
                insights.append(sentence)

        # Limit to top 5 insights
        return insights[:5]

    def _calculate_confidence_score(self, original: str, summary: str) -> float:
        """Calculate confidence score for the summary."""
        # Simple heuristic based on length and coverage
        original_words = set(original.lower().split())
        summary_words = set(summary.lower().split())

        if not original_words:
            return 0.0

        coverage = len(original_words & summary_words) / len(original_words)
        length_ratio = len(summary_words) / len(original_words)

        # Ideal summary is 10-30% of original with good coverage
        ideal_ratio_range = (0.1, 0.3)

        if ideal_ratio_range[0] <= length_ratio <= ideal_ratio_range[1]:
            length_score = 1.0
        else:
            length_score = max(0, 1 - abs(length_ratio - 0.2) / 0.2)

        # Weight coverage more than length
        return (coverage * 0.7 + length_score * 0.3)

    def _find_relevant_artifacts(self, question: str, artifacts: List[Dict]) -> List[Dict]:
        """Find artifacts relevant to the question."""
        # Extract keywords from question
        question_words = set(re.findall(r'\b\w+\b', question.lower()))
        question_words.difference_update(['what', 'how', 'when', 'where', 'why', 'who', 'is', 'are', 'the', 'a', 'an'])

        scored_artifacts = []
        for artifact in artifacts:
            score = 0
            content_lower = artifact.get('content', '').lower()
            title_lower = artifact.get('title', '').lower()

            # Score based on keyword matches
            for word in question_words:
                if word in content_lower:
                    score += 2
                if word in title_lower:
                    score += 3

            # Bonus for entities
            entities = artifact.get('entities', {})
            for entity_list in entities.values():
                if isinstance(entity_list, list):
                    for entity in entity_list:
                        if entity.lower() in question_words:
                            score += 1

            if score > 0:
                scored_artifacts.append({**artifact, 'relevance_score': score})

        # Sort by relevance score
        scored_artifacts.sort(key=lambda x: x['relevance_score'], reverse=True)

        return scored_artifacts

    def _answer_from_artifact(self, question: str, artifact: Dict) -> str:
        """Answer question from a single artifact."""
        content = artifact.get('content', '')
        sentences = self._split_into_sentences(content)

        # Find sentences most relevant to the question
        question_words = set(re.findall(r'\b\w+\b', question.lower()))
        question_words.difference_update(['what', 'how', 'when', 'where', 'why', 'who', 'is', 'are', 'the', 'a', 'an'])

        scored_sentences = []
        for sentence in sentences:
            sentence_words = set(re.findall(r'\b\w+\b', sentence.lower()))
            overlap = len(question_words & sentence_words)
            if overlap > 0:
                scored_sentences.append((sentence, overlap))

        if not scored_sentences:
            return "I couldn't find specific information to answer your question in this artifact."

        # Return most relevant sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        answer = ' '.join(s[0] for s in scored_sentences[:3])

        return f"Based on the artifact: {answer}"

    def _extract_relevant_content(self, question: str, artifact: Dict) -> Optional[Dict]:
        """Extract content most relevant to the question."""
        content = artifact.get('content', '')
        sentences = self._split_into_sentences(content)

        question_words = set(re.findall(r'\b\w+\b', question.lower()))
        question_words.difference_update(['what', 'how', 'when', 'where', 'why', 'who', 'is', 'are', 'the', 'a', 'an'])

        best_sentence = None
        best_score = 0
        best_sentence_text = ""

        for sentence in sentences:
            sentence_words = set(re.findall(r'\b\w+\b', sentence.lower()))
            overlap = len(question_words & sentence_words)

            # Score based on overlap and length
            score = overlap
            if 10 <= len(sentence.split()) <= 25:
                score += 1

            if score > best_score:
                best_score = score
                best_sentence = sentence
                best_sentence_text = sentence

        if best_sentence and best_score > 0:
            return {
                'content': best_sentence,
                'score': best_score,
                'snippet': best_sentence_text[:100] + '...' if len(best_sentence_text) > 100 else best_sentence_text
            }

        return None

    def _combine_answers(self, answer_parts: List[str], question: str) -> str:
        """Combine multiple answers into a coherent response."""
        if len(answer_parts) == 1:
            return answer_parts[0]

        # Simple combination for now
        combined = ""
        for i, part in enumerate(answer_parts):
            if i == 0:
                combined += part
            else:
                combined += f" Additionally, {part.lower()[0].upper() + part.lower()[1:]}"

        return combined

    def _analyze_themes(self, artifacts: List[Dict]) -> List[Dict]:
        """Analyze themes from artifacts."""
        themes = Counter()

        for artifact in artifacts:
            entities = artifact.get('entities', {})
            tech_terms = entities.get('tech_terms', [])
            business_terms = entities.get('business_terms', [])

            # Combine all terms
            all_terms = tech_terms + business_terms
            for term in all_terms:
                themes[term] += 1

        # Return top themes
        return [{'term': term, 'count': count} for term, count in themes.most_common(10)]

    def _analyze_sentiment_trends(self, artifacts: List[Dict]) -> Dict:
        """Analyze sentiment trends in artifacts."""
        positive = 0
        negative = 0
        neutral = 0

        for artifact in artifacts:
            insights = artifact.get('insights', {})
            sentiment = insights.get('sentiment', {})
            category = sentiment.get('category', 'neutral')

            if category == 'positive':
                positive += 1
            elif category == 'negative':
                negative += 1
            else:
                neutral += 1

        total = positive + negative + neutral
        return {
            'positive': positive,
            'negative': negative,
            'neutral': neutral,
            'total': total,
            'positive_ratio': positive / total if total > 0 else 0,
            'negative_ratio': negative / total if total > 0 else 0
        }

    def _analyze_entity_trends(self, artifacts: List[Dict]) -> Dict:
        """Analyze entity trends."""
        all_entities = Counter()
        entity_types = Counter()

        for artifact in artifacts:
            entities = artifact.get('entities', {})
            for entity_type, entity_list in entities.items():
                if isinstance(entity_list, list):
                    entity_types[entity_type] += len(entity_list)
                    for entity in entity_list:
                        all_entities[entity] += 1

        return {
            'top_entities': [{'entity': entity, 'count': count} for entity, count in all_entities.most_common(10)],
            'entity_types': dict(entity_types)
        }

    def _generate_recommendations(self, artifacts: List[Dict]) -> List[str]:
        """Generate recommendations based on artifacts."""
        recommendations = []

        # Look for unconsumed high-priority content
        for artifact in artifacts:
            if (artifact.get('consumption_status') == 'unconsumed' and
                artifact.get('importance_score', 0) > 0.7):
                recommendations.append(
                    f"Review '{artifact.get('title', 'Untitled')}' - high importance, not yet consumed"
                )

        return recommendations[:5]

    def _identify_consumption_gaps(self, artifacts: List[Dict]) -> List[str]:
        """Identify consumption gaps."""
        total = len(artifacts)
        consumed = sum(1 for a in artifacts if a.get('consumption_status') in ['reviewed', 'applied'])

        gaps = []
        if consumed / total < 0.5:
            gaps.append(f"Low consumption rate: Only {consumed}/{total} artifacts have been reviewed or applied")

        return gaps

    def _get_date_range(self, artifacts: List[Dict]) -> str:
        """Get the date range of artifacts."""
        if not artifacts:
            return "No artifacts"

        dates = [a.get('created_at') for a in artifacts if a.get('created_at')]
        if not dates:
            return "No dates available"

        min_date = min(dates)
        max_date = max(dates)

        return f"{min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}"