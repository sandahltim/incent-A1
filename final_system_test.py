#!/usr/bin/env python3
"""
Final Comprehensive System Test
Test all components of the mini-games analytics system
"""

import sqlite3
import json
import requests
import random
from datetime import datetime
from config import Config

def test_game_simulation():
    """Simulate playing games and verify analytics tracking"""
    print("🎮 Testing Game Simulation and Analytics...")
    
    conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
    conn.row_factory = sqlite3.Row
    
    # Test data collection before simulation
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as before_count FROM mini_game_payouts")
    before_count = cursor.fetchone()['before_count']
    
    cursor.execute("SELECT COUNT(*) as before_games FROM mini_games")
    before_games = cursor.fetchone()['before_games']
    
    print(f"  Before: {before_games} games, {before_count} payouts")
    
    # Simulate some game outcomes with proper dollar values
    test_games = [
        ('E001', 'slot', 'points', 10, 1.0),
        ('E002', 'scratch', 'bonus', 0, 15.0),
        ('E003', 'wheel', 'mini_game', 1, 2.5),
        ('E004', 'roulette', 'points', 5, 0.5),
        ('E005', 'dice', 'points', 15, 1.5)
    ]
    
    for employee_id, game_type, prize_type, prize_amount, dollar_value in test_games:
        try:
            # Add a mini game first
            cursor.execute("""
                INSERT INTO mini_games (employee_id, game_type, awarded_date, played_date, status, outcome)
                VALUES (?, ?, datetime('now'), datetime('now'), 'played', ?)
            """, (employee_id, game_type, json.dumps({
                'prize_type': prize_type,
                'prize_amount': prize_amount,
                'prize_description': f'Test {prize_type} prize',
                'win': True
            })))
            
            game_id = cursor.lastrowid
            
            # Record payout
            cursor.execute("""
                INSERT INTO mini_game_payouts 
                (game_id, employee_id, game_type, prize_type, prize_amount, dollar_value)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (game_id, employee_id, game_type, prize_type, prize_amount, dollar_value))
            
            print(f"    ✅ {game_type} game for {employee_id}: {prize_type} ${dollar_value}")
            
        except Exception as e:
            print(f"    ❌ Error simulating game: {e}")
    
    conn.commit()
    
    # Test data collection after simulation
    cursor.execute("SELECT COUNT(*) as after_count FROM mini_game_payouts")
    after_count = cursor.fetchone()['after_count']
    
    cursor.execute("SELECT COUNT(*) as after_games FROM mini_games")
    after_games = cursor.fetchone()['after_games']
    
    print(f"  After: {after_games} games, {after_count} payouts")
    print(f"  Added: {after_games - before_games} games, {after_count - before_count} payouts")
    
    conn.close()
    return after_count > before_count

def test_analytics_queries():
    """Test analytics calculations"""
    print("📊 Testing Analytics Calculations...")
    
    conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Test 1: Total payout calculation
        cursor.execute("""
            SELECT 
                COUNT(*) as total_payouts,
                SUM(dollar_value) as total_value,
                AVG(dollar_value) as avg_value,
                MIN(dollar_value) as min_value,
                MAX(dollar_value) as max_value
            FROM mini_game_payouts
        """)
        
        totals = cursor.fetchone()
        print(f"  📈 Payout Summary:")
        print(f"    Total Payouts: {totals['total_payouts']}")
        print(f"    Total Value: ${totals['total_value']:.2f}")
        print(f"    Average: ${totals['avg_value']:.2f}")
        print(f"    Range: ${totals['min_value']:.2f} - ${totals['max_value']:.2f}")
        
        # Test 2: Win rates by game type
        cursor.execute("""
            SELECT 
                mg.game_type,
                COUNT(*) as total_games,
                COUNT(mp.id) as winning_games,
                ROUND(CAST(COUNT(mp.id) AS FLOAT) / COUNT(*) * 100, 1) as win_rate,
                COALESCE(SUM(mp.dollar_value), 0) as total_winnings
            FROM mini_games mg
            LEFT JOIN mini_game_payouts mp ON mg.id = mp.game_id
            WHERE mg.status = 'played'
            GROUP BY mg.game_type
            ORDER BY win_rate DESC
        """)
        
        print(f"  🎯 Win Rates by Game Type:")
        win_rates = cursor.fetchall()
        for game in win_rates:
            print(f"    {game['game_type']}: {game['win_rate']}% ({game['winning_games']}/{game['total_games']} games, ${game['total_winnings']:.2f})")
        
        # Test 3: Daily trends
        cursor.execute("""
            SELECT 
                DATE(payout_date) as date,
                COUNT(*) as payouts,
                SUM(dollar_value) as daily_value,
                COUNT(DISTINCT employee_id) as unique_players
            FROM mini_game_payouts
            WHERE payout_date >= date('now', '-7 days')
            GROUP BY DATE(payout_date)
            ORDER BY date DESC
        """)
        
        print(f"  📅 Recent Daily Activity:")
        daily_trends = cursor.fetchall()
        for day in daily_trends:
            print(f"    {day['date']}: {day['payouts']} payouts, ${day['daily_value']:.2f}, {day['unique_players']} players")
        
        success = len(win_rates) > 0 and totals['total_payouts'] > 0
        
    except Exception as e:
        print(f"    ❌ Analytics query error: {e}")
        success = False
    finally:
        conn.close()
    
    return success

def test_system_analytics_entry():
    """Test system analytics table functionality"""
    print("🔧 Testing System Analytics Entry...")
    
    conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Check if we have analytics entries
        cursor.execute("SELECT COUNT(*) as count FROM system_analytics")
        count = cursor.fetchone()['count']
        print(f"  📋 Found {count} system analytics entries")
        
        if count > 0:
            cursor.execute("""
                SELECT 
                    period_start, period_end, total_games_played, total_payout_value,
                    win_rate, average_payout, active_employees
                FROM system_analytics 
                ORDER BY created_at DESC 
                LIMIT 1
            """)
            
            latest = cursor.fetchone()
            print(f"  📊 Latest Analytics Entry:")
            print(f"    Period: {latest['period_start']} to {latest['period_end']}")
            print(f"    Games: {latest['total_games_played']}, Payout: ${latest['total_payout_value']:.2f}")
            print(f"    Win Rate: {latest['win_rate']:.1f}%, Avg Payout: ${latest['average_payout']:.2f}")
            print(f"    Active Players: {latest['active_employees']}")
            
        success = True
        
    except Exception as e:
        print(f"    ❌ System analytics error: {e}")
        success = False
    finally:
        conn.close()
    
    return success

def test_prize_value_configurations():
    """Test prize value configurations"""
    print("💰 Testing Prize Value Configurations...")
    
    conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM prize_values ORDER BY prize_type")
        prize_configs = cursor.fetchall()
        
        print(f"  💎 Prize Value Configurations:")
        for config in prize_configs:
            managed = "System" if config['is_system_managed'] else "Manual"
            rate = f", Rate: ${config['point_to_dollar_rate']:.2f}" if config['point_to_dollar_rate'] else ""
            print(f"    {config['prize_type']}: ${config['base_dollar_value']:.2f} ({managed}{rate})")
        
        success = len(prize_configs) > 0
        
    except Exception as e:
        print(f"    ❌ Prize configuration error: {e}")
        success = False
    finally:
        conn.close()
    
    return success

def test_api_connectivity():
    """Test basic API connectivity"""
    print("🌐 Testing API Connectivity...")
    
    try:
        # Test public data endpoint
        response = requests.get("http://localhost:7409/data", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Data endpoint accessible")
            print(f"    Response size: {len(str(data))} characters")
            if 'scoreboard' in data:
                print(f"    Scoreboard entries: {len(data['scoreboard'])}")
            success = True
        else:
            print(f"  ❌ Data endpoint returned {response.status_code}")
            success = False
    except Exception as e:
        print(f"  ❌ API connectivity error: {e}")
        success = False
    
    return success

def run_comprehensive_test():
    """Run all tests"""
    print("🚀 COMPREHENSIVE MINI-GAMES ANALYTICS TEST")
    print("=" * 60)
    
    results = []
    
    # Run all tests
    tests = [
        ("Game Simulation", test_game_simulation),
        ("Analytics Queries", test_analytics_queries),
        ("System Analytics", test_system_analytics_entry),
        ("Prize Configurations", test_prize_value_configurations),
        ("API Connectivity", test_api_connectivity)
    ]
    
    for test_name, test_func in tests:
        print()
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Results summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOVERALL: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! System is ready for production.")
    elif passed >= total * 0.8:
        print("⚠️  MOSTLY WORKING - Minor issues remain.")
    else:
        print("❌ SIGNIFICANT ISSUES - Not ready for production.")
    
    return passed == total

if __name__ == "__main__":
    run_comprehensive_test()