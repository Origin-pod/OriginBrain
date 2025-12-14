"""
Content Analyzer for enhanced artifact processing.
Provides entity extraction, sentiment analysis, and content insights.
"""

import re
import json
import logging
from typing import List, Dict, Set, Optional, Tuple
from collections import Counter
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.tag import pos_tag
from nltk.chunk import ne_chunk

# Download required NLTK data (only once)
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('sentiment/vader_lexicon.zip')
    nltk.data.find('taggers/averaged_perceptron_tagger')
    nltk.data.find('chunkers/maxent_ne_chunker')
    nltk.data.find('corpora/words')
except LookupError:
    nltk.download('punkt', quiet=True)
    nltk.download('vader_lexicon', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
    nltk.download('maxent_ne_chunker', quiet=True)
    nltk.download('words', quiet=True)

logger = logging.getLogger(__name__)

class ContentAnalyzer:
    """Analyzes content for entities, sentiment, and insights."""

    def __init__(self):
        self.sentiment_analyzer = SentimentIntensityAnalyzer()

        # Common tech/ML/AI terms for entity detection
        self.tech_terms = {
            'AI', 'ML', 'Deep Learning', 'Neural Networks', 'GPT', 'LLM',
            'Transformer', 'BERT', 'Attention', 'Backpropagation', 'Gradient Descent',
            'Python', 'TensorFlow', 'PyTorch', 'React', 'Vue', 'JavaScript', 'TypeScript',
            'API', 'REST', 'GraphQL', 'Docker', 'Kubernetes', 'AWS', 'GCP', 'Azure',
            'Microservices', 'Serverless', 'DevOps', 'CI/CD', 'Git', 'GitHub',
            'Agile', 'Scrum', 'Kanban', 'MVP', 'Product-Market Fit', 'SaaS',
            'B2B', 'B2C', 'IPO', 'VC', 'Angel', 'Startup', 'Unicorn', 'Pivot'
        }

        # Business concept terms
        self.business_terms = {
            'Revenue', 'Profit', 'Margin', 'Growth', 'Retention', 'Churn', 'CAC', 'LTV',
            'ROI', 'ARR', 'MRR', 'CAC', 'LTV', 'GMV', 'DAU', 'MAU', 'Active Users',
            'Engagement', 'Conversion', 'Funnel', 'A/B Testing', 'Metrics', 'KPI',
            'Strategy', 'Vision', 'Mission', 'Values', 'Culture', 'Leadership',
            'Marketing', 'Sales', 'Customer Success', 'Support', 'Product', 'Engineering'
        }

    def extract_entities(self, content: str) -> Dict[str, List[str]]:
        """
        Extract various types of entities from content.

        Returns:
            Dictionary with entity types as keys and entity lists as values
        """
        entities = {
            'people': [],
            'organizations': [],
            'locations': [],
            'tech_terms': [],
            'business_terms': [],
            'concepts': [],
            'numbers': [],
            'urls': []
        }

        # Clean content for analysis
        content = content.strip()

        # Extract URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`[\]]+'
        entities['urls'] = list(set(re.findall(url_pattern, content)))

        # Extract numbers (year, money, percentages)
        number_patterns = [
            r'\$\d+(?:,\d{3})*(?:\.\d{2})?',  # Money
            r'\d+(?:,\d{3})*(?:\.\d+)%?',  # Numbers and percentages
            r'\b(19|20)\d{2}\b'  # Years
        ]
        for pattern in number_patterns:
            entities['numbers'].extend(re.findall(pattern, content))

        # Tokenize and tag for named entity recognition
        try:
            # NLTK NER
            tokens = word_tokenize(content)
            tagged = pos_tag(tokens)
            tree = ne_chunk(tagged)

            # Extract named entities
            for subtree in tree:
                if hasattr(subtree, 'label'):
                    entity = ' '.join([token for token, pos in subtree.leaves()])
                    if subtree.label() == 'PERSON':
                        entities['people'].append(entity)
                    elif subtree.label() == 'ORGANIZATION':
                        entities['organizations'].append(entity)
                    elif subtree.label() == 'GPE':  # Geopolitical entity
                        entities['locations'].append(entity)
                    elif subtree.label() == 'FACILITY':
                        entities['organizations'].append(entity)
        except Exception as e:
            logger.warning(f"NLTK NER failed: {e}")

        # Extract tech and business terms (case-insensitive)
        content_lower = content.lower()

        for term in self.tech_terms:
            if term.lower() in content_lower:
                entities['tech_terms'].append(term)

        for term in self.business_terms:
            if term.lower() in content_lower:
                entities['business_terms'].append(term)

        # Extract key concepts (capitalized words that aren't at sentence start)
        # This is a simple heuristic - could be improved with more sophisticated NLP
        capitalized_words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
        # Filter out common words
        stop_words = {'The', 'This', 'That', 'These', 'Those', 'When', 'What', 'Where', 'Why', 'How', 'It', 'Its'}
        concepts = [w for w in capitalized_words if w not in stop_words and len(w) > 2]
        entities['concepts'] = list(set(concepts))

        # Clean up entity lists
        for key in entities:
            entities[key] = list(set(entities[key]))  # Remove duplicates
            entities[key].sort(key=lambda x: len(x), reverse=True)  # Sort by length

        return entities

    def analyze_sentiment(self, content: str) -> Dict[str, float]:
        """
        Analyze sentiment of content.

        Returns:
            Dictionary with sentiment scores
        """
        # Get sentiment scores from NLTK
        scores = self.sentiment_analyzer.polarity_scores(content)

        # Normalize scores to -1 to 1 range
        result = {
            'compound': scores['compound'],
            'positive': scores['pos'],
            'negative': scores['neg'],
            'neutral': scores['neu']
        }

        # Add sentiment category
        if scores['compound'] >= 0.05:
            result['category'] = 'positive'
        elif scores['compound'] <= -0.05:
            result['category'] = 'negative'
        else:
            result['category'] = 'neutral'

        return result

    def extract_key_phrases(self, content: str, min_phrase_length: int = 2, max_phrases: int = 20) -> List[str]:
        """
        Extract key phrases from content using n-gram analysis.

        Args:
            content: Text to analyze
            min_phrase_length: Minimum number of words in a phrase
            max_phrases: Maximum number of phrases to return

        Returns:
            List of key phrases sorted by importance
        """
        # Clean and tokenize
        sentences = sent_tokenize(content)
        phrases = []

        # Extract n-grams from sentences
        for sentence in sentences:
            # Tokenize and remove stop words
            tokens = word_tokenize(sentence.lower())
            # Simple stop word removal
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                         'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
                         'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
                         'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you',
                         'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who', 'when',
                         'where', 'why', 'how', 'my', 'your', 'our', 'their'}
            tokens = [t for t in tokens if t.isalpha() and t not in stop_words and len(t) > 2]

            # Generate n-grams
            for n in range(min_phrase_length, min(5, len(tokens) + 1)):
                for i in range(len(tokens) - n + 1):
                    phrase = ' '.join(tokens[i:i+n])
                    phrases.append(phrase)

        # Count phrase frequencies
        phrase_counts = Counter(phrases)

        # Filter by frequency and return top phrases
        min_frequency = 1 if len(phrase_counts) < 20 else 2
        common_phrases = [phrase for phrase, count in phrase_counts.items()
                         if count >= min_frequency]

        # Sort by length (longer phrases often more specific) and frequency
        common_phrases.sort(key=lambda x: (-phrase_counts[x], -len(x)))

        return common_phrases[:max_phrases]

    def estimate_read_time(self, content: str) -> int:
        """
        Estimate reading time in minutes.

        Args:
            content: Text to analyze

        Returns:
            Estimated reading time in minutes
        """
        # Count words
        word_count = len(word_tokenize(content))

        # Average reading speed: 200-250 words per minute
        words_per_minute = 225

        read_time = max(1, round(word_count / words_per_minute))
        return read_time

    def generate_summary(self, content: str, max_sentences: int = 3) -> Optional[str]:
        """
        Generate a simple extractive summary.

        Args:
            content: Text to summarize
            max_sentences: Maximum number of sentences in summary

        Returns:
            Summary text or None if content is too short
        """
        sentences = sent_tokenize(content)

        if len(sentences) <= max_sentences:
            return None  # Content is already short enough

        # Simple heuristic: select sentences with high content density
        # (sentences with more entities, numbers, and key phrases)
        scored_sentences = []

        for sentence in sentences:
            score = 0

            # Score for numbers
            score += len(re.findall(r'\d+', sentence)) * 2

            # Score for capitalized words (potential entities)
            score += len(re.findall(r'\b[A-Z][a-z]+\b', sentence))

            # Score for sentence length (prefer medium length)
            words = word_tokenize(sentence)
            if 10 <= len(words) <= 25:
                score += 1
            elif len(words) > 25:
                score += 0.5

            # Score for position (first and last sentences often important)
            if sentence == sentences[0]:
                score += 2
            elif sentence == sentences[-1]:
                score += 1

            scored_sentences.append((sentence, score))

        # Sort by score and select top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        selected_sentences = [s[0] for s in scored_sentences[:max_sentences]]

        # Maintain original order
        summary_sentences = []
        for sentence in sentences:
            if sentence in selected_sentences:
                summary_sentences.append(sentence)
                if len(summary_sentences) >= max_sentences:
                    break

        return ' '.join(summary_sentences)

    def extract_insights(self, content: str, metadata: Dict = None) -> Dict:
        """
        Extract comprehensive insights from content.

        Args:
            content: Text to analyze
            metadata: Artifact metadata

        Returns:
            Dictionary with all insights
        """
        insights = {
            'entities': self.extract_entities(content),
            'sentiment': self.analyze_sentiment(content),
            'key_phrases': self.extract_key_phrases(content),
            'read_time_minutes': self.estimate_read_time(content),
            'summary': self.generate_summary(content),
            'content_stats': self._get_content_stats(content)
        }

        # Add metadata-based insights
        if metadata:
            insights['source_analysis'] = self._analyze_source(metadata)

        return insights

    def _get_content_stats(self, content: str) -> Dict:
        """Get basic statistics about the content."""
        sentences = sent_tokenize(content)
        words = word_tokenize(content)

        return {
            'word_count': len(words),
            'sentence_count': len(sentences),
            'avg_words_per_sentence': round(len(words) / len(sentences), 1) if sentences else 0,
            'has_urls': bool(re.search(r'https?://', content)),
            'has_numbers': bool(re.search(r'\d+', content)),
            'question_count': len(re.findall(r'\?', content)),
            'exclamation_count': len(re.findall(r'!', content))
        }

    def _analyze_source(self, metadata: Dict) -> Dict:
        """Analyze the source based on metadata."""
        analysis = {
            'source_type': metadata.get('source_type', 'unknown'),
            'domain': None,
            'authority_score': 0.5  # Default neutral score
        }

        # Extract domain from URL if available
        if 'source_url' in metadata:
            url = metadata['source_url']
            if url.startswith('http'):
                domain = re.sub(r'https?://([^/]+).*', r'\1', url)
                analysis['domain'] = domain

                # Simple authority scoring based on domain patterns
                if any(d in domain for d in ['arxiv.org', 'nature.com', 'science.org', 'mit.edu']):
                    analysis['authority_score'] = 0.9
                elif any(d in domain for d in ['medium.com', 'github.com', 'stackoverflow.com']):
                    analysis['authority_score'] = 0.7
                elif domain in ['twitter.com', 'x.com']:
                    analysis['authority_score'] = 0.6

        return analysis