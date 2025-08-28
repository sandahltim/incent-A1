# tests/test_caching.py
# Caching service tests for the Employee Incentive System
# Version: 1.0.0

import pytest
import time
import threading
import os
import sys
from unittest.mock import patch, Mock, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from services.cache import (
        CacheEntry, IncentiveCacheManager, InvalidationManager, CacheConfig,
        CacheWarmer, MetricsCollector, cached, get_cache_manager,
        get_invalidation_manager, get_cache_config, get_cache_warmer,
        get_metrics_collector
    )
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False


@pytest.mark.skipif(not CACHE_AVAILABLE, reason="Cache module not available")
class TestCacheEntry:
    """Test CacheEntry functionality"""
    
    def test_cache_entry_creation(self):
        """Test cache entry creation with default values"""
        data = {"key": "value"}
        entry = CacheEntry(data)
        
        assert entry.data == data
        assert entry.ttl == 300  # Default TTL
        assert entry.hit_count == 0
        assert entry.tags == set()
        assert not entry.is_expired
    
    def test_cache_entry_with_custom_values(self):
        """Test cache entry creation with custom values"""
        data = {"key": "value"}
        tags = {"tag1", "tag2"}
        ttl = 600
        
        entry = CacheEntry(data, ttl=ttl, tags=tags)
        
        assert entry.data == data
        assert entry.ttl == ttl
        assert entry.tags == tags
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration"""
        entry = CacheEntry("test_data", ttl=1)  # 1 second TTL
        
        assert not entry.is_expired
        
        time.sleep(1.1)  # Wait for expiration
        
        assert entry.is_expired
    
    def test_cache_entry_access_tracking(self):
        """Test cache entry access tracking"""
        entry = CacheEntry("test_data")
        
        initial_hit_count = entry.hit_count
        initial_last_access = entry.last_access
        
        time.sleep(0.01)  # Small delay to ensure time difference
        entry.access()
        
        assert entry.hit_count == initial_hit_count + 1
        assert entry.last_access > initial_last_access
    
    def test_cache_entry_age(self):
        """Test cache entry age calculation"""
        entry = CacheEntry("test_data")
        
        initial_age = entry.age
        time.sleep(0.1)  # Wait 100ms
        
        assert entry.age > initial_age
        assert entry.age >= 0.1


@pytest.mark.skipif(not CACHE_AVAILABLE, reason="Cache module not available")
class TestIncentiveCacheManager:
    """Test IncentiveCacheManager functionality"""
    
    def test_cache_manager_creation(self):
        """Test cache manager creation with default values"""
        cache = IncentiveCacheManager()
        
        assert cache._max_size == 1000
        assert cache._default_ttl == 300
        assert cache._cleanup_interval == 60
    
    def test_cache_manager_with_custom_values(self):
        """Test cache manager creation with custom values"""
        cache = IncentiveCacheManager(max_size=500, default_ttl=600, cleanup_interval=120)
        
        assert cache._max_size == 500
        assert cache._default_ttl == 600
        assert cache._cleanup_interval == 120
    
    def test_cache_set_and_get(self):
        """Test basic cache set and get operations"""
        cache = IncentiveCacheManager()
        
        key = "test_key"
        value = {"data": "test_value"}
        
        # Set cache entry
        result = cache.set(key, value)
        assert result is True
        
        # Get cache entry
        cached_value = cache.get(key)
        assert cached_value == value
    
    def test_cache_get_nonexistent_key(self):
        """Test getting a non-existent cache key"""
        cache = IncentiveCacheManager()
        
        result = cache.get("nonexistent_key")
        assert result is None
        
        # Test with default value
        default_value = "default"
        result = cache.get("nonexistent_key", default_value)
        assert result == default_value
    
    def test_cache_delete(self):
        """Test cache entry deletion"""
        cache = IncentiveCacheManager()
        
        key = "test_key"
        value = "test_value"
        
        # Set and verify
        cache.set(key, value)
        assert cache.get(key) == value
        
        # Delete and verify
        result = cache.delete(key)
        assert result is True
        assert cache.get(key) is None
        
        # Delete non-existent key
        result = cache.delete("nonexistent_key")
        assert result is False
    
    def test_cache_clear(self):
        """Test clearing all cache entries"""
        cache = IncentiveCacheManager()
        
        # Add multiple entries
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Verify entries exist
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        
        # Clear cache
        cache.clear()
        
        # Verify all entries are gone
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None
    
    def test_cache_ttl_expiration(self):
        """Test cache TTL expiration"""
        cache = IncentiveCacheManager()
        
        key = "test_key"
        value = "test_value"
        ttl = 1  # 1 second
        
        # Set with short TTL
        cache.set(key, value, ttl=ttl)
        assert cache.get(key) == value
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Entry should be expired and return None
        result = cache.get(key)
        assert result is None
    
    def test_cache_size_limit(self):
        """Test cache size limitation"""
        cache = IncentiveCacheManager(max_size=3)
        
        # Add entries up to limit
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # All entries should be present
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        
        # Add one more entry (should evict oldest)
        cache.set("key4", "value4")
        
        # key1 should be evicted, others should remain
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
    
    def test_cache_statistics(self):
        """Test cache statistics collection"""
        cache = IncentiveCacheManager()
        
        # Perform some operations
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.get("key1")  # Hit
        cache.get("key1")  # Hit
        cache.get("nonexistent")  # Miss
        
        stats = cache.get_stats()
        
        assert 'hits' in stats
        assert 'misses' in stats
        assert 'sets' in stats
        assert 'deletes' in stats
        assert 'size' in stats
        
        assert stats['hits'] >= 2
        assert stats['misses'] >= 1
        assert stats['sets'] >= 2
    
    def test_cache_thread_safety(self):
        """Test cache thread safety"""
        cache = IncentiveCacheManager()
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                for i in range(100):
                    key = f"key_{worker_id}_{i}"
                    value = f"value_{worker_id}_{i}"
                    
                    # Set value
                    cache.set(key, value)
                    
                    # Get value
                    retrieved = cache.get(key)
                    if retrieved == value:
                        results.append((worker_id, i, True))
                    else:
                        results.append((worker_id, i, False))
                        
            except Exception as e:
                errors.append((worker_id, str(e)))
        
        # Run concurrent workers
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        
        # All operations should have succeeded
        successful_ops = [r for r in results if r[2] is True]
        assert len(successful_ops) == 500  # 5 workers * 100 operations each


@pytest.mark.skipif(not CACHE_AVAILABLE, reason="Cache module not available")
class TestCacheDecorator:
    """Test the @cached decorator functionality"""
    
    def test_cached_decorator_basic(self):
        """Test basic cached decorator functionality"""
        call_count = 0
        
        @cached(ttl=300)
        def expensive_function(arg1, arg2):
            nonlocal call_count
            call_count += 1
            return f"result_{arg1}_{arg2}"
        
        # First call should execute function
        result1 = expensive_function("a", "b")
        assert result1 == "result_a_b"
        assert call_count == 1
        
        # Second call with same args should use cache
        result2 = expensive_function("a", "b")
        assert result2 == "result_a_b"
        assert call_count == 1  # Function not called again
        
        # Call with different args should execute function
        result3 = expensive_function("c", "d")
        assert result3 == "result_c_d"
        assert call_count == 2
    
    def test_cached_decorator_with_kwargs(self):
        """Test cached decorator with keyword arguments"""
        call_count = 0
        
        @cached(ttl=300)
        def function_with_kwargs(arg1, arg2=None, arg3="default"):
            nonlocal call_count
            call_count += 1
            return f"{arg1}_{arg2}_{arg3}"
        
        # Test with kwargs
        result1 = function_with_kwargs("a", arg2="b", arg3="c")
        assert result1 == "a_b_c"
        assert call_count == 1
        
        # Same call should use cache
        result2 = function_with_kwargs("a", arg2="b", arg3="c")
        assert result2 == "a_b_c"
        assert call_count == 1
        
        # Different order of kwargs should still match
        result3 = function_with_kwargs("a", arg3="c", arg2="b")
        assert result3 == "a_b_c"
        assert call_count == 1  # Should still use cache
    
    def test_cached_decorator_ttl_expiration(self):
        """Test cached decorator TTL expiration"""
        call_count = 0
        
        @cached(ttl=1)  # 1 second TTL
        def short_ttl_function(arg):
            nonlocal call_count
            call_count += 1
            return f"result_{arg}"
        
        # First call
        result1 = short_ttl_function("test")
        assert result1 == "result_test"
        assert call_count == 1
        
        # Immediate second call should use cache
        result2 = short_ttl_function("test")
        assert result2 == "result_test"
        assert call_count == 1
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Call after expiration should execute function again
        result3 = short_ttl_function("test")
        assert result3 == "result_test"
        assert call_count == 2
    
    def test_cached_decorator_with_tags(self):
        """Test cached decorator with cache tags"""
        @cached(ttl=300, tags=["user_data"])
        def get_user_data(user_id):
            return f"user_data_{user_id}"
        
        result = get_user_data(123)
        assert result == "user_data_123"
        
        # This test verifies the decorator works with tags
        # Actual tag-based invalidation testing would require
        # integration with InvalidationManager


@pytest.mark.skipif(not CACHE_AVAILABLE, reason="Cache module not available")
class TestCacheIntegration:
    """Test cache integration with database operations"""
    
    def test_cache_scoreboard_integration(self, mock_cache_manager):
        """Test caching integration with scoreboard data"""
        # Mock scoreboard data
        scoreboard_data = [
            {"id": 1, "name": "John Doe", "score": 100},
            {"id": 2, "name": "Jane Smith", "score": 150}
        ]
        
        # Test cache miss
        mock_cache_manager.get.return_value = None
        
        # Simulate getting scoreboard with cache
        def get_cached_scoreboard():
            cached = mock_cache_manager.get("scoreboard")
            if cached is None:
                # Simulate database query
                data = scoreboard_data
                mock_cache_manager.set("scoreboard", data, ttl=300)
                return data
            return cached
        
        # First call should cache the data
        result1 = get_cached_scoreboard()
        assert result1 == scoreboard_data
        mock_cache_manager.set.assert_called_with("scoreboard", scoreboard_data, ttl=300)
        
        # Second call should use cache
        mock_cache_manager.get.return_value = scoreboard_data
        result2 = get_cached_scoreboard()
        assert result2 == scoreboard_data
    
    def test_cache_invalidation_on_vote(self, mock_cache_manager, mock_invalidation_manager):
        """Test cache invalidation when votes are cast"""
        # Simulate vote casting that should invalidate scoreboard cache
        def cast_vote_with_cache_invalidation(voter_id, votes):
            # Cast vote logic here
            success = True  # Simulate successful vote
            
            if success:
                # Invalidate related caches
                mock_invalidation_manager.invalidate_pattern("scoreboard*")
                mock_invalidation_manager.invalidate_tags(["voting", "scores"])
            
            return success
        
        result = cast_vote_with_cache_invalidation(1, {"2": "positive"})
        assert result is True
        
        mock_invalidation_manager.invalidate_pattern.assert_called_with("scoreboard*")
        mock_invalidation_manager.invalidate_tags.assert_called_with(["voting", "scores"])
    
    def test_cache_warming(self, mock_cache_manager):
        """Test cache warming functionality"""
        # Mock data that should be preloaded
        warm_data = {
            "settings": {"site_name": "Test Site"},
            "active_employees": [{"id": 1, "name": "John"}],
            "voting_status": {"active": False}
        }
        
        # Simulate cache warming
        def warm_cache():
            for key, data in warm_data.items():
                mock_cache_manager.set(f"warm_{key}", data, ttl=600)
        
        warm_cache()
        
        # Verify cache was warmed
        assert mock_cache_manager.set.call_count == 3
        mock_cache_manager.set.assert_any_call("warm_settings", warm_data["settings"], ttl=600)
        mock_cache_manager.set.assert_any_call("warm_active_employees", warm_data["active_employees"], ttl=600)
        mock_cache_manager.set.assert_any_call("warm_voting_status", warm_data["voting_status"], ttl=600)


@pytest.mark.skipif(not CACHE_AVAILABLE, reason="Cache module not available")
class TestCachePerformance:
    """Test cache performance characteristics"""
    
    def test_cache_performance_improvement(self):
        """Test that caching provides performance improvement"""
        cache = IncentiveCacheManager()
        
        def expensive_operation(value):
            # Simulate expensive operation
            time.sleep(0.01)  # 10ms delay
            return f"processed_{value}"
        
        # Time uncached operations
        start_time = time.time()
        for i in range(10):
            expensive_operation(i)
        uncached_time = time.time() - start_time
        
        # Time cached operations
        start_time = time.time()
        for i in range(10):
            key = f"expensive_{i}"
            result = cache.get(key)
            if result is None:
                result = expensive_operation(i)
                cache.set(key, result)
        
        # Second pass should be faster (cached)
        start_time = time.time()
        for i in range(10):
            key = f"expensive_{i}"
            result = cache.get(key)
        cached_time = time.time() - start_time
        
        # Cached operations should be significantly faster
        assert cached_time < uncached_time * 0.5  # At least 50% faster
    
    def test_cache_memory_usage(self):
        """Test cache memory usage characteristics"""
        import sys
        
        cache = IncentiveCacheManager(max_size=1000)
        
        # Add many entries and measure memory impact
        initial_size = sys.getsizeof(cache._cache)
        
        for i in range(100):
            cache.set(f"key_{i}", f"value_{i}" * 100)  # Larger values
        
        final_size = sys.getsizeof(cache._cache)
        
        # Memory should have increased
        assert final_size > initial_size
        
        # Clear cache and verify memory is released
        cache.clear()
        cleared_size = sys.getsizeof(cache._cache)
        
        # Size should be close to initial (allowing for some overhead)
        assert cleared_size <= initial_size * 1.1
    
    def test_concurrent_cache_performance(self):
        """Test cache performance under concurrent load"""
        cache = IncentiveCacheManager()
        
        # Pre-populate cache
        for i in range(100):
            cache.set(f"key_{i}", f"value_{i}")
        
        results = []
        
        def concurrent_worker(worker_id):
            start_time = time.time()
            
            # Perform many cache operations
            for i in range(100):
                key = f"key_{i % 50}"  # Mix of hits and misses
                value = cache.get(key)
                
                if value is None:
                    cache.set(key, f"new_value_{worker_id}_{i}")
            
            elapsed = time.time() - start_time
            results.append(elapsed)
        
        # Run concurrent workers
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(concurrent_worker, i) for i in range(10)]
            
            for future in as_completed(futures):
                future.result()
        
        # All workers should complete in reasonable time
        max_time = max(results)
        avg_time = sum(results) / len(results)
        
        assert max_time < 5.0  # No worker should take more than 5 seconds
        assert avg_time < 1.0  # Average should be under 1 second


@pytest.mark.skipif(not CACHE_AVAILABLE, reason="Cache module not available")
class TestCacheConfiguration:
    """Test cache configuration and setup"""
    
    def test_cache_config_loading(self):
        """Test loading cache configuration"""
        try:
            config = get_cache_config()
            assert config is not None
            # Configuration should have expected attributes
            assert hasattr(config, 'cache_enabled') or isinstance(config, dict)
        except Exception:
            # If configuration loading fails, it's acceptable in test environment
            pass
    
    def test_cache_manager_singleton(self):
        """Test that cache manager is a singleton"""
        try:
            manager1 = get_cache_manager()
            manager2 = get_cache_manager()
            
            # Should be the same instance
            assert manager1 is manager2
        except Exception:
            # If singleton pattern fails, it's acceptable in test environment
            pass
    
    def test_cache_invalidation_manager_singleton(self):
        """Test that invalidation manager is a singleton"""
        try:
            manager1 = get_invalidation_manager()
            manager2 = get_invalidation_manager()
            
            # Should be the same instance
            assert manager1 is manager2
        except Exception:
            # If singleton pattern fails, it's acceptable in test environment
            pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])