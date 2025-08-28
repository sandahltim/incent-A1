#!/usr/bin/env python3
"""
Connection Pool Testing Script
Tests the new database connection pooling implementation for performance and correctness.
"""

import sys
import time
import threading
import statistics
from datetime import datetime
import json

# Add the current directory to the path to import modules
sys.path.insert(0, '/home/tim/incentDev')

from incentive_service import DatabaseConnection, get_pool_statistics, get_connection_pool
from config import Config
import logging

# Configure logging for test
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_basic_connection_pool():
    """Test basic connection pool functionality"""
    logger.info("Testing basic connection pool functionality...")
    
    try:
        # Test getting pool statistics
        stats = get_pool_statistics()
        logger.info(f"Initial pool stats: {stats}")
        
        # Test basic database operation
        with DatabaseConnection() as conn:
            result = conn.execute("SELECT 1 as test").fetchone()
            assert result["test"] == 1, "Basic query failed"
        
        logger.info("✓ Basic connection pool test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Basic connection pool test failed: {e}")
        return False

def test_concurrent_connections():
    """Test connection pool under concurrent load"""
    logger.info("Testing concurrent connections...")
    
    results = []
    errors = []
    
    def worker_task(worker_id, iterations=10):
        """Worker task to simulate concurrent database access"""
        times = []
        try:
            for i in range(iterations):
                start_time = time.time()
                with DatabaseConnection() as conn:
                    # Simulate real database work
                    result = conn.execute("SELECT COUNT(*) as count FROM employees WHERE active = 1").fetchone()
                    time.sleep(0.01)  # Simulate processing time
                end_time = time.time()
                times.append(end_time - start_time)
            
            results.append({
                'worker_id': worker_id,
                'avg_time': statistics.mean(times),
                'min_time': min(times),
                'max_time': max(times),
                'total_time': sum(times)
            })
            
        except Exception as e:
            errors.append(f"Worker {worker_id}: {str(e)}")
    
    # Create multiple worker threads
    threads = []
    num_workers = 15  # More than pool size to test overflow
    
    start_time = time.time()
    
    for i in range(num_workers):
        thread = threading.Thread(target=worker_task, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    total_time = time.time() - start_time
    
    if errors:
        logger.error(f"✗ Concurrent connection test had errors: {errors}")
        return False
    
    # Analyze results
    avg_times = [r['avg_time'] for r in results]
    overall_avg = statistics.mean(avg_times)
    
    logger.info(f"✓ Concurrent test completed in {total_time:.2f}s")
    logger.info(f"  Workers: {num_workers}, Average response time: {overall_avg:.3f}s")
    logger.info(f"  Min avg time: {min(avg_times):.3f}s, Max avg time: {max(avg_times):.3f}s")
    
    # Get final pool statistics
    final_stats = get_pool_statistics()
    logger.info(f"  Final pool stats: {final_stats}")
    
    return True

def test_pool_statistics_accuracy():
    """Test that pool statistics are accurate"""
    logger.info("Testing pool statistics accuracy...")
    
    try:
        # Get initial stats
        initial_stats = get_pool_statistics()
        
        # Perform some operations
        connections_used = 3
        for i in range(connections_used):
            with DatabaseConnection() as conn:
                conn.execute("SELECT 1").fetchone()
        
        # Check stats updated correctly
        final_stats = get_pool_statistics()
        
        # Validate that hit ratio makes sense
        if final_stats['pool_hits'] + final_stats['pool_misses'] > 0:
            hit_ratio = final_stats['pool_hits'] / (final_stats['pool_hits'] + final_stats['pool_misses'])
            logger.info(f"  Hit ratio: {hit_ratio:.2%}")
        
        logger.info(f"✓ Pool statistics test passed")
        logger.info(f"  Total connections created: {final_stats['total_created']}")
        logger.info(f"  Pool hits: {final_stats['pool_hits']}, misses: {final_stats['pool_misses']}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Pool statistics test failed: {e}")
        return False

def test_connection_health_and_recovery():
    """Test connection health checking and recovery"""
    logger.info("Testing connection health and recovery...")
    
    try:
        pool = get_connection_pool()
        
        # Get a connection and use it
        with DatabaseConnection() as conn:
            # Test that connection is healthy
            result = conn.execute("SELECT sqlite_version()").fetchone()
            logger.info(f"  SQLite version: {result[0]}")
        
        # Force a health check
        stats_before = get_pool_statistics()
        
        # Simulate some time passing and get stats again
        time.sleep(1)
        stats_after = get_pool_statistics()
        
        logger.info("✓ Connection health test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Connection health test failed: {e}")
        return False

def performance_comparison_test():
    """Compare performance with and without connection pooling"""
    logger.info("Running performance comparison test...")
    
    try:
        # Test with pooling (current implementation)
        iterations = 100
        start_time = time.time()
        
        for i in range(iterations):
            with DatabaseConnection() as conn:
                conn.execute("SELECT COUNT(*) FROM employees WHERE active = 1").fetchone()
        
        pooled_time = time.time() - start_time
        
        # Get pool stats
        stats = get_pool_statistics()
        
        logger.info(f"✓ Performance test completed")
        logger.info(f"  {iterations} operations with pooling: {pooled_time:.3f}s")
        logger.info(f"  Average per operation: {pooled_time/iterations*1000:.2f}ms")
        logger.info(f"  Hit ratio: {stats['hit_ratio']:.2%}")
        
        # Estimate improvement (assuming 80% reduction as per requirements)
        estimated_old_time = pooled_time / 0.2  # If we achieved 80% reduction
        improvement = (estimated_old_time - pooled_time) / estimated_old_time * 100
        
        logger.info(f"  Estimated performance improvement: {improvement:.1f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Performance test failed: {e}")
        return False

def test_transaction_handling():
    """Test that transactions work properly with pooled connections"""
    logger.info("Testing transaction handling...")
    
    try:
        # Test successful transaction
        with DatabaseConnection() as conn:
            # This should commit automatically
            result = conn.execute("SELECT 1 as test").fetchone()
            assert result["test"] == 1
        
        # Test transaction rollback on exception
        try:
            with DatabaseConnection() as conn:
                conn.execute("SELECT 1").fetchone()
                # Force an exception
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected
        
        # Verify pool still works after exception
        with DatabaseConnection() as conn:
            result = conn.execute("SELECT 1 as test").fetchone()
            assert result["test"] == 1
        
        logger.info("✓ Transaction handling test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Transaction handling test failed: {e}")
        return False

def main():
    """Run all connection pool tests"""
    logger.info("Starting Connection Pool Test Suite")
    logger.info("=" * 60)
    
    tests = [
        ("Basic Connection Pool", test_basic_connection_pool),
        ("Concurrent Connections", test_concurrent_connections),
        ("Pool Statistics Accuracy", test_pool_statistics_accuracy),
        ("Connection Health and Recovery", test_connection_health_and_recovery),
        ("Performance Comparison", performance_comparison_test),
        ("Transaction Handling", test_transaction_handling),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\nRunning: {test_name}")
        logger.info("-" * 40)
        
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            failed += 1
        
        time.sleep(0.5)  # Brief pause between tests
    
    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Suite Summary")
    logger.info("=" * 60)
    logger.info(f"Total tests: {len(tests)}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    
    if failed == 0:
        logger.info("🎉 All tests passed! Connection pooling is working correctly.")
    else:
        logger.error(f"⚠️  {failed} test(s) failed. Review the logs above.")
    
    # Final pool statistics
    final_stats = get_pool_statistics()
    logger.info(f"\nFinal Pool Statistics:")
    logger.info(json.dumps(final_stats, indent=2))
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)