#!/usr/bin/env python3
"""
Create test data with embeddings for testing accelerated search
"""

import uuid
import numpy as np
from src.db.db import BrainDB

def create_test_data():
    """Create test artifacts with embeddings."""

    print("=== Creating Test Data ===\n")

    db = BrainDB()

    # Create a test drop first
    drop_id = db.insert_drop("test", '{"source": "test"}', "Test data for accelerated search")
    print(f"Created drop: {drop_id}")

    # Create test artifacts
    test_artifacts = [
        {
            "title": "Introduction to Machine Learning",
            "content": "Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data.",
            "tag": "ml"
        },
        {
            "title": "Python Programming Best Practices",
            "content": "Python is a versatile programming language with many best practices for writing clean and maintainable code.",
            "tag": "python"
        },
        {
            "title": "Deep Learning with Neural Networks",
            "content": "Deep learning uses neural networks with multiple layers to learn complex patterns from data.",
            "tag": "dl"
        },
        {
            "title": "Web Development with React",
            "content": "React is a popular JavaScript library for building user interfaces, particularly web applications.",
            "tag": "react"
        },
        {
            "title": "Data Science Fundamentals",
            "content": "Data science combines statistics, programming, and domain expertise to extract insights from data.",
            "tag": "data"
        }
    ]

    artifact_ids = []

    for artifact_data in test_artifacts:
        # Create artifact
        import json
        artifact_id = db.insert_artifact(
            drop_id=drop_id,
            title=artifact_data["title"],
            content=artifact_data["content"],
            metadata=json.dumps({"tag": artifact_data["tag"], "test": True})
        )
        artifact_ids.append(artifact_id)

        # Create dummy embedding (1536 dimensions for OpenAI compatibility)
        dummy_embedding = np.random.rand(1536).tolist()

        # Insert embedding as JSON
        conn = db.get_connection()
        with conn.cursor() as cur:
            import json
            embedding_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO embeddings (id, artifact_id, vector, model)
                VALUES (%s, %s, %s, %s)
            """, (embedding_id, artifact_id, json.dumps(dummy_embedding), "test-model"))

        print(f"Created artifact: {artifact_data['title']}")

    print(f"\nCreated {len(artifact_ids)} test artifacts with embeddings")
    print("\n=== Test Data Created ===")

if __name__ == "__main__":
    create_test_data()