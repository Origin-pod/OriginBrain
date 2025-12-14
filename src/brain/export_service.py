"""
Export Service for OriginBrain.
Handles exporting artifacts and knowledge graph in various formats.
"""

import json
import csv
import logging
from datetime import datetime
from io import StringIO
from typing import List, Dict, Optional, Any
from src.db.db import BrainDB

logger = logging.getLogger(__name__)

class ExportService:
    """Service for exporting data in various formats."""

    def __init__(self):
        self.db = BrainDB()

    def export_artifacts(self, format_type: str, artifact_ids: List[str] = None,
                        filters: Dict = None) -> Dict:
        """
        Export artifacts in specified format.

        Args:
            format_type: Format to export (json, csv, markdown, pdf)
            artifact_ids: Specific artifact IDs to export
            filters: Filters to apply

        Returns:
            Dictionary with export results
        """
        # Get artifacts
        if artifact_ids:
            artifacts = []
            for artifact_id in artifact_ids:
                artifact = self.db.get_artifact_extended(artifact_id)
                if artifact:
                    artifacts.append(artifact)
        else:
            artifacts = self.db.get_artifacts_with_extended(limit=None)

        # Apply filters if provided
        if filters:
            artifacts = self._apply_filters(artifacts, filters)

        # Export based on format
        if format_type.lower() == 'json':
            result = self._export_json(artifacts)
        elif format_type.lower() == 'csv':
            result = self._export_csv(artifacts)
        elif format_type.lower() == 'markdown':
            result = self._export_markdown(artifacts)
        elif format_type.lower() == 'pdf':
            result = self._export_pdf(artifacts)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

        return {
            'format': format_type,
            'count': len(artifacts),
            'exported_at': datetime.now().isoformat(),
            'result': result
        }

    def export_knowledge_graph(self, format_type: str) -> Dict:
        """
        Export knowledge graph data.

        Args:
            format_type: Format to export (json, graphml, gexf)

        Returns:
            Dictionary with export results
        """
        from src.brain.relationship_mapper import RelationshipMapper

        mapper = RelationshipMapper()
        graph_data = mapper.build_knowledge_graph()

        if format_type.lower() == 'json':
            result = self._export_graph_json(graph_data)
        elif format_type.lower() == 'graphml':
            result = self._export_graph_graphml(graph_data)
        elif format_type.lower() == 'gexf':
            result = self._export_graph_gexf(graph_data)
        else:
            raise ValueError(f"Unsupported graph format: {format_type}")

        return {
            'format': format_type,
            'nodes_count': len(graph_data.get('nodes', [])),
            'edges_count': len(graph_data.get('edges', [])),
            'exported_at': datetime.now().isoformat(),
            'result': result
        }

    def _export_json(self, artifacts: List[Dict]) -> str:
        """Export artifacts as JSON."""
        # Clean artifacts for JSON serialization
        clean_artifacts = []
        for artifact in artifacts:
            clean_artifact = {
                'id': artifact.get('id'),
                'title': artifact.get('title'),
                'content': artifact.get('content'),
                'metadata': artifact.get('metadata'),
                'created_at': artifact.get('created_at').isoformat() if artifact.get('created_at') else None,
                'consumption_status': artifact.get('consumption_status'),
                'importance_score': artifact.get('importance_score'),
                'consumption_score': artifact.get('consumption_score'),
                'engagement_score': artifact.get('engagement_score'),
                'auto_tags': artifact.get('auto_tags'),
                'entities': artifact.get('entities'),
                'insights': artifact.get('insights'),
                'summary': artifact.get('summary')
            }
            clean_artifacts.append(clean_artifact)

        return json.dumps(clean_artifacts, indent=2, default=str)

    def _export_csv(self, artifacts: List[Dict]) -> str:
        """Export artifacts as CSV."""
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        header = ['ID', 'Title', 'Type', 'Consumption Status', 'Importance Score',
                  'Created At', 'Tags', 'Read Time', 'Summary']
        writer.writerow(header)

        # Write rows
        for artifact in artifacts:
            metadata = artifact.get('metadata', {})
            row = [
                artifact.get('id', ''),
                artifact.get('title', '')[:100],  # Limit length
                metadata.get('source_type', ''),
                artifact.get('consumption_status', 'unconsumed'),
                artifact.get('importance_score', 0),
                artifact.get('created_at', ''),
                ', '.join(artifact.get('auto_tags', [])) if artifact.get('auto_tags') else '',
                artifact.get('estimated_read_time', 0),
                (artifact.get('summary', '') or '')[:200]  # Limit length
            ]
            writer.writerow(row)

        return output.getvalue()

    def _export_markdown(self, artifacts: List[Dict]) -> str:
        """Export artifacts as Markdown."""
        md_lines = ["# OriginBrain Export", ""]
        md_lines.append(f"Exported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md_lines.append(f"Total artifacts: {len(artifacts)}")
        md_lines.append("")

        for artifact in artifacts:
            md_lines.append(f"## {artifact.get('title', 'Untitled')}")

            metadata = artifact.get('metadata', {})
            if metadata.get('source_url'):
                md_lines.append(f"**Source:** [{metadata['source_url']}]({metadata['source_url']})")

            md_lines.append(f"**Status:** {artifact.get('consumption_status', 'unconsumed').title()}")
            md_lines.append(f"**Importance:** {artifact.get('importance_score', 0):.2f}/10")

            created_at = artifact.get('created_at')
            if created_at:
                md_lines.append(f"**Created:** {created_at.strftime('%Y-%m-%d')}")

            # Tags
            tags = artifact.get('auto_tags', [])
            if tags:
                md_lines.append(f"**Tags:** {' | '.join(tags)}")

            # Summary if available
            summary = artifact.get('summary')
            if summary:
                md_lines.append(f"**Summary:** {summary}")
                md_lines.append("")

            # Content (truncated for readability)
            content = artifact.get('content', '')
            if content:
                md_lines.append("### Content")
                # Truncate long content
                if len(content) > 1000:
                    content = content[:1000] + "..."
                md_lines.append(content)
                md_lines.append("")

            # Entities
            entities = artifact.get('entities', {})
            if entities:
                md_lines.append("### Entities")
                for entity_type, entity_list in entities.items():
                    if entity_list and isinstance(entity_list, list):
                        md_lines.append(f"**{entity_type.title()}:** {', '.join(entity_list[:5])}")
                md_lines.append("")

            md_lines.append("---")
            md_lines.append("")

        return '\n'.join(md_lines)

    def _export_pdf(self, artifacts: List[Dict]) -> Dict:
        """Export artifacts as PDF (placeholder implementation)."""
        # For now, return a message that PDF export requires additional setup
        return {
            'message': "PDF export requires additional dependencies. Please use JSON or Markdown formats for now.",
            'alternatives': ['json', 'markdown', 'csv']
        }

    def _export_graph_json(self, graph_data: Dict) -> str:
        """Export graph as JSON."""
        return json.dumps(graph_data, indent=2, default=str)

    def _export_graph_graphml(self, graph_data: Dict) -> str:
        """Export graph as GraphML."""
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append('<graphml xmlns="http://graphml.graphdrawing.org/xmlns" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"')
        lines.append('xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">')
        lines.append('<graph id="G" edgedefault="directed">')

        # Add nodes
        lines.append('<node id="n0"><key id="n0" for="node" attr.name="description"/>')
        lines.append('<graph id="n0" edgedefault="directed">')
        lines.append('<node id="n1"><key id="n1" for="node" attr.name="description"/>')
        lines.append('<graph id="n1" edgedefault="directed">')

        for node in graph_data.get('nodes', []):
            lines.append(f'<node id="{node["id"]}">')
            lines.append(f'  <data key="d5">{node.get("label", "")}</data>')
            lines.append(f'  <data key="d6">{node.get("type", "")}</data>')
            lines.append(f'  <data key="d10">{node.get("importance", 0)}</data>')
            lines.append('</node>')

        # Add edges
        lines.append('<edge id="e0"><key id="e0" for="edge" attr.name="description"/>')
        lines.append('<key id="e0" for="edge" attr.name="weight"/>')

        for edge in graph_data.get('edges', []):
            lines.append(f'<edge source="{edge["source"]}" target="{edge["target"]}">')
            lines.append(f'  <data key="d10">{edge.get("weight", 1)}</data>')
            lines.append(f'  <data key="d11">{edge.get("type", "related")}</data>')
            lines.append('</edge>')

        lines.append('</graph>')
        lines.append('</graph>')

        return '\n'.join(lines)

    def _export_graph_gexf(self, graph_data: Dict) -> str:
        """Export graph as GEXF."""
        # Simplified GEXF export
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append('<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">')
        lines.append('<meta lastmodifieddate="2023-01-01">')
        lines.append('<graph mode="static" defaultedgettype="directed">')

        # Add nodes
        for node in graph_data.get('nodes', []):
            lines.append(f'<node id="{node["id"]}" label="{node.get("label", "")}"/>')

        # Add edges
        for edge in graph_data.get('edges', []):
            lines.append(f'<edge source="{edge["source"]}" target="{edge["target"]}" weight="{edge.get("weight", 1)}" label="{edge.get("type", "related")}"/>')

        lines.append('</graph>')
        lines.append('</gexf>')

        return '\n'.join(lines)

    def _apply_filters(self, artifacts: List[Dict], filters: Dict) -> List[Dict]:
        """Apply filters to artifacts list."""
        filtered = artifacts

        # Filter by consumption status
        if 'consumption_status' in filters:
            status = filters['consumption_status']
            filtered = [a for a in filtered if a.get('consumption_status') == status]

        # Filter by importance score range
        if 'min_importance' in filters:
            min_score = filters['min_importance']
            filtered = [a for a in filtered if a.get('importance_score', 0) >= min_score]

        if 'max_importance' in filters:
            max_score = filters['max_importance']
            filtered = [a for a in filtered if a.get('importance_score', 0) <= max_score]

        # Filter by date range
        if 'date_from' in filters:
            date_from = filters['date_from']
            filtered = [a for a in filtered if a.get('created_at') and a['created_at'] >= date_from]

        if 'date_to' in filters:
            date_to = filters['date_to']
            filtered = [a for a in filtered if a.get('created_at') and a['created_at'] <= date_to]

        # Filter by tags
        if 'tags' in filters:
            required_tags = filters['tags']
            filtered = [a for a in filtered if a.get('auto_tags') and
                        any(tag in a['auto_tags'] for tag in required_tags)]

        return filtered

    def generate_insights_report_file(self, report: Dict, format_type: str = 'markdown') -> str:
        """
        Generate a formatted insights report file.

        Args:
            report: The report data
            format_type: Format for the report (markdown, html, txt)

        Returns:
            Formatted report as string
        """
        if format_type.lower() == 'markdown':
            return self._generate_markdown_report(report)
        elif format_type.lower() == 'html':
            return self._generate_html_report(report)
        elif format_type.lower() == 'txt':
            return self._generate_text_report(report)
        else:
            raise ValueError(f"Unsupported report format: {format_type}")

    def _generate_markdown_report(self, report: Dict) -> str:
        """Generate Markdown formatted report."""
        lines = ["# OriginBrain Insights Report", ""]

        # Summary section
        summary = report.get('summary', {})
        lines.append("## Summary")
        lines.append(f"- **Total Artifacts Analyzed:** {summary.get('total_artifacts', 0)}")
        lines.append(f"- **Date Range:** {summary.get('date_range', 'N/A')}")
        lines.append(f"- **Generated:** {summary.get('report_generated', 'N/A')}")
        lines.append("")

        # Key Themes
        themes = report.get('key_themes', [])
        if themes:
            lines.append("## Key Themes")
            for i, theme in enumerate(themes[:10], 1):
                lines.append(f"{i}. **{theme['term']}** - {theme['count']} mentions")
            lines.append("")

        # Sentiment Analysis
        sentiment = report.get('sentiment_analysis', {})
        if sentiment:
            lines.append("## Sentiment Analysis")
            lines.append(f"- **Positive:** {sentiment.get('positive', 0)} ({sentiment.get('positive_ratio', 0):.1%})")
            lines.append(f"- **Negative:** {sentiment.get('negative', 0)} ({sentiment.get('negative_ratio', 0):.1%})")
            lines.append(f"- **Neutral:** {sentiment.get('neutral', 0)}")
            lines.append("")

        # Entity Analysis
        entity_analysis = report.get('entity_analysis', {})
        if entity_analysis and entity_analysis.get('top_entities'):
            lines.append("## Top Entities")
            for i, entity in enumerate(entity_analysis['top_entities'][:10], 1):
                lines.append(f"{i}. **{entity['entity']}** - {entity['count']} occurrences")
            lines.append("")

        # Recommendations
        recommendations = report.get('recommendations', [])
        if recommendations:
            lines.append("## Recommendations")
            for rec in recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        # Consumption Gaps
        gaps = report.get('consumption_gaps', [])
        if gaps:
            lines.append("## Consumption Gaps")
            for gap in gaps:
                lines.append(f"- {gap}")
            lines.append("")

        return '\n'.join(lines)

    def _generate_html_report(self, report: Dict) -> str:
        """Generate HTML formatted report."""
        # Simple HTML template
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>OriginBrain Insights Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .section {{ margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #e3f2fd; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>OriginBrain Insights Report</h1>

    <div class="summary">
        <h2>Summary</h2>
        <div class="metric">Total Artifacts: {report.get('summary', {}).get('total_artifacts', 0)}</div>
        <div class="metric">Generated: {report.get('summary', {}).get('report_generated', 'N/A')}</div>
    </div>

    <div class="section">
        <h2>Key Themes</h2>
        {self._format_themes_html(report.get('key_themes', []))}
    </div>

    <div class="section">
        <h2>Sentiment Analysis</h2>
        {self._format_sentiment_html(report.get('sentiment_analysis', {}))}
    </div>

    <div class="section">
        <h2>Recommendations</h2>
        <ul>
            {self._format_recommendations_html(report.get('recommendations', []))}
        </ul>
    </div>
</body>
</html>
        """
        return html

    def _generate_text_report(self, report: Dict) -> str:
        """Generate plain text report."""
        lines = ["ORIGINBRAIN INSIGHTS REPORT", "=" * 40, ""]

        # Summary
        summary = report.get('summary', {})
        lines.append(f"Total Artifacts Analyzed: {summary.get('total_artifacts', 0)}")
        lines.append(f"Date Range: {summary.get('date_range', 'N/A')}")
        lines.append(f"Generated: {summary.get('report_generated', 'N/A')}")
        lines.append("")

        # Themes
        themes = report.get('key_themes', [])
        if themes:
            lines.append("KEY THEMES:")
            for theme in themes[:10]:
                lines.append(f"  • {theme['term']} ({theme['count']} mentions)")
            lines.append("")

        return '\n'.join(lines)

    def _format_themes_html(self, themes: List[Dict]) -> str:
        """Format themes for HTML."""
        if not themes:
            return "<p>No themes identified</p>"
        return '<br>'.join([f"<span>{theme['term']} ({theme['count']})</span>" for theme in themes])

    def _format_sentiment_html(self, sentiment: Dict) -> str:
        """Format sentiment for HTML."""
        return f"""
        <div class="metric">Positive: {sentiment.get('positive', 0)} ({sentiment.get('positive_ratio', 0):.1%})</div>
        <div class="metric">Negative: {sentiment.get('negative', 0)} ({sentiment.get('negative_ratio', 0):.1%})</div>
        <div class="metric">Neutral: {sentiment.get('neutral', 0)}</div>
        """

    def _format_recommendations_html(self, recommendations: List[str]) -> str:
        """Format recommendations for HTML."""
        if not recommendations:
            return "<p>No recommendations</p>"
        return '\n'.join([f"<li>{rec}</li>" for rec in recommendations])