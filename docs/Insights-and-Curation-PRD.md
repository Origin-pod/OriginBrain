# OriginBrain Insights & Curation PRD

## 1. Executive Summary

### Vision
Transform OriginBrain from a passive capture system into an **intelligent knowledge partner** that actively helps users consume, connect, and act on their captured information. The system will make captured content **consumption-ready** through automated curation, relationship mapping, and personalized insight generation.

### Problem Statement
- **Information Overload**: Users capture vast amounts of content but struggle to derive value from it
- **Context Gaps**: Captured information exists in isolation without meaningful connections
- **Consumption Friction**: Users don't know what to consume, when, or how it relates to their goals
- **Value Leakage**: Valuable insights remain buried and unactionable in the archive

### Solution Overview
Build an intelligent insights and curation layer that:
1. **Automatically surfaces relevant content** based on usage patterns and goals
2. **Maps relationships** between captures to create knowledge graphs
3. **Provides consumption guidance** through red/green signaling and priority scoring
4. **Tracks consumption patterns** to optimize future recommendations

## 2. Product Philosophy (Inspired by Sreyas Doshi)

### Core Principles

#### 2.1 Consumption-Centric Design
> "Products should be designed around the way customers actually consume value, not around predetermined usage patterns"

**Applied to OriginBrain:**
- Design around natural knowledge consumption patterns (spaced repetition, context-based learning)
- Align features with how users actually process and retain information
- Reduce friction between capture and consumption

#### 2.2 Growth Partnership
> "We think about consumption as a partnership - our success is directly tied to our customers' success in using our products"

**Applied to OriginBrain:**
- System learns and improves based on user consumption patterns
- Success measured by user's knowledge growth and actionable insights
- Create virtuous cycle: better curation → more consumption → better insights → more captures

#### 2.3 Simplified Complexity
> "The best consumption products make complex simple while maintaining transparency about value"

**Applied to OriginBrain:**
- Complex relationship mapping presented through simple visual cues
- Transparent scoring and recommendation logic
- Progressive disclosure of insights based on user readiness

## 3. User Stories & Use Cases

### Primary User Personas

#### The Researcher (Alex)
- **Goal**: Stay current in their field and connect disparate research findings
- **Pain Points**: Forgets important papers, misses connections between related work
- **Needs**: Automatic literature review, connection discovery, trend identification

#### The Product Manager (Taylor)
- **Goal**: Keep pulse on competitors, market trends, and user feedback
- **Pain Points**: Information scattered across sources, hard to synthesize insights
- **Needs**: Competitive intelligence clustering, trend analysis, actionable summaries

#### The Lifelong Learner (Jordan)
- **Goal**: Personal growth and skill development
- **Pain Points**: Loses track of learning progress, struggles to apply knowledge
- **Needs**: Learning path guidance, knowledge application tracking, spaced repetition

### Key User Stories

#### Consumption Stories
1. **"Show me what I need to read"** - Get personalized reading recommendations based on recent captures and goals
2. **"How does this relate to what I know?"** - See connections between new content and existing knowledge
3. **"What have I been ignoring?"** - Identify valuable content that hasn't been consumed
4. **"What's trending in my captures?"** - Discover emerging themes and patterns

#### Curation Stories
1. **"Organize my mess automatically"** - AI-powered tagging and clustering without manual effort
2. **"Mark what matters"** - Simple red/green signaling for importance and consumption status
3. **"Show me the gaps"** - Identify missing information or areas needing more research
4. **"Build my knowledge graph"** - Visualize connections and explore related concepts

## 4. System Architecture

### 4.1 Data Model Extensions

