"""
Semantic Cache Demo Script

Demonstrates the semantic cache functionality without requiring full agent initialization.
This script can run independently to validate the cache implementation.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def demo_cache_basic():
    """Demonstrate basic cache operations"""
    print("=" * 60)
    print("Semantic Cache Demo - Basic Operations")
    print("=" * 60)
    
    try:
        from memory.cache_manager import SemanticCacheManager
        import tempfile
        
        # Create temporary cache directory
        with tempfile.TemporaryDirectory() as tmpdir:
            print(f"\n📁 Using temporary cache directory: {tmpdir}")
            
            # Initialize cache
            cache = SemanticCacheManager(
                index_path=f"{tmpdir}/cache_index.faiss",
                store_path=f"{tmpdir}/cache_store.parquet",
                similarity_threshold=0.9,
                max_cache_size=10,
                ttl_hours=24
            )
            print("✓ Cache initialized")
            
            # Store first entry
            print("\n📝 Storing query-response pair...")
            entry_id = cache.store(
                query="What is Python?",
                response_text="Python is a high-level, interpreted programming language.",
                conversation_id="demo_001",
                tools_used=["knowledge_base"],
                usage={"prompt_tokens": 15, "completion_tokens": 12, "total_tokens": 27},
                iterations=1
            )
            print(f"   Entry ID: {entry_id}")
            
            # Exact match query
            print("\n🔍 Query 1: Exact match")
            result1 = cache.get("What is Python?")
            if result1:
                print(f"   ✓ CACHE HIT!")
                print(f"   Similarity: {result1['similarity_score']:.3f}")
                print(f"   Response: {result1['response']['response_text']}")
            else:
                print("   ✗ Cache miss")
            
            # Similar query (should hit if similarity > 0.9)
            print("\n🔍 Query 2: Similar query")
            result2 = cache.get("What's Python?")
            if result2:
                print(f"   ✓ CACHE HIT!")
                print(f"   Similarity: {result2['similarity_score']:.3f}")
                print(f"   Response: {result2['response']['response_text']}")
                print(f"   Hit count: {result2['hit_count']}")
            else:
                print("   ✗ Cache miss (similarity too low)")
            
            # Dissimilar query
            print("\n🔍 Query 3: Dissimilar query")
            result3 = cache.get("How to cook pasta?")
            if result3:
                print(f"   ✓ Cache hit (unexpected)")
            else:
                print("   ✗ Cache miss (expected)")
            
            # Cache metrics
            print("\n📊 Cache Metrics:")
            metrics = cache.get_metrics()
            print(f"   Total queries: {metrics['total_queries']}")
            print(f"   Cache hits: {metrics['cache_hits']}")
            print(f"   Cache misses: {metrics['cache_misses']}")
            print(f"   Hit rate: {metrics['hit_rate']:.1%}")
            if metrics['cache_hits'] > 0:
                print(f"   Avg similarity on hit: {metrics['avg_similarity_on_hit']:.3f}")
            
            # Cache statistics
            print("\n📈 Cache Statistics:")
            stats = cache.get_stats()
            print(f"   Total entries: {stats['total_entries']}")
            print(f"   Index size: {stats['index_size']}")
            print(f"   Similarity threshold: {stats['similarity_threshold']}")
            print(f"   Max cache size: {stats['max_cache_size']}")
            print(f"   TTL (hours): {stats['ttl_hours']}")
            
            print("\n✅ Demo completed successfully!")
            
    except ImportError as e:
        print(f"\n❌ Error: Missing dependencies")
        print(f"   {e}")
        print("\nPlease install required packages:")
        print("   pip install faiss-cpu sentence-transformers pandas pyarrow")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def demo_cache_advanced():
    """Demonstrate advanced cache features"""
    print("\n" + "=" * 60)
    print("Semantic Cache Demo - Advanced Features")
    print("=" * 60)
    
    try:
        from memory.cache_manager import SemanticCacheManager
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SemanticCacheManager(
                index_path=f"{tmpdir}/cache_index.faiss",
                store_path=f"{tmpdir}/cache_store.parquet",
                similarity_threshold=0.9,
                max_cache_size=5,  # Small size to demonstrate eviction
                ttl_hours=24
            )
            
            # Store multiple entries
            print("\n📝 Storing multiple entries...")
            for i in range(7):
                cache.store(
                    query=f"Question {i}: What is topic {i}?",
                    response_text=f"Answer {i}: This is the response about topic {i}.",
                    conversation_id=f"conv_{i}"
                )
            
            print(f"   Stored 7 entries (max size: 5)")
            stats = cache.get_stats()
            print(f"   Current entries: {stats['total_entries']} (should be 5 due to eviction)")
            
            # Test threshold override
            print("\n🔧 Testing threshold override...")
            cache.store(
                query="Test query for threshold",
                response_text="Test response",
                conversation_id="threshold_test"
            )
            
            # Try with default threshold (0.9)
            result_default = cache.get("Test query for threshold override", similarity_threshold=0.9)
            print(f"   With threshold 0.9: {'HIT' if result_default else 'MISS'}")
            
            # Try with lower threshold (0.8)
            result_lower = cache.get("Test query for threshold override", similarity_threshold=0.8)
            print(f"   With threshold 0.8: {'HIT' if result_lower else 'MISS'}")
            
            # Test invalidation
            print("\n🗑️  Testing cache invalidation...")
            initial_count = len(cache.entries)
            cache.invalidate_all()
            final_count = len(cache.entries)
            print(f"   Before: {initial_count} entries")
            print(f"   After:  {final_count} entries")
            print(f"   ✓ Cache cleared successfully")
            
            print("\n✅ Advanced demo completed successfully!")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    print("\n🚀 FilAgent Semantic Cache Demonstration\n")
    
    # Run basic demo
    success1 = demo_cache_basic()
    
    # Run advanced demo
    if success1:
        success2 = demo_cache_advanced()
    else:
        success2 = False
    
    # Summary
    print("\n" + "=" * 60)
    print("Demo Summary")
    print("=" * 60)
    print(f"Basic operations: {'✅ PASSED' if success1 else '❌ FAILED'}")
    print(f"Advanced features: {'✅ PASSED' if success2 else '❌ FAILED'}")
    
    if success1 and success2:
        print("\n✨ All demos completed successfully!")
        print("\nNext steps:")
        print("1. Integrate cache into your agent workflow")
        print("2. Monitor cache hit rates and adjust threshold")
        print("3. Set up periodic cache cleanup")
        print("4. See docs/SEMANTIC_CACHE.md for more details")
    else:
        print("\n⚠️  Some demos failed. Check error messages above.")
    
    sys.exit(0 if (success1 and success2) else 1)
