#!/usr/bin/env python3
"""
Realistic performance test simulating actual user load patterns
Tests concurrent requests and composite operations like those in the web interface
"""

import time
import sys
import os
import logging
from datetime import datetime
import threading
import concurrent.futures
import random

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from incentive_service import (
    DatabaseConnection, get_scoreboard, get_rules, get_roles, 
    get_settings, get_pot_info, get_voting_results, get_history
)
from config import Config
from services.cache import get_cache_manager, get_metrics_collector, get_invalidation_manager

# Configure logging for test
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

def simulate_dashboard_load(conn):
    """Simulate loading the main dashboard (multiple DB calls)"""
    start = time.time()
    
    # This simulates the main route in app.py
    scoreboard = get_scoreboard(conn)
    rules = get_rules(conn)
    pot_info = get_pot_info(conn)
    roles = get_roles(conn)
    settings = get_settings(conn)
    
    # Calculate payouts like in the real app
    money_threshold = int(settings.get('money_threshold', 50))
    for emp in scoreboard:
        role_key = emp['role'].lower().replace(' ', '_')
        point_value = pot_info.get(f'{role_key}_point_value', 0)
        if emp['score'] >= money_threshold:
            payout = round(emp['score'] * point_value, 2)
    
    return time.time() - start

def simulate_admin_load(conn):
    """Simulate admin operations (heavy data operations)"""
    start = time.time()
    
    # Admin dashboard operations
    scoreboard = get_scoreboard(conn)
    rules = get_rules(conn)
    roles = get_roles(conn)
    settings = get_settings(conn)
    pot_info = get_pot_info(conn)
    history = get_history(conn)
    voting_results = get_voting_results(conn, is_admin=True)
    
    return time.time() - start

def simulate_api_load(conn):
    """Simulate API endpoint load (frequent polling)"""
    start = time.time()
    
    # This simulates the /data endpoint
    scoreboard = get_scoreboard(conn)
    pot_info = get_pot_info(conn)
    
    return time.time() - start

def worker_thread(operation_func, conn, iterations, results, thread_id):
    """Worker thread for concurrent testing"""
    times = []
    for i in range(iterations):
        duration = operation_func(conn)
        times.append(duration)
        # Add some randomness to simulate real user behavior
        time.sleep(random.uniform(0.01, 0.05))
    
    results[thread_id] = times

def test_concurrent_load(operation_func, name, num_threads=5, iterations_per_thread=10, use_cache=True):
    """Test concurrent operations"""
    print(f"\nTesting {name} ({'with cache' if use_cache else 'without cache'})...")
    
    # Configure caching
    original_cache_enabled = Config.CACHE_ENABLED
    Config.CACHE_ENABLED = use_cache
    
    if use_cache:
        cache = get_cache_manager()
        cache.clear()
    
    results = {}
    threads = []
    
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for thread_id in range(num_threads):
            future = executor.submit(
                worker_thread, 
                operation_func, 
                DatabaseConnection().__enter__(), 
                iterations_per_thread, 
                results, 
                thread_id
            )
            futures.append(future)
        
        # Wait for all threads to complete
        for future in futures:
            future.result()
    
    total_time = time.time() - start_time
    
    # Collect all timing data
    all_times = []
    for thread_results in results.values():
        all_times.extend(thread_results)
    
    avg_time = sum(all_times) / len(all_times)
    total_operations = len(all_times)
    operations_per_second = total_operations / total_time
    
    # Restore original cache setting
    Config.CACHE_ENABLED = original_cache_enabled
    
    return {
        'avg_time': avg_time,
        'min_time': min(all_times),
        'max_time': max(all_times),
        'total_time': total_time,
        'operations_per_second': operations_per_second,
        'total_operations': total_operations
    }