```sql
-- Extended Artifacts Model
CREATE TABLE artifacts_extended (
    id UUID PRIMARY KEY,
    content TEXT,
    metadata JSONB,

    -- Curation Fields
    consumption_score FLOAT DEFAULT 0.0,
    importance_score FLOAT DEFAULT 0.0,
    consumption_status VARCHAR(20) DEFAULT 'unconsumed', -- unconsumed, reading, reviewed, applied
    last_consumed_at TIMESTAMP,
    consumption_count INTEGER DEFAULT 0,

    -- Relationship Fields
    related_artifacts UUID[] DEFAULT '{}',
    parent_artifact UUID,
    child_artifacts UUID[] DEFAULT '{}',

    -- Insight Fields
    insights JSONB DEFAULT '{}',
    auto_tags TEXT[] DEFAULT '{}',
    themes TEXT[] DEFAULT '{}',

    -- Tracking Fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Foreign Key
    artifact_id UUID REFERENCES artifacts(id)
);

-- Consumption Tracking
CREATE TABLE consumption_events (
    id UUID PRIMARY KEY,
    artifact_id UUID REFERENCES artifacts_extended(id),
    event_type VARCHAR(50), -- view, read, highlight, note, apply
    duration_seconds INTEGER,
    engagement_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Knowledge Graph Edges
CREATE TABLE artifact_relationships (
    id UUID PRIMARY KEY,
    source_artifact UUID REFERENCES artifacts_extended(id),
    target_artifact UUID REFERENCES artifacts_extended(id),
    relationship_type VARCHAR(50), -- similar, references, contradicts, extends
    strength FLOAT,
    created_by VARCHAR(20) DEFAULT 'auto', -- auto, manual
    created_at TIMESTAMP DEFAULT NOW()
);

-- User Goals & Context
CREATE TABLE user_goals (
    id UUID PRIMARY KEY,
    goal TEXT NOT NULL,
    priority INTEGER DEFAULT 5,
    tags TEXT[] DEFAULT '{}',
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Consumption Queue
CREATE TABLE consumption_queue (
    id UUID PRIMARY KEY,
    artifact_id UUID REFERENCES artifacts_extended(id),
    queue_type VARCHAR(50), -- daily, weekly, priority, context
    score FLOAT,
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4.2 Insights Engine Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    INSIGHTS ENGINE                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   Content    │    │   Context    │    │  Behavioral  │ │
│  │   Analyzer   │    │   Analyzer   │    │  Analyzer    │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                   │                   │         │
│         └───────────────────┼───────────────────┘         │
│                             │                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            INSIGHT ORCHESTRATOR                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                             │                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │ Relationship │    │ Consumption  │    │    Trend     │ │
│  │   Mapper     │    │   Scorer     │    │   Detector   │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Core Components

#### Content Analyzer
- **Entity Extraction**: Identify people, places, concepts, companies
- **Topic Modeling**: Advanced theme discovery using LDA/NMF
- **Sentiment Analysis**: Emotional tone and opinion detection
- **Summarization**: TL;DR generation for quick consumption
- **Key Phrase Extraction**: Important concepts and terminology

#### Context Analyzer
- **Temporal Patterns**: Time-based relationships and trends
- **Source Authority**: Domain trustworthiness and expertise scoring
- **User Goals Alignment**: Mapping content to user objectives
- **Knowledge Gaps**: Identifying missing complementary information

#### Relationship Mapper
- **Semantic Similarity**: Content overlap and conceptual similarity
- **Reference Detection**: Citations, mentions, and direct references
- **Temporal Relationships**: How information evolves over time
- **Contradiction Detection**: Conflicting information identification

## 5. Feature Specifications

### 5.1 Intelligent Curation System

#### Auto-Tagging 2.0
```python
# Enhanced tagging algorithm
def generate_smart_tags(artifact):
    tags = set()

    # Content-based tags
    entities = extract_entities(artifact.content)
    concepts = extract_concepts(artifact.content)
    tags.update(entities, concepts)

    # Contextual tags
    if artifact.metadata['source_type'] == 'research_paper':
        tags.add('research')
        if has_methodology(artifact):
            tags.add('methodology')

    # Behavioral tags
    if is_part_of_trend(artifact):
        tags.add('trending')

    # Personal tags based on user goals
    aligned_goals = get_aligned_goals(artifact)
    tags.update([f'goal:{goal}' for goal in aligned_goals])

    return list(tags)
