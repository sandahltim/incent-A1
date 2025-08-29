# Developer Troubleshooting Technical Documentation

**Version**: 1.0.0  
**Date**: August 29, 2025  
**Target Audience**: Developers, System Administrators, Technical Support Staff  

## Table of Contents

1. [Common Issues and Solutions](#common-issues-and-solutions)
2. [CSRF Related Issues](#csrf-related-issues)
3. [Dual Game System Issues](#dual-game-system-issues)
4. [Database Issues](#database-issues)
5. [Performance Issues](#performance-issues)
6. [Service and Deployment Issues](#service-and-deployment-issues)
7. [API and Integration Issues](#api-and-integration-issues)
8. [Logging and Monitoring](#logging-and-monitoring)
9. [Development Environment Issues](#development-environment-issues)
10. [Emergency Procedures](#emergency-procedures)

## Common Issues and Solutions

### Issue: Application Won't Start

**Symptoms**:
- Service fails to start
- Port already in use errors
- Import errors in Python

**Diagnosis Steps**:
```bash
# Check if service is running
sudo systemctl status incent-dev.service

# Check port usage
sudo netstat -tlnp | grep 7410

# Check Python environment
source venv/bin/activate
python -c "import flask, sqlite3; print('Dependencies OK')"

# Check database file permissions
ls -la incentive.db
```

**Common Solutions**:

1. **Port Already in Use**:
```bash
# Find and kill process using port 7410
sudo lsof -i :7410
sudo kill -9 <PID>

# Or change port in configuration
echo "PORT=7411" >> .env
```

2. **Python Dependencies Missing**:
```bash
# Reinstall dependencies
source venv/bin/activate
pip install -r requirements.txt

# Check for conflicting packages
pip list | grep -i flask
```

3. **Database Permission Issues**:
```bash
# Fix database permissions
sudo chown tim:tim incentive.db
chmod 660 incentive.db

# Check directory permissions
ls -la /home/tim/incentDev/
```

4. **Configuration Issues**:
```bash
# Verify configuration
python -c "from config import Config; print(Config.SECRET_KEY[:10])"

# Check environment variables
env | grep FLASK
```

### Issue: Database Connection Errors

**Symptoms**:
- "Database is locked" errors
- Connection timeout errors
- Database file not found

**Diagnosis Steps**:
```bash
# Check database file
sqlite3 incentive.db "PRAGMA integrity_check;"

# Check for locks
sqlite3 incentive.db "PRAGMA lock_status;"

# Check disk space
df -h /home/tim/incentDev/

# Check database size
ls -lh incentive.db*
```

**Solutions**:

1. **Database Locked**:
```bash
# Check for zombie processes
ps aux | grep python | grep app.py

# Restart service to clear locks
sudo systemctl restart incent-dev.service

# Manual unlock (use with caution)
sqlite3 incentive.db "PRAGMA wal_checkpoint(FULL);"
```

2. **Database Corruption**:
```bash
# Check integrity
sqlite3 incentive.db "PRAGMA integrity_check;"

# Restore from backup
cp backups/incentive.db.bak-$(date +%Y%m%d) incentive.db

# Rebuild database if necessary
python init_db.py
python setup_dual_game_system.py
```

## CSRF Related Issues

### Issue: CSRF Token Not Found

**Symptoms**:
- JavaScript errors: "CSRF token not found"
- Failed form submissions
- 400 errors with CSRF validation messages

**Diagnosis**:
```javascript
// Check for CSRF token in browser console
console.log(document.querySelector('meta[name="csrf-token"]'));

// Check if getCSRFToken function works
console.log(getCSRFToken());
```

**Solutions**:

1. **Missing Meta Tag**:
```html
<!-- Ensure this is in base template -->
<meta name="csrf-token" content="{{ csrf_token() }}">
```

2. **JavaScript Token Retrieval**:
```javascript
// Robust CSRF token retrieval
function getCSRFToken() {
    // Try meta tag first
    let token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    // Try form input as fallback
    if (!token) {
        token = document.querySelector('input[name="csrf_token"]')?.value;
    }
    
    if (!token) {
        console.error('CSRF token not found');
        // Force page refresh to get new token
        location.reload();
    }
    
    return token;
}
```

### Issue: CSRF Validation Failures

**Symptoms**:
- 400 errors on POST requests
- "CSRF validation failed" messages
- Forms work sometimes but not always

**Diagnosis Steps**:
```bash
# Check server logs for CSRF errors
sudo journalctl -u incent-dev.service | grep -i csrf

# Check Flask-WTF configuration
python -c "from app import app; print(app.config.get('WTF_CSRF_ENABLED'))"
```

**Solutions**:

1. **Session Issues**:
```python
# Add to app.py for debugging
@app.before_request
def debug_csrf():
    if request.method == 'POST':
        logging.debug(f"Session ID: {session.get('csrf_token', 'None')}")
        logging.debug(f"Form CSRF: {request.form.get('csrf_token', 'None')}")
        logging.debug(f"Header CSRF: {request.headers.get('X-CSRFToken', 'None')}")
```

2. **Multiple Tab Issues**:
```javascript
// Refresh CSRF token periodically
setInterval(function() {
    fetch('/api/csrf-token')
        .then(response => response.json())
        .then(data => {
            document.querySelector('meta[name="csrf-token"]').setAttribute('content', data.csrf_token);
        });
}, 5 * 60 * 1000); // Every 5 minutes
```

3. **Mixed Content Issues**:
```python
# Ensure consistent protocol
@app.before_request
def force_https():
    if not request.is_secure and request.headers.get('X-Forwarded-Proto') != 'https':
        # Log warning in development
        logging.warning(f"Insecure request: {request.url}")
```

## Dual Game System Issues

### Issue: Token Exchange Failures

**Symptoms**:
- "Exchange failed" messages
- Incorrect exchange rates
- Daily limits not working

**Diagnosis Steps**:
```python
# Check token account in database
python3 -c "
from services.token_economy import token_economy
account = token_economy.get_employee_token_account('E001')
print(account)
"

# Check tier settings
sqlite3 incentive.db "SELECT * FROM admin_game_config WHERE config_category = 'token_economy';"
```

**Solutions**:

1. **Rate Calculation Issues**:
```python
# Verify tier-based rates
from services.token_economy import token_economy
print(token_economy.tier_exchange_rates)

# Fix incorrect rates in database
sqlite3 incentive.db "UPDATE admin_game_config SET config_value = '8' WHERE config_key = 'silver_exchange_rate';"
```

2. **Daily Limit Reset Issues**:
```python
# Manual daily limit reset
from services.token_economy import token_economy
token_economy.reset_daily_exchange_limits()

# Check reset function
sqlite3 incentive.db "UPDATE employee_tokens SET daily_exchange_count = 0 WHERE DATE(last_exchange_date) < DATE('now');"
```

### Issue: Category A Games Not Awarding Correctly

**Symptoms**:
- Games not marked as guaranteed wins
- Wrong prize amounts
- Individual limits not enforced

**Diagnosis**:
```bash
# Check Category A game configuration
sqlite3 incentive.db "SELECT * FROM mini_games WHERE game_category = 'reward' LIMIT 5;"

# Check individual prize limits
sqlite3 incentive.db "SELECT * FROM employee_prize_limits WHERE employee_id = 'E001';"
```

**Solutions**:

1. **Game Category Issues**:
```sql
-- Fix games that should be Category A
UPDATE mini_games 
SET game_category = 'reward', guaranteed_win = 1 
WHERE game_type = 'reward_selection';
```

2. **Prize Limit Issues**:
```python
# Reset prize limits for testing
python3 -c "
from services.dual_game_manager import dual_game_manager
# Reset monthly limits (use carefully)
import sqlite3
conn = sqlite3.connect('incentive.db')
conn.execute('DELETE FROM employee_prize_limits WHERE last_reset_date < date(\"now\", \"start of month\")')
conn.commit()
"
```

### Issue: Global Prize Pools Exhausted

**Symptoms**:
- All Category B games return basic points
- "Global prize pool exhausted" messages
- High-value prizes unavailable

**Diagnosis**:
```sql
-- Check global pool status
SELECT prize_type, daily_used, daily_limit, 
       CASE WHEN daily_used >= daily_limit THEN 'EXHAUSTED' ELSE 'AVAILABLE' END as status
FROM global_prize_pools;
```

**Solutions**:

1. **Reset Daily Pools** (Admin Only):
```sql
-- Reset daily usage (emergency only)
UPDATE global_prize_pools 
SET daily_used = 0, last_daily_reset = date('now');
```

2. **Increase Pool Limits**:
```sql
-- Increase daily limits temporarily
UPDATE global_prize_pools 
SET daily_limit = daily_limit * 2 
WHERE prize_type = 'cash_prize_100';
```

## Database Issues

### Issue: Database Performance Degradation

**Symptoms**:
- Slow query responses
- Timeouts on database operations
- High CPU usage

**Diagnosis**:
```bash
# Check database size and fragmentation
sqlite3 incentive.db "PRAGMA page_count; PRAGMA page_size; PRAGMA freelist_count;"

# Analyze query performance
sqlite3 incentive.db "EXPLAIN QUERY PLAN SELECT * FROM mini_games WHERE employee_id = 'E001';"

# Check indexes
sqlite3 incentive.db ".schema" | grep INDEX
```

**Solutions**:

1. **Database Maintenance**:
```bash
# Vacuum database (reclaim space)
sqlite3 incentive.db "VACUUM;"

# Update statistics
sqlite3 incentive.db "ANALYZE;"

# Reindex all indexes
sqlite3 incentive.db "REINDEX;"
```

2. **Query Optimization**:
```sql
-- Add missing indexes
CREATE INDEX IF NOT EXISTS idx_mini_games_employee_status 
ON mini_games(employee_id, status);

CREATE INDEX IF NOT EXISTS idx_token_transactions_employee_date 
ON token_transactions(employee_id, transaction_date DESC);
```

3. **Connection Pool Tuning**:
```python
# Adjust connection pool settings in config.py
DB_POOL_SIZE = min(20, (os.cpu_count() or 1) * 2)
DB_POOL_TIMEOUT = 60
DB_POOL_MAX_OVERFLOW = 10
```

### Issue: Database Corruption

**Symptoms**:
- "Database disk image is malformed" errors
- Integrity check failures
- Missing or corrupted data

**Diagnosis**:
```bash
# Check database integrity
sqlite3 incentive.db "PRAGMA integrity_check;"

# Check for corruption signs
sqlite3 incentive.db "PRAGMA quick_check;"

# Check file system
fsck /dev/sda1  # Replace with correct device
```

**Solutions**:

1. **Restore from Backup**:
```bash
# Stop service first
sudo systemctl stop incent-dev.service

# Restore latest backup
cp backups/incentive.db.bak-$(ls backups/ | grep bak | tail -1 | cut -d'-' -f2) incentive.db

# Restart service
sudo systemctl start incent-dev.service
```

2. **Attempt Repair**:
```bash
# Dump and recreate database
sqlite3 incentive.db ".dump" > dump.sql
mv incentive.db incentive.db.corrupted
sqlite3 incentive.db < dump.sql

# Verify repair
sqlite3 incentive.db "PRAGMA integrity_check;"
```

## Performance Issues

### Issue: High Memory Usage

**Symptoms**:
- Application consuming excessive RAM
- Out of memory errors
- System becoming unresponsive

**Diagnosis**:
```bash
# Check memory usage
ps aux | grep python
top -p $(pgrep -f "python.*app.py")

# Check for memory leaks
valgrind --tool=memcheck python app.py

# Monitor memory over time
watch -n 5 "ps aux | grep python | grep app.py"
```

**Solutions**:

1. **Cache Optimization**:
```python
# Reduce cache size in config.py
CACHE_MAX_SIZE = 1000  # Reduce from 2000
CACHE_DEFAULT_TTL = 60  # Reduce TTL

# Clear cache manually
from services.cache import cache
cache.clear_all()
```

2. **Connection Pool Optimization**:
```python
# Reduce connection pool size
DB_POOL_SIZE = 5  # Reduce if too many connections
DB_POOL_MAX_OVERFLOW = 2
```

3. **Garbage Collection Tuning**:
```python
# Add to app.py
import gc
gc.set_threshold(700, 10, 10)  # More aggressive GC

# Force GC periodically
@app.after_request
def cleanup(response):
    if random.random() < 0.1:  # 10% chance
        gc.collect()
    return response
```

### Issue: Slow Response Times

**Symptoms**:
- API endpoints taking > 2 seconds
- Browser timeouts
- Poor user experience

**Diagnosis**:
```python
# Add timing middleware
@app.before_request
def start_timer():
    g.start = time.time()

@app.after_request
def log_timing(response):
    duration = time.time() - g.start
    if duration > 1.0:  # Log slow requests
        logging.warning(f"Slow request: {request.path} took {duration:.3f}s")
    return response
```

**Solutions**:

1. **Database Query Optimization**:
```sql
-- Add composite indexes for common queries
CREATE INDEX idx_game_employee_category_status 
ON mini_games(employee_id, game_category, status);

-- Optimize heavy analytics queries
CREATE MATERIALIZED VIEW IF NOT EXISTS employee_stats AS
SELECT employee_id, COUNT(*) as game_count, AVG(prize_amount) as avg_prize
FROM mini_games mg JOIN game_history gh ON mg.id = gh.mini_game_id
GROUP BY employee_id;
```

2. **Cache Strategic Data**:
```python
# Cache expensive operations
@cache.memoize(timeout=300)
def get_employee_game_summary(employee_id):
    # Expensive database operations here
    pass

# Preload common data
@app.before_first_request
def preload_cache():
    # Preload frequently accessed data
    get_employee_game_summary('E001')
```

## Service and Deployment Issues

### Issue: Service Won't Start After Deployment

**Symptoms**:
- systemctl start fails
- Permission denied errors
- Module import errors

**Diagnosis**:
```bash
# Check service status
sudo systemctl status incent-dev.service -l

# Check service logs
sudo journalctl -u incent-dev.service -n 50

# Test manual start
cd /home/tim/incentDev
source venv/bin/activate
python app.py
```

**Solutions**:

1. **Permission Issues**:
```bash
# Fix file ownership
sudo chown -R tim:tim /home/tim/incentDev

# Fix service file permissions
sudo chmod 644 /etc/systemd/system/incent-dev.service
sudo systemctl daemon-reload
```

2. **Environment Issues**:
```bash
# Verify virtual environment
source venv/bin/activate
which python
pip list | head -10

# Recreate virtual environment if needed
rm -rf venv
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: Port Configuration Problems

**Symptoms**:
- Service starts but not accessible
- "Connection refused" errors
- Wrong port being used

**Diagnosis**:
```bash
# Check which ports are listening
sudo netstat -tlnp | grep python

# Check firewall rules
sudo ufw status

# Test port connectivity
telnet localhost 7410
```

**Solutions**:

1. **Port Binding Issues**:
```python
# In app.py, ensure proper port binding
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7410))
    app.run(host='0.0.0.0', port=port, debug=False)
```

2. **Firewall Configuration**:
```bash
# Allow port through firewall
sudo ufw allow 7410/tcp

# Check iptables rules
sudo iptables -L INPUT -n | grep 7410
```

3. **Service Configuration**:
```ini
# In /etc/systemd/system/incent-dev.service
[Service]
Environment=PORT=7410
ExecStart=/home/tim/incentDev/venv/bin/python app.py
```

## API and Integration Issues

### Issue: API Endpoints Return 500 Errors

**Symptoms**:
- Internal server errors
- No specific error messages
- APIs working intermittently

**Diagnosis**:
```bash
# Check application logs
sudo journalctl -u incent-dev.service | grep ERROR

# Check specific endpoint
curl -v http://localhost:7410/api/dual-system/status

# Test with authentication
curl -H "X-CSRFToken: test" http://localhost:7410/api/games/category-b/play
```

**Solutions**:

1. **Add Error Logging**:
```python
# Add to app.py
@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Internal error: {error}")
    logging.error(f"Request: {request.method} {request.path}")
    logging.error(f"Form data: {request.form}")
    return jsonify({'error': 'Internal server error'}), 500
```

2. **Validate Input Data**:
```python
# Add input validation
@app.route('/api/games/category-b/play', methods=['POST'])
def play_category_b():
    try:
        # Validate required fields
        game_type = request.form.get('game_type')
        if not game_type or game_type not in ['slots', 'roulette', 'dice']:
            return jsonify({'error': 'Invalid game type'}), 400
            
        token_cost = int(request.form.get('token_cost', 0))
        if token_cost <= 0:
            return jsonify({'error': 'Invalid token cost'}), 400
            
    except ValueError:
        return jsonify({'error': 'Invalid input data'}), 400
```

### Issue: Frontend JavaScript Errors

**Symptoms**:
- Games not loading
- CSRF token errors
- Function undefined errors

**Diagnosis**:
```javascript
// Check in browser console
console.log(typeof playDualGameCategoryA);
console.log(getCSRFToken());

// Check for network errors
fetch('/api/dual-system/status')
  .then(response => console.log(response))
  .catch(error => console.error(error));
```

**Solutions**:

1. **Function Definition Issues**:
```html
<!-- Ensure scripts are loaded in correct order -->
<script src="/static/script.js"></script>
<script>
// Check if functions are defined before using
if (typeof getCSRFToken === 'undefined') {
    console.error('CSRF functions not loaded');
}
</script>
```

2. **Network Request Issues**:
```javascript
// Add comprehensive error handling
async function safeApiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'X-CSRFToken': getCSRFToken(),
                ...options.headers
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error(`API request failed: ${url}`, error);
        throw error;
    }
}
```

## Logging and Monitoring

### Accessing Logs

**System Logs**:
```bash
# Service logs
sudo journalctl -u incent-dev.service -f

# Application logs
tail -f /var/log/incentive/app.log

# Error logs only
tail -f /var/log/incentive/error.log
```

**Log Analysis**:
```bash
# Find CSRF errors
sudo grep -i "csrf" /var/log/incentive/app.log | tail -20

# Find database errors
sudo grep -i "database" /var/log/incentive/error.log

# Find performance issues
sudo grep "took.*s" /var/log/incentive/app.log | tail -10
```

### Performance Monitoring

**Real-time Monitoring**:
```bash
# CPU and memory usage
htop -p $(pgrep -f "python.*app.py")

# Database connections
sudo lsof -p $(pgrep -f "python.*app.py") | grep ".db"

# Network connections
sudo netstat -an | grep 7410
```

**Health Checks**:
```bash
# Application health
curl -s http://localhost:7410/api/health | jq .

# Database health
sqlite3 incentive.db "PRAGMA integrity_check;"

# Service health
systemctl is-active incent-dev.service
```

## Development Environment Issues

### Issue: Development Server Errors

**Symptoms**:
- Flask debug mode not working
- Changes not reflected
- Import path issues

**Solutions**:

1. **Debug Mode Configuration**:
```python
# In app.py for development
if __name__ == '__main__':
    import os
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=7410, debug=debug, threaded=True)
```

2. **Python Path Issues**:
```bash
# Set PYTHONPATH
export PYTHONPATH=/home/tim/incentDev:$PYTHONPATH

# Or add to app.py
import sys
sys.path.insert(0, '/home/tim/incentDev')
```

3. **Template and Static File Caching**:
```python
# Disable caching in development
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
```

### Issue: Database Schema Changes

**Symptoms**:
- Migration errors
- Column doesn't exist errors
- Foreign key constraint failures

**Solutions**:

1. **Safe Schema Updates**:
```python
# Add migration script
def migrate_database():
    conn = sqlite3.connect('incentive.db')
    
    try:
        # Check if column exists before adding
        cursor = conn.execute("PRAGMA table_info(employees)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'new_column' not in columns:
            conn.execute("ALTER TABLE employees ADD COLUMN new_column TEXT DEFAULT ''")
            conn.commit()
            print("Added new_column to employees table")
    except Exception as e:
        print(f"Migration error: {e}")
        conn.rollback()
    finally:
        conn.close()
```

2. **Backup Before Changes**:
```bash
# Always backup before schema changes
cp incentive.db "incentive.db.backup-$(date +%Y%m%d-%H%M%S)"

# Test migrations on copy first
cp incentive.db test.db
sqlite3 test.db < migration.sql
```

## Emergency Procedures

### Critical System Failure

**Immediate Response**:
```bash
# 1. Stop service to prevent further damage
sudo systemctl stop incent-dev.service

# 2. Check system resources
df -h  # Check disk space
free -m  # Check memory
ps aux | grep python  # Check for zombie processes

# 3. Backup current state
cp incentive.db "incentive.db.emergency-$(date +%Y%m%d-%H%M%S)"

# 4. Check logs for root cause
tail -50 /var/log/incentive/error.log
```

**Recovery Steps**:
```bash
# 1. Restore from latest backup if database is corrupted
cp backups/incentive.db.bak-$(ls backups/ | tail -1 | cut -d'-' -f2) incentive.db

# 2. Verify database integrity
sqlite3 incentive.db "PRAGMA integrity_check;"

# 3. Run system validation
python csrf_system_validation.py

# 4. Restart service
sudo systemctl start incent-dev.service

# 5. Test critical functions
curl http://localhost:7410/api/health
```

### Data Recovery

**Employee Data Recovery**:
```sql
-- Recover employee data from backup
.mode csv
.output employees_backup.csv
SELECT * FROM employees;

-- Import to new database
.mode csv
.import employees_backup.csv employees
```

**Game Data Recovery**:
```sql
-- Recover recent game plays
SELECT mg.*, gh.prize_description 
FROM mini_games mg 
LEFT JOIN game_history gh ON mg.id = gh.mini_game_id
WHERE mg.played_date > date('now', '-7 days')
ORDER BY mg.played_date DESC;
```

### Communication During Outages

**Status Page Updates**:
```bash
# Create status message
echo "System maintenance in progress. Expected resolution: $(date -d '+1 hour')" > /var/www/html/status.txt

# Update service status
systemctl status incent-dev.service > /tmp/service_status.txt
```

**Notification Script**:
```bash
#!/bin/bash
# notify_outage.sh
SUBJECT="Incentive System Outage - $(date)"
MESSAGE="System experiencing issues. Investigation in progress. ETA: 30 minutes."
RECIPIENTS="admin@company.com,support@company.com"

echo "$MESSAGE" | mail -s "$SUBJECT" "$RECIPIENTS"
```

---

## Quick Reference Commands

### Common Diagnostic Commands
```bash
# Service status
sudo systemctl status incent-dev.service

# View logs
sudo journalctl -u incent-dev.service -f

# Check database
sqlite3 incentive.db "PRAGMA integrity_check;"

# Test API
curl -s http://localhost:7410/api/health | jq .

# Check ports
sudo netstat -tlnp | grep 7410

# Resource usage
htop -p $(pgrep -f "python.*app.py")
```

### Emergency Commands
```bash
# Stop service
sudo systemctl stop incent-dev.service

# Backup database
cp incentive.db "incentive.db.backup-$(date +%Y%m%d-%H%M%S)"

# Restore from backup
cp backups/incentive.db.bak-latest incentive.db

# Restart service
sudo systemctl restart incent-dev.service

# Force service reload
sudo systemctl daemon-reload
sudo systemctl restart incent-dev.service
```

---

## Related Documentation

- [CSRF Security Implementation](CSRF_SECURITY_TECHNICAL_DOCS.md)
- [Dual Game System Technical Architecture](DUAL_GAME_SYSTEM_TECHNICAL_DOCS.md)
- [API Endpoint Documentation](API_ENDPOINTS_TECHNICAL_DOCS.md)
- [Database Schema Documentation](DATABASE_SCHEMA_TECHNICAL_DOCS.md)
- [Deployment and Configuration Guide](DEPLOYMENT_CONFIGURATION_TECHNICAL_DOCS.md)
- [Testing and Validation Procedures](TESTING_VALIDATION_TECHNICAL_DOCS.md)

---

**Last Updated**: August 29, 2025  
**Next Review**: September 29, 2025  
**Maintained By**: Development Team

**Emergency Contact**: For critical issues contact the development team immediately.  
**Escalation Path**: Development Team → System Administrator → Technical Lead