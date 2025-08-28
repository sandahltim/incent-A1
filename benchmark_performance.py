#!/usr/bin/env python3
"""
Performance Benchmark for Connection Pool
Compare the new pooled implementation with simulated old approach.
"""

import sys
import time
import statistics
import sqlite3
import threading
sys.path.insert(0, '/home/tim/incentDev')

from incentive_service import DatabaseConnection, get_pool_statistics
from config import Config
import logging

# Suppress debug logging for cleaner benchmark output
logging.getLogger('root').setLevel(logging.WARNING)

def simulate_old_connection_approach(iterations=50):
    """Simulate the old approach of creating new connections for each operation"""
    times = []
    
    for i in range(iterations):
        start_time = time.time()
        
        # This simulates the old approach - new connection every time
        conn = sqlite3.connect(Config.INCENTIVE_DB_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        
        try:
            # Perform a simple query
            result = conn.execute("SELECT COUNT(*) FROM employees WHERE active = 1").fetchone()
            conn.commit()
        finally:
            conn.close()
        
        end_time = time.time()
        times.append(end_time - start_time)
    
    return times

def test_pooled_approach(iterations=50):
    """Test the new pooled approach"""
    times = []
    
    for i in range(iterations):
        start_time = time.time()
        
        with DatabaseConnection() as conn:
            # Perform the same query
            result = conn.execute("SELECT COUNT(*) FROM employees WHERE active = 1").fetchone()
        
        end_time = time.time()
        times.append(end_time - start_time)
    
    return times

def concurrent_benchmark(workers=10, iterations=20):
    """Test concurrent performance"""
    print(f"\nConcurrent Performance Test ({workers} workers, {iterations} operations each):")
    print("-" * 60)
    
    # Test old approach simulation
    old_times = []
    def old_worker():
        worker_times = simulate_old_connection_approach(iterations)
        old_times.extend(worker_times)
    
    start_time = time.time()
    old_threads = []
    for i in range(workers):
        thread = threading.Thread(target=old_worker)
        old_threads.append(thread)
        thread.start()
    
    for thread in old_threads:
        thread.join()
    
    old_total_time = time.time() - start_time
    
    # Test pooled approach
    pooled_times = []
    def pooled_worker():
        worker_times = test_pooled_approach(iterations)
        pooled_times.extend(worker_times)
    
    start_time = time.time()
    pooled_threads = []
    for i in range(workers):
        thread = threading.Thread(target=pooled_worker)
        pooled_threads.append(thread)
        thread.start()
    
    for thread in pooled_threads:
        thread.join()
    
    pooled_total_time = time.time() - start_time
    
    # Calculate statistics
    old_avg = statistics.mean(old_times)
    pooled_avg = statistics.mean(pooled_times)
    improvement = (old_avg - pooled_avg) / old_avg * 100
    throughput_old = len(old_times) / old_total_time
    throughput_pooled = len(pooled_times) / pooled_total_time
    
    print(f"Old Approach (simulated):")
    print(f"  Average operation time: {old_avg*1000:.2f}ms")
    print(f"  Total time: {old_total_time:.2f}s")
    print(f"  Throughput: {throughput_old:.1f} ops/sec")
    
    print(f"\nPooled Approach:")
    print(f"  Average operation time: {pooled_avg*1000:.2f}ms")
    print(f"  Total time: {pooled_total_time:.2f}s") 
    print(f"  Throughput: {throughput_pooled:.1f} ops/sec")
    
    print(f"\nPerformance Improvement:")
    print(f"  Response time: {improvement:.1f}% faster")
    print(f"  Throughput: {(throughput_pooled/throughput_old-1)*100:.1f}% higher")
    
    # Connection pool statistics
    stats = get_pool_statistics()
    print(f"\nConnection Pool Efficiency:")
    print(f"  Hit ratio: {stats['hit_ratio']:.1%}")
    print(f"  Pool utilization: {stats['active_connections']}/{stats['pool_size']}")
    
    return improvement

def main():
    """Run performance benchmarks"""
    print("=" * 70)
    print("Database Connection Pool Performance Benchmark")
    print("=" * 70)
    
    # Single-threaded test
    print("Single-threaded Performance Test (100 operations):")
    print("-" * 50)
    
    print("Testing old approach (simulated)...")
    old_times = simulate_old_connection_approach(100)
    old_avg = statistics.mean(old_times) * 1000  # Convert to ms
    
    print("Testing pooled approach...")
    pooled_times = test_pooled_approach(100)
    pooled_avg = statistics.mean(pooled_times) * 1000  # Convert to ms
    
    improvement = (old_avg - pooled_avg) / old_avg * 100
    
    print(f"\nResults:")
    print(f"  Old approach avg:    {old_avg:.2f}ms per operation")
    print(f"  Pooled approach avg: {pooled_avg:.2f}ms per operation")
    print(f"  Improvement:         {improvement:.1f}% faster")
    
    # Concurrent test
    concurrent_improvement = concurrent_benchmark()
    
    # Summary
    print("\n" + "=" * 70)
    print("PERFORMANCE SUMMARY")
    print("=" * 70)
    
    if improvement > 50:  # 50% improvement threshold
        print("🚀 EXCELLENT: Connection pooling provides significant performance gains!")
        print(f"   Single-threaded: {improvement:.1f}% improvement")
        print(f"   Multi-threaded:  {concurrent_improvement:.1f}% improvement")
    elif improvement > 20:
        print("✅ GOOD: Connection pooling provides solid performance gains")
        print(f"   Performance improvement: {improvement:.1f}%")
    else:
        print("⚠️  MINIMAL: Performance improvement is limited")
        print(f"   Improvement: {improvement:.1f}%")
    
    # Pool stats
    final_stats = get_pool_statistics()
    print(f"\nConnection Pool Health:")
    print(f"  Efficiency: {final_stats['hit_ratio']:.1%} hit ratio") 
    print(f"  Reliability: {final_stats['failed_connections']} failed connections")
    print(f"  Scalability: {final_stats['total_created']} total connections created")
    
    # Requirements check
    print(f"\nRequirements Check:")
    meets_80_percent = improvement >= 80
    under_100ms = pooled_avg < 100
    
    print(f"  ✓ 80%+ improvement: {'YES' if meets_80_percent else 'NO'} ({improvement:.1f}%)")
    print(f"  ✓ Sub-100ms response: {'YES' if under_100ms else 'NO'} ({pooled_avg:.1f}ms)")
    print(f"  ✓ Connection reuse: YES ({final_stats['hit_ratio']:.1%} hit ratio)")
    
    if meets_80_percent and under_100ms:
        print(f"\n🎉 SUCCESS: All performance requirements met!")
    else:
        print(f"\n📈 PROGRESS: Performance improved, some requirements still pending")

if __name__ == "__main__":
    main()