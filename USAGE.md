# A1 Rent-It Incentive Program - Usage Guide

## Quick Start Guide

### For Employees
1. **Access the System**: Go to `http://rfid:7409/` (or your configured port)
2. **Vote for Peers**: Enter initials to vote for colleagues (+1 or -1)
3. **Play Minigames**: Access casino games from the employee portal
4. **Check Your Score**: View current points and ranking
5. **Submit Feedback**: Use the feedback form to communicate with management

### For Admins
1. **Login**: Navigate to `/admin_login`
   - Username: `admin1`, `admin2`, or `admin3`
   - Password: `Broadway8101`
2. **Manage Points**: Adjust employee scores with reasons
3. **Control Voting**: Start, pause, and end voting sessions
4. **Export Data**: Download CSV reports for payroll
5. **Award Minigames**: Give game tokens to employees

### For Master Admin
1. **Login**: Navigate to `/admin_login`
   - Username: `master`
   - Password: `Master8101`
2. **Full System Access**: All admin features plus:
   - Add/remove other admins
   - Change system settings
   - Perform master reset
   - Configure minigame prizes

---

## Employee Portal Features

### Voting System
- **Weekly Sessions**: Vote once per active session
- **Peer Recognition**: Give +1 votes to recognize good work
- **Feedback**: Give -1 votes for improvement areas
- **Anonymous**: Voting is by initials but results are aggregated

### Minigames 🎰
**How to Play:**
1. Wait for admin to award you game tokens
2. Access "Play Games" from employee portal
3. Choose from available games:
   - **Slot Machine**: Click spin, match symbols to win
   - **Scratch Cards**: Click to reveal prizes
   - **Wheel of Fortune**: Spin the wheel for prizes

**Prize Types:**
- **Points**: Directly added to your score
- **Special Prizes**: Extra breaks, gift cards, company swag
  - These show in your history and require manual fulfillment

### Your Dashboard
- **Current Score**: See your point total
- **Role & Ranking**: View your position among peers
- **Game History**: Track all minigames played and prizes won
- **Payout Preview**: Estimate potential bonus based on current performance

---

## Admin Operations Guide

### Point Management
**Quick Adjust**: Fast point changes with password protection
- Navigate to Quick Adjust panel
- Enter employee initials
- Add/subtract points with reason
- Password required for security

**Bulk Operations**: 
- Use admin panel for multiple employees
- Apply standardized rules
- Export changes for audit

### Voting Session Management
**Starting Sessions**:
1. Go to "Start Voting" from admin panel
2. Set session parameters
3. Announce to employees
4. Monitor participation

**Ending Sessions**:
1. Close voting when period ends
2. Review results before applying
3. Apply point changes based on thresholds
4. Export results for records

### Minigame Administration
**Awarding Games**:
1. Access admin panel
2. Select employee(s)
3. Choose game type and quantity
4. Games appear in employee portal

**Prize Management**:
- Point prizes: Automatically added to employee scores
- Non-point prizes: Flag for manual fulfillment
- Track redemption through admin panel

### Data Export & Reporting
**Monthly Reports**:
- Export voting data for specific months
- Download payout calculations
- Generate audit trails

**Backup Operations**:
- Use settings panel to configure backup location
- Export full database for disaster recovery
- Schedule regular backups

---

## Troubleshooting Common Issues

### Audio Problems
**Symptoms**: No sounds during minigames, console errors
**Solutions**:
1. Check browser audio settings
2. Refresh page (Ctrl+F5)
3. Verify audio files exist in `/static/` directory
4. Toggle sound setting in admin panel

### CSRF Token Errors
**Symptoms**: "CSRF validation failed" on form submissions
**Solutions**:
1. Refresh the page to get new token
2. Clear browser cache
3. Check if cookies are enabled
4. Contact admin if problem persists

### Minigame Display Issues
**Symptoms**: Games not loading, prizes showing incorrectly
**Solutions**:
1. Clear browser cache
2. Check JavaScript console for errors
3. Verify database connection
4. Restart service if needed

### Vote Submission Problems
**Symptoms**: Cannot submit votes, "already voted" errors
**Solutions**:
1. Verify voting session is active
2. Check if you've already voted this session
3. Confirm employee initials are correct
4. Contact admin to reset vote if needed

---

## System Administration

### Service Management
```bash
# Check service status
sudo systemctl status incent-dev

# Restart service
sudo systemctl restart incent-dev

# View logs
sudo journalctl -u incent-dev -f

# Check application logs
tail -f /home/tim/incentDev/logs/app.log
```

### Database Maintenance
```bash
# Backup database
cp incentive.db incentive.db.backup-$(date +%Y%m%d)

# Initialize/update database schema
python init_db.py

# Check database integrity
sqlite3 incentive.db "PRAGMA integrity_check;"
```

### Configuration Updates
**Settings via Web Interface**:
- Master admin can modify all settings
- Changes take effect immediately
- Backup settings before major changes

**Direct Configuration**:
- Edit `config.py` for system-level changes
- Modify templates for UI changes
- Restart service after code changes

---

## Best Practices

### For Employees
- Vote thoughtfully and constructively
- Play minigames responsibly
- Submit detailed feedback
- Check dashboard regularly

### For Admins  
- Document all point adjustments
- Communicate voting periods clearly
- Monitor system performance
- Review feedback regularly
- Backup data before major changes

### For System Health
- Monitor logs for errors
- Keep audio files updated
- Regular database backups
- Test minigames after updates
- Review user feedback for system issues

---

## Support & Contact

**Internal Support**: Contact Tim Sandahl for:
- System issues or bugs
- Feature requests
- Database problems
- Configuration help

**Emergency Procedures**: 
1. Service fails: Restart with `sudo systemctl restart incent-dev`
2. Database corruption: Restore from backup
3. Audio issues: Run audio fix script
4. CSRF problems: Clear browser cache and restart service

**Logs Location**: `/home/tim/incentDev/logs/`
**Backup Location**: Configurable via admin settings (default: `/home/tim/incentDev/backups/`)