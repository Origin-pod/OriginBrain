#!/usr/bin/env python3
"""
Test script for Accelerated Search functionality
"""

import sys
import numpy as np
from src.brain.accelerated_search import AcceleratedSearch
from src.db.db import BrainDB

def test_accelerated_search():
    """Test the accelerated search functionality."""

    print("=== Testing Accelerated Search ===\n")

    # Initialize search
    search = AcceleratedSearch()
    db = BrainDB()

    # 1. Check initial stats
    print("1. Initial search index stats:")
    stats = search.get_index_stats()
    print(f"   Index size: {stats['index_size']}")
    print(f"   Last updated: {stats['last_updated']}")
    print()

    # 2. Rebuild index
    print("2. Rebuilding search index...")
    result = search.rebuild_index(force=True)
    if result.get("success"):
        print(f"   ✓ Indexed {result['indexed_artifacts']} artifacts")
        print(f"   ✓ Index size: {result['index_size']}")
    else:
        print(f"   ✗ {result.get('error', 'Unknown error')}")
    print()

    # 3. Get updated stats
    print("3. Updated search index stats:")
    stats = search.get_index_stats()
    print(f"   Index size: {stats['index_size']}")
    print(f"   Last updated: {stats['last_updated']}")
    print()

    # 4. Test search with dummy embedding
    print("4. Testing search with dummy embedding...")
    # Create a dummy embedding of correct dimension (384)
    dummy_embedding = np.random.rand(384).tolist()

    results = search.search_similar(dummy_embedding, k=5)
    print(f"   Found {len(results)} results")
    for i, result in enumerate(results[:3]):
        artifact = result["artifact"]
        print(f"   {i+1}. {artifact.get('title', 'Untitled')} (similarity: {result['distance']:.3f})")
    print()

    # 5. Test hybrid search
    print("5. Testing hybrid search...")
    results = search.search_hybrid("python", dummy_embedding, k=5)
    print(f"   Found {len(results)} results")
    for i, result in enumerate(results[:3]):
        artifact = result["artifact"]
        print(f"   {i+1}. {artifact.get('title', 'Untitled')} (score: {result['combined_score']:.3f})")
    print()

    # 6. Test filters
    print("6. Testing search with filters...")
    filters = {"consumption_status": ["unconsumed", "reading"]}
    results = search.search_similar(dummy_embedding, k=5, filters=filters)
    print(f"   Found {len(results)} unconsumed artifacts")
    print()

    # 7. Test optimization
    print("7. Optimizing search index...")
    result = search.optimize_index()
    if result.get("success"):
        print(f"   ✓ {result['message']}")
        if 'nprobe' in result:
            print(f"   ✓ nprobe: {result['nprobe']}")
        if 'index_type' in result:
            print(f"   ✓ Index type: {result['index_type']}")
    else:
        print(f"   ✗ {result.get('error', 'Unknown error')}")
    print()

    print("=== Test Complete ===")

if __name__ == "__main__":
    test_accelerated_search()