```

#### Relationship Graph
- **Automatic Linking**: Find and create relationships between artifacts
- **Visual Graph View**: Interactive knowledge network visualization
- **Path Discovery**: Find connections between seemingly unrelated topics
- **Influence Mapping**: Track how ideas spread and evolve

#### Red/Green Signaling System
- **Green (Consume)**: High relevance, high consumption priority
- **Yellow (Skim)**: Moderate relevance, quick review recommended
- **Red (Archive)**: Low relevance, skip for now but keep for reference
- **Purple (Critical)**: Urgent, requires immediate attention

### 5.2 Consumption Intelligence

#### Personalized Recommendation Engine
```python
class RecommendationEngine:
    def __init__(self):
        self.user_behavior = UserBehaviorModel()
        self.content_similarity = ContentSimilarity()
        self.goal_alignment = GoalAlignment()

    def get_recommendations(self, user, context):
        # Factor 1: Consumption patterns (what user actually reads)
        behavior_score = self.user_behavior.predict_engagement(user, artifacts)

        # Factor 2: Content relationships (what's related to consumed content)
        similarity_score = self.content_similarity.find_related(artifacts, user.consumed)

        # Factor 3: Goal alignment (what helps achieve current objectives)
        goal_score = self.goal_alignment.calculate_score(artifacts, user.active_goals)

        # Combine with temporal factors (recency, trends)
        final_scores = weighted_average([
            (behavior_score, 0.4),
            (similarity_score, 0.3),
            (goal_score, 0.2),
            (temporal_score, 0.1)
        ])

        return rank_and_filter(final_scores)
```

#### Consumption Tracking
- **Reading Progress**: Track how much of each artifact is consumed
- **Engagement Metrics**: Time spent, highlights, notes, shares
- **Application Tracking**: When knowledge is applied to projects
- **Retention Scoring**: Spaced repetition for long-term memory

#### Smart Queues
1. **Daily Digest**: 5-10 items for daily consumption
2. **Weekly Review**: Deeper dive into weekly themes
3. **Goal-Focused**: Items aligned with specific objectives
4. **Trending Topics**: Emerging patterns in captures
5. **Knowledge Gaps**: Areas needing more information

### 5.3 Insight Generation

#### Automated Insights
- **Trend Reports**: Weekly/monthly summaries of captured themes
- **Knowledge Clusters**: Grouped insights on specific topics
- **Action Items**: Extract actionable tasks from captured content
- **Question Generation**: Create research questions based on gaps

#### Visual Dashboards
- **Consumption Heatmap**: Visual representation of reading patterns
- **Knowledge Graph**: Interactive network of connected ideas
- **Trend Visualization**: How topics evolve over time
- **Goal Progress**: Tracking advancement toward objectives

## 6. User Experience Design

### 6.1 Consumption Interface

#### Main Dashboard Redesign
```
┌─────────────────────────────────────────────────────────────┐
│  Today's Consumption Queue          ┌─────────────────────┐ │
│  ┌─────────────────────────────────┐ │  Knowledge Graph   │ │
│  │ 🟢 [5] High Priority            │ │  ┌───────┐         │ │
│  │ 🟡 [3] Quick Review             │ │  │   AI  │         │ │
│  │ 🟣 [1] Critical                 │ │  │ Ethics│         │ │
│  │ ─────────────────────────────── │ │  └─┬─┬───┘         │ │
│  │ 📈 Trending: "LLM Reasoning"    │ │    │ │             │ │
│  │ 🎯 Goal: "Product Strategy"     │ │ ┌──┘ └───┐         │ │
│  └─────────────────────────────────┘ │ │ChatGPT  │         │ │
│                                     │ └─────────┘         │ │
│  Recent Activity                    └─────────────────────┘ │
│  ✅ Read "Attention is All You Need"                      │
│  📝 Noted "3 key takeaways from..."                       │
│  🔄 Reviewing "Product-Market Fit Framework"              │
└─────────────────────────────────────────────────────────────┘
```

#### Artifact View Enhancement
```html
<div class="artifact-view">
  <div class="consumption-header">
    <span class="priority-indicator green">HIGH PRIORITY</span>
    <span class="consumption-time">5 min read</span>
    <span class="engagement-predictor">92% match</span>
  </div>

  <div class="related-content">
    <h4>Related to your reading:</h4>
    <div class="related-pills">
      <span class="pill">GPT-4 Technical Report</span>
      <span class="pill">Transformer Architecture</span>
      <span class="pill">Scaling Laws</span>
    </div>
  </div>

  <div class="consumption-actions">
    <button class="mark-read">✅ Mark as Consumed</button>
    <button class="quick-note">📝 Add Note</button>
    <button class="apply-knowledge">🎯 Apply to Project</button>
  </div>

  <div class="ai-insights">
    <h4>Key Insights:</h4>
    <ul>
      <li>This extends concepts from "Attention is All You Need"</li>
      <li>3 actionable frameworks for your product strategy</li>
      <li>Contradicts previous paper on model limitations</li>
    </ul>
  </div>
