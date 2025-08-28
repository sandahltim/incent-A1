#!/usr/bin/env python3
"""
Comprehensive Debug Script for Mini-Games Analytics System
Tests database integrity, API endpoints, game logic, and analytics functionality
"""

import sqlite3
import json
import requests
import sys
import traceback
from datetime import datetime, timedelta
from config import Config

class AnalyticsDebugger:
    def __init__(self):
        self.db_path = Config.INCENTIVE_DB_FILE
        self.base_url = "http://localhost:7409"
        self.issues = []
        self.success_count = 0
        self.test_count = 0
        
    def log_issue(self, category, severity, message):
        """Log a debug issue"""
        self.issues.append({
            'category': category,
            'severity': severity,  # CRITICAL, HIGH, MEDIUM, LOW
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        print(f"[{severity}] {category}: {message}")
        
    def log_success(self, message):
        """Log a successful test"""
        self.success_count += 1
        print(f"[SUCCESS] {message}")
        
    def test_database_schema_integrity(self):
        """Test 1: Database Schema Integrity"""
        print("\n=== TESTING DATABASE SCHEMA INTEGRITY ===")
        self.test_count += 1
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check if new analytics tables exist
            required_tables = ['mini_game_payouts', 'system_analytics', 'prize_values', 'game_odds', 'game_prizes']
            for table in required_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone():
                    self.log_success(f"Table '{table}' exists")
                else:
                    self.log_issue('Database Schema', 'CRITICAL', f"Missing required table: {table}")
            
            # Check foreign key constraints
            cursor.execute("PRAGMA foreign_key_check")
            violations = cursor.fetchall()
            if violations:
                self.log_issue('Database Schema', 'HIGH', f"Foreign key violations found: {len(violations)} violations")
                for violation in violations[:5]:  # Show first 5
                    self.log_issue('Database Schema', 'HIGH', f"FK violation: {dict(violation)}")
            else:
                self.log_success("No foreign key violations found")
                
            # Check table structures
            for table in required_tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                if columns:
                    column_names = [col['name'] for col in columns]
                    self.log_success(f"Table '{table}' has {len(columns)} columns: {column_names}")
                    
                    # Check specific important columns
                    if table == 'mini_game_payouts':
                        required_cols = ['game_id', 'employee_id', 'game_type', 'prize_type', 'dollar_value']
                        for col in required_cols:
                            if col not in column_names:
                                self.log_issue('Database Schema', 'HIGH', f"Missing column '{col}' in {table}")
                    
                    if table == 'prize_values':
                        if 'base_dollar_value' not in column_names:
                            self.log_issue('Database Schema', 'HIGH', f"Missing column 'base_dollar_value' in {table}")
                            
            conn.close()
            
        except Exception as e:
            self.log_issue('Database Schema', 'CRITICAL', f"Database access error: {str(e)}")
            
    def test_data_consistency(self):
        """Test 2: Data Consistency"""
        print("\n=== TESTING DATA CONSISTENCY ===")
        self.test_count += 1
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check mini_game_payouts data consistency
            cursor.execute("SELECT COUNT(*) as count FROM mini_game_payouts")
            payout_count = cursor.fetchone()['count']
            self.log_success(f"Found {payout_count} payout records")
            
            if payout_count > 0:
                # Check for null dollar values
                cursor.execute("SELECT COUNT(*) as count FROM mini_game_payouts WHERE dollar_value IS NULL")
                null_values = cursor.fetchone()['count']
                if null_values > 0:
                    self.log_issue('Data Consistency', 'MEDIUM', f"{null_values} records have NULL dollar_value")
                else:
                    self.log_success("No NULL dollar_value records found")
                    
                # Check for negative dollar values
                cursor.execute("SELECT COUNT(*) as count FROM mini_game_payouts WHERE dollar_value < 0")
                negative_values = cursor.fetchone()['count']
                if negative_values > 0:
                    self.log_issue('Data Consistency', 'HIGH', f"{negative_values} records have negative dollar_value")
                else:
                    self.log_success("No negative dollar_value records found")
                    
            # Check prize_values data
            cursor.execute("SELECT * FROM prize_values")
            prize_values = cursor.fetchall()
            if prize_values:
                self.log_success(f"Found {len(prize_values)} prize value configurations")
                for pv in prize_values:
                    if pv['base_dollar_value'] < 0:
                        self.log_issue('Data Consistency', 'MEDIUM', f"Negative base_dollar_value for {pv['prize_type']}")
            else:
                self.log_issue('Data Consistency', 'HIGH', "No prize value configurations found")
                
            # Check game odds data
            cursor.execute("SELECT * FROM game_odds")
            odds = cursor.fetchall()
            if odds:
                self.log_success(f"Found odds for {len(odds)} game types")
                for odd in odds:
                    if odd['win_probability'] < 0 or odd['win_probability'] > 1:
                        self.log_issue('Data Consistency', 'HIGH', f"Invalid win_probability for {odd['game_type']}: {odd['win_probability']}")
            else:
                self.log_issue('Data Consistency', 'CRITICAL', "No game odds found - games will use fallback values")
                
            # Check game prizes data
            cursor.execute("SELECT game_type, COUNT(*) as prize_count FROM game_prizes GROUP BY game_type")
            prize_counts = cursor.fetchall()
            if prize_counts:
                for pc in prize_counts:
                    self.log_success(f"Game type '{pc['game_type']}' has {pc['prize_count']} prizes configured")
            else:
                self.log_issue('Data Consistency', 'CRITICAL', "No game prizes found - games will use fallback values")
                
            conn.close()
            
        except Exception as e:
            self.log_issue('Data Consistency', 'CRITICAL', f"Data consistency check error: {str(e)}")
            
    def test_api_endpoints(self):
        """Test 3: API Endpoint Functionality"""
        print("\n=== TESTING API ENDPOINTS ===")
        self.test_count += 1
        
        # Test unauthenticated access (should fail)
        endpoints = [
            '/admin/prize_values',
            '/admin/payout_analytics',
            '/admin/system_trends',
            '/admin/adjust_odds_by_payout'
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                if response.status_code == 403:
                    self.log_success(f"Endpoint {endpoint} properly requires authentication")
                else:
                    self.log_issue('API Security', 'HIGH', f"Endpoint {endpoint} returned {response.status_code} instead of 403")
            except requests.exceptions.RequestException as e:
                self.log_issue('API Connectivity', 'HIGH', f"Cannot connect to {endpoint}: {str(e)}")
                
        # Test data endpoint (should work without auth)
        try:
            response = requests.get(f"{self.base_url}/data", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_success(f"Data endpoint accessible, returned {len(str(data))} characters")
            else:
                self.log_issue('API Connectivity', 'MEDIUM', f"Data endpoint returned {response.status_code}")
        except Exception as e:
            self.log_issue('API Connectivity', 'HIGH', f"Data endpoint error: {str(e)}")
            
    def test_game_logic(self):
        """Test 4: Game Logic and Prize Calculation"""
        print("\n=== TESTING GAME LOGIC ===")
        self.test_count += 1
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            
            # Test each game type's prize configuration
            game_types = ['slot', 'scratch', 'roulette', 'wheel', 'dice']
            
            for game_type in game_types:
                # Check if game has odds configured
                odds_row = conn.execute("SELECT * FROM game_odds WHERE game_type=?", (game_type,)).fetchone()
                if odds_row:
                    self.log_success(f"Game '{game_type}' has odds configured: win={odds_row['win_probability']}, jackpot={odds_row['jackpot_probability']}")
                    
                    # Validate probability ranges
                    if not (0 <= odds_row['win_probability'] <= 1):
                        self.log_issue('Game Logic', 'HIGH', f"Invalid win probability for {game_type}: {odds_row['win_probability']}")
                    if not (0 <= odds_row['jackpot_probability'] <= 1):
                        self.log_issue('Game Logic', 'HIGH', f"Invalid jackpot probability for {game_type}: {odds_row['jackpot_probability']}")
                else:
                    self.log_issue('Game Logic', 'MEDIUM', f"Game '{game_type}' has no odds configured, will use defaults")
                
                # Check if game has prizes configured
                prizes = conn.execute("SELECT * FROM game_prizes WHERE game_type=?", (game_type,)).fetchall()
                if prizes:
                    total_prob = sum(p['probability'] for p in prizes)
                    self.log_success(f"Game '{game_type}' has {len(prizes)} prizes, total probability: {total_prob}")
                    
                    # Check probability consistency
                    if total_prob > 1.1 or total_prob < 0.1:
                        self.log_issue('Game Logic', 'HIGH', f"Unusual total probability for {game_type}: {total_prob}")
                        
                    # Check for dollar values
                    dollar_values = [p['dollar_value'] for p in prizes if p['dollar_value'] is not None]
                    if dollar_values:
                        avg_value = sum(dollar_values) / len(dollar_values)
                        self.log_success(f"Game '{game_type}' average prize value: ${avg_value:.2f}")
                    else:
                        self.log_issue('Game Logic', 'MEDIUM', f"Game '{game_type}' has no dollar values set")
                else:
                    self.log_issue('Game Logic', 'MEDIUM', f"Game '{game_type}' has no prizes configured, will use defaults")
                    
            conn.close()
            
        except Exception as e:
            self.log_issue('Game Logic', 'CRITICAL', f"Game logic test error: {str(e)}")
            
    def test_analytics_calculations(self):
        """Test 5: Analytics Calculations"""
        print("\n=== TESTING ANALYTICS CALCULATIONS ===")
        self.test_count += 1
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            
            # Test basic analytics queries
            
            # 1. Total payouts calculation
            total_payouts = conn.execute("SELECT COUNT(*) as count, SUM(dollar_value) as total FROM mini_game_payouts").fetchone()
            if total_payouts['count'] > 0:
                self.log_success(f"Analytics: {total_payouts['count']} total payouts worth ${total_payouts['total']:.2f}")
            else:
                self.log_issue('Analytics', 'LOW', "No payout data available for analytics")
                
            # 2. Win rate calculation
            win_rates = conn.execute("""
                SELECT 
                    mg.game_type,
                    COUNT(*) as total_games,
                    COUNT(mp.id) as winning_games,
                    ROUND(CAST(COUNT(mp.id) AS FLOAT) / COUNT(*) * 100, 2) as win_rate_percent
                FROM mini_games mg
                LEFT JOIN mini_game_payouts mp ON mg.id = mp.game_id
                WHERE mg.status = 'played'
                GROUP BY mg.game_type
            """).fetchall()
            
            for wr in win_rates:
                self.log_success(f"Win rate for {wr['game_type']}: {wr['win_rate_percent']}% ({wr['winning_games']}/{wr['total_games']})")
                
                # Validate win rates are reasonable
                if wr['win_rate_percent'] > 80:
                    self.log_issue('Analytics', 'MEDIUM', f"Unusually high win rate for {wr['game_type']}: {wr['win_rate_percent']}%")
                elif wr['win_rate_percent'] < 5:
                    self.log_issue('Analytics', 'MEDIUM', f"Unusually low win rate for {wr['game_type']}: {wr['win_rate_percent']}%")
                    
            # 3. Daily trends
            daily_trends = conn.execute("""
                SELECT 
                    DATE(payout_date) as date,
                    COUNT(*) as daily_payouts,
                    SUM(dollar_value) as daily_value
                FROM mini_game_payouts 
                WHERE payout_date >= date('now', '-7 days')
                GROUP BY DATE(payout_date)
                ORDER BY date
            """).fetchall()
            
            if daily_trends:
                for trend in daily_trends:
                    self.log_success(f"Daily trend {trend['date']}: {trend['daily_payouts']} payouts, ${trend['daily_value']:.2f} value")
            else:
                self.log_issue('Analytics', 'LOW', "No recent daily trend data available")
                
            conn.close()
            
        except Exception as e:
            self.log_issue('Analytics', 'CRITICAL', f"Analytics calculation error: {str(e)}")
            
    def test_error_handling(self):
        """Test 6: Error Handling and Edge Cases"""
        print("\n=== TESTING ERROR HANDLING ===")
        self.test_count += 1
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            
            # Test for orphaned records
            orphaned_payouts = conn.execute("""
                SELECT COUNT(*) as count 
                FROM mini_game_payouts 
                WHERE game_id NOT IN (SELECT id FROM mini_games)
            """).fetchone()
            
            if orphaned_payouts['count'] > 0:
                self.log_issue('Error Handling', 'HIGH', f"{orphaned_payouts['count']} orphaned payout records found")
            else:
                self.log_success("No orphaned payout records found")
                
            # Test for missing employee references
            missing_employees = conn.execute("""
                SELECT DISTINCT employee_id 
                FROM mini_game_payouts 
                WHERE employee_id NOT IN (SELECT employee_id FROM employees)
            """).fetchall()
            
            if missing_employees:
                self.log_issue('Error Handling', 'HIGH', f"Payout records reference missing employees: {[e['employee_id'] for e in missing_employees]}")
            else:
                self.log_success("All payout records reference valid employees")
                
            # Test for games with missing odds
            games_without_odds = conn.execute("""
                SELECT DISTINCT game_type 
                FROM mini_games 
                WHERE game_type NOT IN (SELECT game_type FROM game_odds)
            """).fetchall()
            
            if games_without_odds:
                game_types = [g['game_type'] for g in games_without_odds]
                self.log_issue('Error Handling', 'MEDIUM', f"Games without odds configuration: {game_types}")
            else:
                self.log_success("All game types have odds configured")
                
            conn.close()
            
        except Exception as e:
            self.log_issue('Error Handling', 'CRITICAL', f"Error handling test failed: {str(e)}")
            
    def generate_report(self):
        """Generate comprehensive debug report"""
        print("\n" + "="*80)
        print("COMPREHENSIVE DEBUG REPORT")
        print("="*80)
        
        # Summary
        print(f"\nSUMMARY:")
        print(f"  Tests Run: {self.test_count}")
        print(f"  Successful Checks: {self.success_count}")
        print(f"  Issues Found: {len(self.issues)}")
        
        # Issues by severity
        critical = [i for i in self.issues if i['severity'] == 'CRITICAL']
        high = [i for i in self.issues if i['severity'] == 'HIGH']
        medium = [i for i in self.issues if i['severity'] == 'MEDIUM']
        low = [i for i in self.issues if i['severity'] == 'LOW']
        
        print(f"\nISSUES BY SEVERITY:")
        print(f"  🔴 CRITICAL: {len(critical)}")
        print(f"  🟠 HIGH: {len(high)}")
        print(f"  🟡 MEDIUM: {len(medium)}")
        print(f"  🟢 LOW: {len(low)}")
        
        # Production readiness assessment
        print(f"\nPRODUCTION READINESS ASSESSMENT:")
        if critical:
            print("  ❌ NOT PRODUCTION READY - Critical issues found")
        elif high:
            print("  ⚠️  CAUTION - High priority issues should be addressed")
        elif medium:
            print("  ⚡ MOSTLY READY - Medium priority issues are acceptable")
        else:
            print("  ✅ PRODUCTION READY - No critical issues found")
            
        # Detailed issues
        if self.issues:
            print(f"\nDETAILED ISSUES:")
            for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                severity_issues = [i for i in self.issues if i['severity'] == severity]
                if severity_issues:
                    print(f"\n{severity} ISSUES:")
                    for issue in severity_issues:
                        print(f"  [{issue['category']}] {issue['message']}")
                        
        # Recommendations
        print(f"\nRECOMMENDATIONS:")
        
        if critical:
            print("  1. Address all CRITICAL issues before production deployment")
            print("  2. Run database integrity checks and repairs")
            print("  3. Test all API endpoints with proper authentication")
            
        if high:
            print("  4. Fix HIGH priority data consistency issues")
            print("  5. Validate all foreign key relationships")
            print("  6. Review game logic and prize calculations")
            
        print("  7. Implement comprehensive error logging")
        print("  8. Set up monitoring for analytics system performance")
        print("  9. Create automated tests for continued validation")
        print("  10. Document any known limitations or workarounds")
        
        print("\n" + "="*80)
        
    def run_all_tests(self):
        """Run complete debug suite"""
        print("MINI-GAMES ANALYTICS DEBUG SUITE")
        print("="*50)
        
        try:
            self.test_database_schema_integrity()
            self.test_data_consistency()
            self.test_api_endpoints()
            self.test_game_logic()
            self.test_analytics_calculations()
            self.test_error_handling()
            
        except Exception as e:
            self.log_issue('System', 'CRITICAL', f"Debug suite crashed: {str(e)}")
            traceback.print_exc()
            
        finally:
            self.generate_report()

if __name__ == "__main__":
    debugger = AnalyticsDebugger()
    debugger.run_all_tests()