def run_realistic_test():
    """Run realistic performance test"""
    print("=" * 80)
    print("REALISTIC LOAD PERFORMANCE TEST")
    print("=" * 80)
    print(f"Test started at: {datetime.now()}")
    print(f"Database file: {Config.INCENTIVE_DB_FILE}")
    print()
    
    operations = [
        (simulate_dashboard_load, "Dashboard Load"),
        (simulate_admin_load, "Admin Dashboard Load"),
        (simulate_api_load, "API Polling Load")
    ]
    
    results_summary = {}
    
    for operation_func, name in operations:
        try:
            # Test without cache
            uncached_results = test_concurrent_load(
                operation_func, name, 
                num_threads=5, iterations_per_thread=20, use_cache=False
            )
            
            # Test with cache
            cached_results = test_concurrent_load(
                operation_func, name,
                num_threads=5, iterations_per_thread=20, use_cache=True
            )
            
            # Calculate improvement
            avg_improvement = ((uncached_results['avg_time'] - cached_results['avg_time']) 
                             / uncached_results['avg_time'] * 100)
            throughput_improvement = ((cached_results['operations_per_second'] - uncached_results['operations_per_second']) 
                                    / uncached_results['operations_per_second'] * 100)
            
            results_summary[name] = {
                'uncached': uncached_results,
                'cached': cached_results,
                'avg_improvement': avg_improvement,
                'throughput_improvement': throughput_improvement
            }
            
        except Exception as e:
            print(f"Error testing {name}: {e}")
            continue
    
    # Report results
    print("\n" + "=" * 80)
    print("REALISTIC LOAD TEST RESULTS")
    print("=" * 80)
    
    total_avg_improvement = 0
    total_throughput_improvement = 0
    test_count = 0
    
    for name, data in results_summary.items():
        uncached = data['uncached']
        cached = data['cached']
        avg_improvement = data['avg_improvement']
        throughput_improvement = data['throughput_improvement']
        
        status = "✅" if avg_improvement >= 60 else "⚠️" if avg_improvement >= 30 else "❌"
        
        print(f"\n{status} {name}:")
        print(f"   Uncached avg time: {uncached['avg_time']:.4f}s")
        print(f"   Cached avg time:   {cached['avg_time']:.4f}s")
        print(f"   Response time improvement: {avg_improvement:.1f}%")
        print(f"   Uncached throughput: {uncached['operations_per_second']:.1f} ops/sec")
        print(f"   Cached throughput:   {cached['operations_per_second']:.1f} ops/sec")
        print(f"   Throughput improvement: {throughput_improvement:.1f}%")
        
        total_avg_improvement += avg_improvement
        total_throughput_improvement += throughput_improvement
        test_count += 1
    
    if test_count > 0:
        overall_avg_improvement = total_avg_improvement / test_count
        overall_throughput_improvement = total_throughput_improvement / test_count
        
        print(f"\n" + "=" * 40)
        print(f"OVERALL RESULTS:")
        print(f"Average response time improvement: {overall_avg_improvement:.1f}%")
        print(f"Average throughput improvement: {overall_throughput_improvement:.1f}%")
        print(f"Target: 60-80% improvement")
        
        if overall_avg_improvement >= 60:
            print("✅ SUCCESS: Target performance improvement achieved!")
            success = True
        elif overall_avg_improvement >= 30:
            print("⚠️  PARTIAL: Some improvement achieved, but below target")
            success = False
        else:
            print("❌ FAILED: Insufficient performance improvement")
            success = False
        
        # Get final cache statistics
        if Config.CACHE_ENABLED:
            try:
                metrics = get_metrics_collector()
                cache_stats = metrics.get_performance_report()
                
                print(f"\n" + "=" * 40)
                print("FINAL CACHE STATISTICS:")
                print(f"Cache Hit Ratio: {cache_stats.get('hit_ratio', 0):.3f}")
                print(f"Cache Hits: {cache_stats.get('hits', 0)}")
                print(f"Cache Misses: {cache_stats.get('misses', 0)}")
                print(f"Performance Grade: {cache_stats.get('performance_grade', 'N/A')}")
            except Exception as e:
                print(f"Could not get cache stats: {e}")
        
        print(f"\nTest completed at: {datetime.now()}")
        return success
    else:
        print("❌ No tests completed successfully")
        return False

if __name__ == "__main__":
    success = run_realistic_test()
    sys.exit(0 if success else 1)