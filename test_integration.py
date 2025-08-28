#!/usr/bin/env python3
"""
Integration Test for Connection Pool
Verify that the main application functions work correctly with the new connection pool.
"""

import sys
import logging
sys.path.insert(0, '/home/tim/incentDev')

from incentive_service import (
    DatabaseConnection, get_scoreboard, get_settings, get_pool_statistics,
    get_pot_info
)

# Configure logging
logging.basicConfig(level=logging.ERROR)  # Reduce noise during test

def test_basic_operations():
    """Test basic database operations work with pooling"""
    print("Testing basic database operations...")
    
    try:
        # Test scoreboard
        with DatabaseConnection() as conn:
            scoreboard = get_scoreboard(conn)
            print(f"  ✓ Scoreboard query: {len(scoreboard)} employees")
        
        # Test settings
        with DatabaseConnection() as conn:
            settings = get_settings(conn)
            print(f"  ✓ Settings query: {len(settings)} settings loaded")
        
        # Test pot info  
        with DatabaseConnection() as conn:
            pot_info = get_pot_info(conn)
            print(f"  ✓ Pot info query: ${pot_info.get('sales_dollars', 0):,.2f} sales")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Basic operations failed: {e}")
        return False

def test_concurrent_operations():
    """Test multiple concurrent operations"""
    print("Testing concurrent operations...")
    
    import threading
    import time
    
    results = []
    errors = []
    
    def worker(worker_id):
        try:
            for i in range(5):
                with DatabaseConnection() as conn:
                    # Mix different types of queries
                    if i % 2 == 0:
                        get_scoreboard(conn)
                    else:
                        get_settings(conn)
                    time.sleep(0.001)  # Small delay
            results.append(worker_id)
        except Exception as e:
            errors.append(f"Worker {worker_id}: {e}")
    
    # Start 5 concurrent workers
    threads = []
    for i in range(5):
        thread = threading.Thread(target=worker, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for completion
    for thread in threads:
        thread.join()
    
    if errors:
        print(f"  ✗ Concurrent test failed: {errors}")
        return False
    else:
        print(f"  ✓ All {len(results)} workers completed successfully")
        return True

def test_pool_statistics():
    """Test that pool statistics are working"""
    print("Testing pool statistics...")
    
    try:
        stats = get_pool_statistics()
        
        print(f"  Pool size: {stats['pool_size']}")
        print(f"  Active connections: {stats['active_connections']}")
        print(f"  Hit ratio: {stats['hit_ratio']:.1%}")
        print(f"  Total created: {stats['total_created']}")
        
        if stats['pool_size'] > 0:
            print("  ✓ Pool statistics working correctly")
            return True
        else:
            print("  ✗ Pool size is 0")
            return False
            
    except Exception as e:
        print(f"  ✗ Pool statistics failed: {e}")
        return False

def get_employees(conn):
    """Helper function to get employees (if this function doesn't exist)"""
    try:
        return conn.execute("SELECT COUNT(*) as count FROM employees WHERE active = 1").fetchone()
    except:
        return {"count": 0}

def main():
    """Run integration tests"""
    print("=" * 50)
    print("Connection Pool Integration Test")
    print("=" * 50)
    
    tests = [
        ("Basic Operations", test_basic_operations),
        ("Concurrent Operations", test_concurrent_operations), 
        ("Pool Statistics", test_pool_statistics),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ✗ Test crashed: {e}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print("Integration Test Summary")
    print("=" * 50)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All integration tests passed!")
        print("The connection pool is ready for production use.")
    else:
        print(f"\n⚠️  {failed} test(s) failed.")
    
    # Show final pool stats
    try:
        stats = get_pool_statistics()
        print(f"\nFinal Pool Status:")
        print(f"  Efficiency: {stats['hit_ratio']:.1%} hit ratio")
        print(f"  Utilization: {stats['active_connections']}/{stats['pool_size']} active")
        print(f"  Performance: {stats['total_created']} total connections created")
    except:
        pass
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)