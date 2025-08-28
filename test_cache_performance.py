#!/usr/bin/env python3
"""
Performance test for the caching system
Tests the 60-80% improvement target by comparing cached vs uncached operations
"""

import time
import sys
import os
import logging
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from incentive_service import DatabaseConnection, get_scoreboard, get_rules, get_roles, get_settings, get_pot_info
from config import Config
from services.cache import get_cache_manager, get_metrics_collector, get_invalidation_manager

# Configure logging for test
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def time_function(func, *args, **kwargs):
    """Time how long a function takes to execute"""
    start = time.time()
    result = func(*args, **kwargs)
    end = time.time()
    return result, end - start

def test_database_operations(conn, iterations=10):
    """Test database operations without caching"""
    operations = [
        ('get_scoreboard', lambda: get_scoreboard(conn)),
        ('get_rules', lambda: get_rules(conn)),
        ('get_roles', lambda: get_roles(conn)),
        ('get_settings', lambda: get_settings(conn)),
        ('get_pot_info', lambda: get_pot_info(conn))
    ]
    
    results = {}
    
    for name, func in operations:
        times = []
        for i in range(iterations):
            _, duration = time_function(func)
            times.append(duration)
        
        avg_time = sum(times) / len(times)
        results[name] = {
            'avg_time': avg_time,
            'min_time': min(times),
            'max_time': max(times),
            'iterations': iterations
        }
        logging.info(f"{name}: avg={avg_time:.4f}s, min={min(times):.4f}s, max={max(times):.4f}s")
    
    return results

def test_cached_operations(conn, iterations=10):
    """Test the same operations with caching enabled"""
    # Clear cache before starting
    cache = get_cache_manager()
    cache.clear()
    
    operations = [
        ('get_scoreboard', lambda: get_scoreboard(conn)),
        ('get_rules', lambda: get_rules(conn)),
        ('get_roles', lambda: get_roles(conn)),
        ('get_settings', lambda: get_settings(conn)),
        ('get_pot_info', lambda: get_pot_info(conn))
    ]
    
    results = {}
    
    for name, func in operations:
        times = []
        
        # First call to populate cache
        _, first_call_time = time_function(func)
        times.append(first_call_time)
        
        # Subsequent calls should be cached
        for i in range(iterations - 1):
            _, duration = time_function(func)
            times.append(duration)
        
        avg_time = sum(times) / len(times)
        avg_cached_time = sum(times[1:]) / len(times[1:]) if len(times) > 1 else avg_time
        
        results[name] = {
            'avg_time': avg_time,
            'avg_cached_time': avg_cached_time,
            'first_call_time': first_call_time,
            'min_time': min(times),
            'max_time': max(times),
            'iterations': iterations
        }
        logging.info(f"{name} (cached): avg={avg_time:.4f}s, cached_avg={avg_cached_time:.4f}s, first={first_call_time:.4f}s")
    
    return results

def test_cache_hit_performance():
    """Test cache hit/miss performance"""
    cache = get_cache_manager()
    cache.clear()
    
    # Test cache hits vs misses
    test_data = {f"key_{i}": f"data_{i}" for i in range(100)}
    
    # Measure cache set performance
    start = time.time()
    for key, value in test_data.items():
        cache.set(key, value)
    set_time = time.time() - start
    
    # Measure cache hit performance
    start = time.time()
    for key in test_data:
        cache.get(key)
    hit_time = time.time() - start
    
    # Measure cache miss performance
    cache.clear()
    start = time.time()
    for key in test_data:
        cache.get(key)
    miss_time = time.time() - start
    
    return {
        'set_time': set_time,
        'hit_time': hit_time,
        'miss_time': miss_time,
        'operations': len(test_data)
    }