</div>
```

### 6.2 Curation Interface

#### Relationship Management
- **Visual Graph Builder**: Drag-and-drop relationship creation
- **Bulk Curation**: Select multiple items for batch operations
- **Smart Suggestions**: AI-recommended connections and tags
- **Importance Scoring**: Simple sliders for priority adjustment

#### Goal Management
```
┌─────────────────────────────────────────────────────────────┐
│  Active Goals                      Progress    Next Action  │
│  ─────────────────────────────────────────────────────────── │
│  🎯 Master LLM Architecture         ████████░░  Read paper   │
│  🎯 Improve Product Strategy        ████░░░░░░  Capture more │
│  🎯 Understand AI Ethics            ██░░░░░░░░  Find sources │
└─────────────────────────────────────────────────────────────┘
```

## 7. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4)
**Objective**: Build core insights infrastructure

**Technical Tasks**:
1. **Database Schema Updates**
   - Extend artifacts table with curation fields
   - Implement consumption_events tracking
   - Create artifact_relationships table
   - Add user_goals and consumption_queue tables

2. **Basic Content Analysis**
   - Implement enhanced entity extraction
   - Add sentiment analysis
   - Create basic summarization
   - Extend automatic tagging

3. **Relationship Mapping V1**
   - Semantic similarity calculation
   - Basic reference detection
   - Simple relationship strength scoring

**Features Delivered**:
- Enhanced metadata on all artifacts
- Basic auto-tagging improvements
- Simple relationship detection
- Consumption tracking foundation

### Phase 2: Intelligence Layer (Weeks 5-8)
**Objective**: Add AI-powered insights and recommendations

**Technical Tasks**:
1. **Insights Engine Core**
   - Implement content analyzer module
   - Build context analyzer
   - Create relationship mapper
   - Develop consumption scorer

2. **Recommendation System**
   - User behavior modeling
   - Content similarity algorithms
   - Goal alignment scoring
   - Personalized ranking

3. **API Extensions**
   - `/insights/recommendations` endpoint
   - `/insights/relationships` endpoint
   - `/insights/consumption-queue` endpoint
   - `/insights/trends` endpoint

**Features Delivered**:
- Personalized consumption queue
- Basic recommendation engine
- Relationship viewing
- Trend detection

### Phase 3: User Interface (Weeks 9-12)
**Objective**: Build consumption-focused UI

**Technical Tasks**:
1. **Frontend Components**
   - Consumption dashboard redesign
   - Artifact view enhancement
   - Relationship graph visualization
   - Goal management interface

2. **Interactive Features**
   - Red/green signaling UI
   - Consumption tracking
   - Bulk curation tools
   - Quick note/action interface

3. **Visualizations**
   - Knowledge graph explorer
   - Trend analysis charts
   - Consumption heatmaps
   - Goal progress tracking

**Features Delivered**:
- Full consumption dashboard
- Interactive knowledge graph
- Smart queues and recommendations
- Consumption tracking and analytics

### Phase 4: Advanced Features (Weeks 13-16)
**Objective**: Polish and advanced capabilities

**Technical Tasks**:
1. **Advanced Analytics**
   - Retention modeling
   - Knowledge gap detection
   - Influence propagation
   - Predictive insights

2. **Automation Enhancements**
   - Smart newsletter generation
   - Automated research briefs
   - Goal-based collection building
   - Integration with external tools

3. **Performance Optimization**
   - Vector search optimization
   - Real-time relationship updates
   - Caching strategies
   - Background job optimization

**Features Delivered**:
- Advanced insight reports
- Automated knowledge synthesis
- External integrations
- Optimized performance

## 8. Success Metrics

### Consumption Metrics
- **Consumption Rate**: % of captured items actually consumed
- **Engagement Depth**: Average time spent per artifact
- **Application Rate**: % of consumed knowledge applied
- **Retention Score**: Long-term knowledge retention

### Curation Quality
- **Tag Accuracy**: Precision/recall of auto-tagging
- **Relationship Precision**: Accuracy of detected connections
- **Relevance Score**: User satisfaction with recommendations
- **Curation Efficiency**: Time saved vs manual curation

### User Behavior
- **Daily Active Users**: Consistent engagement patterns
- **Feature Adoption**: Usage of advanced features
- **Knowledge Growth**: Measurable improvement in domain expertise
- **Goal Achievement**: % of user goals completed with system help

## 9. Technical Considerations

### Performance
- **Vector Search Optimization**: Use Faiss or Pinecone for similarity search
- **Caching Strategy**: Redis for frequent queries and recommendations
- **Background Processing**: Async jobs for heavy analysis tasks
- **Database Indexing**: Optimized queries for relationship traversal

### Scalability
- **Microservices Architecture**: Separate insights service from core app
- **Event-Driven Updates**: Kafka/Redis streams for real-time updates
- **Horizontal Scaling**: Container-based deployment with load balancing
- **Data Partitioning**: Time-based partitioning for consumption events

### Privacy
- **Local Processing**: Keep sensitive analysis on-device when possible
- **Data Minimization**: Only collect necessary consumption data
- **User Control**: Clear controls for data deletion and export
- **Transparency**: Explainable AI for insights and recommendations

## 10. Future Extensions

### Advanced AI Integration
- **Question Answering**: Chat directly with your knowledge base
- **Synthesis Generation**: Create new content from captured knowledge
- **Predictive Curation**: Anticipate information needs based on projects
- **Cross-Modal Understanding**: Connect text, images, and audio captures

### Collaboration Features
- **Team Knowledge Graphs**: Shared insights and curation
- **Collaborative Filtering**: Recommendations based on similar users
- **Knowledge Exchange**: Share specific insights with teammates
- **Group Curation**: Team-based tagging and relationship building

### Platform Integration
- **Browser Extension Enhancement**: In-page insights and recommendations
- **Mobile App**: On-the-go consumption and capture
- **API Ecosystem**: Third-party integrations and workflows
- **Notification System**: Proactive insights delivered via preferred channels

---

## Conclusion

This PRD outlines a comprehensive approach to transforming OriginBrain from a simple capture system into an intelligent knowledge partner. By focusing on consumption-centric design, automated curation, and relationship mapping, we can help users derive significantly more value from their captured information.

The implementation roadmap provides a clear path from foundational enhancements to advanced AI-powered features, with regular deliverables that demonstrate increasing value to users. The success metrics ensure we're building features that genuinely improve knowledge consumption and application, not just adding complexity for its own sake.

By embracing Sreyas Doshi's philosophy of consumption-centric design and partnership with users, we can create a system that not only captures information but actively helps users grow their knowledge and achieve their goals.