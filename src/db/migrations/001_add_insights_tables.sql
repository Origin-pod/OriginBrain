-- Migration 001: Add tables for Insights & Curation system
-- This migration adds tables needed for consumption tracking and relationship mapping

-- Extended artifact metadata table
CREATE TABLE IF NOT EXISTS artifacts_extended (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,

    -- Consumption tracking fields
    consumption_score FLOAT DEFAULT 0.0,
    importance_score FLOAT DEFAULT 0.0,
    consumption_status VARCHAR(20) DEFAULT 'unconsumed' CHECK (consumption_status IN ('unconsumed', 'reading', 'reviewed', 'applied', 'archived')),
    last_consumed_at TIMESTAMP,
    consumption_count INTEGER DEFAULT 0,
    estimated_read_time INTEGER, -- in minutes

    -- Enhanced metadata
    auto_tags TEXT[] DEFAULT '{}',
    entities JSONB DEFAULT '{}',
    insights JSONB DEFAULT '{}',
    summary TEXT,

    -- Relationship fields
    related_artifacts UUID[] DEFAULT '{}',
    parent_artifact UUID REFERENCES artifacts(id),

    -- Analytics
    view_count INTEGER DEFAULT 0,
    engagement_score FLOAT DEFAULT 0.0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Consumption events tracking
CREATE TABLE IF NOT EXISTS consumption_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,

    -- Event details
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('view', 'read', 'skim', 'highlight', 'note', 'apply', 'share')),
    duration_seconds INTEGER,

    -- Engagement metrics
    engagement_score FLOAT DEFAULT 0.0,
    scroll_depth FLOAT, -- 0.0 to 1.0

    -- Context
    session_id VARCHAR(255),
    source VARCHAR(50), -- dashboard, search, queue, etc.

    -- Additional data
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP DEFAULT NOW()
);

-- Artifact relationships
CREATE TABLE IF NOT EXISTS artifact_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_artifact UUID NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    target_artifact UUID NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,

    -- Relationship details
    relationship_type VARCHAR(50) NOT NULL CHECK (relationship_type IN ('similar', 'references', 'contradicts', 'extends', 'mentions', 'related')),
    strength FLOAT NOT NULL CHECK (strength >= 0.0 AND strength <= 1.0),

    -- Relationship metadata
    evidence TEXT,
    created_by VARCHAR(20) DEFAULT 'auto' CHECK (created_by IN ('auto', 'manual')),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),

    -- Prevent duplicate relationships
    UNIQUE(source_artifact, target_artifact, relationship_type)
);

-- User goals
CREATE TABLE IF NOT EXISTS user_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Goal details
    goal TEXT NOT NULL,
    description TEXT,
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),

    -- Goal metadata
    tags TEXT[] DEFAULT '{}',
    related_topics TEXT[] DEFAULT '{}',

    -- Status
    active BOOLEAN DEFAULT true,
    progress FLOAT DEFAULT 0.0 CHECK (progress >= 0.0 AND progress <= 1.0),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Consumption queue
CREATE TABLE IF NOT EXISTS consumption_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,

    -- Queue details
    queue_type VARCHAR(50) NOT NULL CHECK (queue_type IN ('daily', 'weekly', 'priority', 'goal_focused', 'trending', 'resurface')),
    score FLOAT NOT NULL,

    -- Recommendation reason
    reason TEXT,
    related_goal_id UUID REFERENCES user_goals(id),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    consumed_at TIMESTAMP
);

-- Indexes for performance

-- Artifacts extended indexes
CREATE INDEX IF NOT EXISTS idx_artifacts_extended_artifact_id ON artifacts_extended(artifact_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_extended_consumption_status ON artifacts_extended(consumption_status);
CREATE INDEX IF NOT EXISTS idx_artifacts_extended_auto_tags ON artifacts_extended USING GIN(auto_tags);
CREATE INDEX IF NOT EXISTS idx_artifacts_extended_importance_score ON artifacts_extended(importance_score DESC);

-- Consumption events indexes
CREATE INDEX IF NOT EXISTS idx_consumption_events_artifact_id ON consumption_events(artifact_id);
CREATE INDEX IF NOT EXISTS idx_consumption_events_created_at ON consumption_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_consumption_events_event_type ON consumption_events(event_type);

-- Relationships indexes
CREATE INDEX IF NOT EXISTS idx_relationships_source_artifact ON artifact_relationships(source_artifact);
CREATE INDEX IF NOT EXISTS idx_relationships_target_artifact ON artifact_relationships(target_artifact);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON artifact_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_relationships_strength ON artifact_relationships(strength DESC);

-- User goals indexes
CREATE INDEX IF NOT EXISTS idx_user_goals_active ON user_goals(active);
CREATE INDEX IF NOT EXISTS idx_user_goals_priority ON user_goals(priority DESC);

-- Queue indexes
CREATE INDEX IF NOT EXISTS idx_consumption_queue_artifact_id ON consumption_queue(artifact_id);
CREATE INDEX IF NOT EXISTS idx_consumption_queue_queue_type ON consumption_queue(queue_type);
CREATE INDEX IF NOT EXISTS idx_consumption_queue_score ON consumption_queue(score DESC);
CREATE INDEX IF NOT EXISTS idx_consumption_queue_expires_at ON consumption_queue(expires_at);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_artifacts_extended_updated_at BEFORE UPDATE ON artifacts_extended
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_goals_updated_at BEFORE UPDATE ON user_goals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();