def calculate_improvement(uncached_results, cached_results):
    """Calculate performance improvement percentage"""
    improvements = {}
    
    for operation in uncached_results:
        if operation in cached_results:
            uncached_time = uncached_results[operation]['avg_time']
            cached_time = cached_results[operation]['avg_cached_time']
            
            if uncached_time > 0:
                improvement = ((uncached_time - cached_time) / uncached_time) * 100
                improvements[operation] = {
                    'uncached_avg': uncached_time,
                    'cached_avg': cached_time,
                    'improvement_percent': improvement
                }
    
    return improvements

def run_performance_test():
    """Run comprehensive performance tests"""
    print("=" * 80)
    print("INCENTIVE SYSTEM CACHING PERFORMANCE TEST")
    print("=" * 80)
    print(f"Test started at: {datetime.now()}")
    print(f"Database file: {Config.INCENTIVE_DB_FILE}")
    print(f"Cache enabled: {Config.CACHE_ENABLED}")
    print()
    
    try:
        with DatabaseConnection() as conn:
            # Test 1: Database operations without heavy caching influence
            print("Phase 1: Testing uncached performance...")
            # Temporarily disable caching for baseline
            original_cache_enabled = Config.CACHE_ENABLED
            Config.CACHE_ENABLED = False
            
            uncached_results = test_database_operations(conn, iterations=20)
            
            # Re-enable caching
            Config.CACHE_ENABLED = original_cache_enabled
            
            print("\nPhase 2: Testing cached performance...")
            cached_results = test_cached_operations(conn, iterations=20)
            
            print("\nPhase 3: Testing cache operations...")
            cache_ops = test_cache_hit_performance()
            
            # Calculate improvements
            print("\nPhase 4: Calculating improvements...")
            improvements = calculate_improvement(uncached_results, cached_results)
            
            # Get cache statistics
            metrics = get_metrics_collector()
            cache_stats = metrics.get_performance_report()
            
            # Report results
            print("\n" + "=" * 80)
            print("PERFORMANCE IMPROVEMENT RESULTS")
            print("=" * 80)
            
            total_improvement = 0
            operation_count = 0
            
            for operation, data in improvements.items():
                improvement = data['improvement_percent']
                total_improvement += improvement
                operation_count += 1
                
                status = "✅" if improvement >= 60 else "⚠️" if improvement >= 30 else "❌"
                print(f"{status} {operation}:")
                print(f"   Uncached: {data['uncached_avg']:.4f}s")
                print(f"   Cached:   {data['cached_avg']:.4f}s")
                print(f"   Improvement: {improvement:.1f}%")
                print()
            
            avg_improvement = total_improvement / operation_count if operation_count > 0 else 0
            
            print(f"Average Performance Improvement: {avg_improvement:.1f}%")
            print(f"Target: 60-80% improvement")
            
            if avg_improvement >= 60:
                print("✅ SUCCESS: Target performance improvement achieved!")
            elif avg_improvement >= 30:
                print("⚠️  PARTIAL: Some improvement achieved, but below target")
            else:
                print("❌ FAILED: Insufficient performance improvement")
            
            print("\n" + "=" * 80)
            print("CACHE PERFORMANCE STATISTICS")
            print("=" * 80)
            print(f"Cache Hit Ratio: {cache_stats.get('hit_ratio', 0):.3f}")
            print(f"Cache Hits: {cache_stats.get('hits', 0)}")
            print(f"Cache Misses: {cache_stats.get('misses', 0)}")
            print(f"Cache Size: {cache_stats.get('current_size', 0)}")
            print(f"Performance Grade: {cache_stats.get('performance_grade', 'N/A')}")
            
            print(f"\nCache Operations Performance:")
            print(f"Set 100 items: {cache_ops['set_time']:.4f}s")
            print(f"Get 100 hits: {cache_ops['hit_time']:.4f}s")
            print(f"Get 100 misses: {cache_ops['miss_time']:.4f}s")
            
            print(f"\nTest completed at: {datetime.now()}")
            
            return avg_improvement >= 60
            
    except Exception as e:
        logging.error(f"Performance test failed: {e}")
        print(f"❌ TEST FAILED: {e}")
        return False

if __name__ == "__main__":
    success = run_performance_test()
    sys.exit(0 if success else 1)