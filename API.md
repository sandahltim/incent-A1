# API Endpoints and Usage Guide

## Overview

The A1 Rent-It Employee Incentive System provides a comprehensive RESTful API for all system operations. This document covers all available endpoints, their parameters, responses, and usage examples.

---

## Table of Contents

- [API Architecture](#api-architecture)
- [Authentication](#authentication)
- [Public Endpoints](#public-endpoints)
- [Employee Portal Endpoints](#employee-portal-endpoints)
- [Administrative Endpoints](#administrative-endpoints)
- [Data Export Endpoints](#data-export-endpoints)
- [Mini-Game Endpoints](#mini-game-endpoints)
- [System Management Endpoints](#system-management-endpoints)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [API Examples](#api-examples)

---

## API Architecture

### Request/Response Format

**Content-Type**: `application/json` for API responses, `text/html` for page responses  
**Encoding**: UTF-8  
**Methods**: GET, POST (CSRF protected)

### Base URL Structure
```
http://your-server:7409/[endpoint]
```

### Response Format
```json
{
  "status": "success|error",
  "data": {},
  "message": "Human readable message",
  "timestamp": "ISO 8601 timestamp"
}
```

### Security Features
- CSRF token protection on all POST requests
- Session-based authentication  
- Role-based access control
- Input sanitization and validation

---

## Authentication

### Session Management

**Admin Authentication:**
```http
GET /admin_login
POST /admin_login
Content-Type: application/x-www-form-urlencoded

username=admin1&password=Broadway8101&csrf_token=...
```

**Employee Portal Authentication:**
```http
POST /employee_portal
Content-Type: application/x-www-form-urlencoded

employee_id=EMP001&pin=1234&csrf_token=...
```

### Authentication Levels

| Level | Access Rights | Session Key |
|-------|---------------|-------------|
| **Public** | Scoreboard, voting | None |
| **Employee** | Portal, games, feedback | `employee_id` |
| **Admin** | Employee management, adjustments | `admin_id` |
| **Master Admin** | Full system access | `admin_id` + `is_master` |

---

## Public Endpoints

### Main Dashboard

#### `GET /` - Main Scoreboard Page
**Purpose**: Display employee scoreboard and voting interface

**Parameters**: None

**Response**: HTML page with:
- Employee rankings and scores
- Voting interface (if active)
- Current pot information
- Recent voting results

**Example**:
```bash
curl http://localhost:7409/
```

#### `GET /data` - JSON Scoreboard Data
**Purpose**: Get scoreboard data in JSON format

**Parameters**:
- `week` (optional): Specific week number for results

**Response**:
```json
{
  "scoreboard": [
    {
      "name": "John Doe",
      "role": "Driver", 
      "score": 75,
      "payout": 150.00
    }
  ],
  "voting_active": true,
  "total_pot": 2500.00
}
```

**Example**:
```bash
curl http://localhost:7409/data?week=5
```

### System Information

#### `GET /cache-stats` - Cache Performance Statistics
**Purpose**: Get real-time caching performance metrics

**Authentication**: None (public monitoring)

**Response**:
```json
{
  "hit_ratio": 0.99,
  "total_requests": 10847,
  "cache_hits": 10736,
  "memory_usage": "15.2MB",
  "performance_grade": "A+"
}
```

#### `GET /voting_status` - Current Voting Status
**Purpose**: Check if voting session is active

**Response**:
```json
{
  "voting_active": true,
  "session_id": 123,
  "participants_count": 15
}
```

---

## Employee Portal Endpoints

### Portal Access

#### `GET /employee_portal` - Employee Portal Login Page
**Purpose**: Display employee login interface

#### `POST /employee_portal` - Employee Portal Authentication
**Purpose**: Authenticate employee with PIN

**Parameters**:
- `employee_id`: Employee identifier
- `pin`: 4-digit PIN
- `csrf_token`: CSRF protection token

**Response**: Redirects to portal dashboard or shows error

### Employee Operations

#### `POST /employee/change_pin` - Change Employee PIN
**Authentication**: Employee session required

**Parameters**:
- `current_pin`: Current PIN
- `new_pin`: New PIN (4 digits)
- `confirm_pin`: PIN confirmation
- `csrf_token`: CSRF protection token

#### `POST /employee/logout` - Employee Logout
**Purpose**: End employee session

**Parameters**:
- `csrf_token`: CSRF protection token

---

## Administrative Endpoints

### Employee Management

#### `POST /admin/add` - Add New Employee
**Authentication**: Admin required

**Parameters**:
```json
{
  "employee_id": "EMP001",
  "name": "John Doe", 
  "initials": "JD",
  "role": "Driver",
  "score": 50,
  "csrf_token": "..."
}
```

#### `POST /admin/edit_employee` - Edit Employee Details
**Authentication**: Admin required

**Parameters**:
- `employee_id`: Employee to edit
- `name`: New name
- `initials`: New initials  
- `role`: New role
- `csrf_token`: CSRF protection token

#### `POST /admin/retire_employee` - Retire Employee
**Authentication**: Admin required

**Parameters**:
- `employee_id`: Employee to retire
- `csrf_token`: CSRF protection token

#### `POST /admin/reactivate_employee` - Reactivate Employee
**Authentication**: Admin required

**Parameters**:
- `employee_id`: Employee to reactivate
- `csrf_token`: CSRF protection token

#### `POST /admin/delete_employee` - Delete Employee
**Authentication**: Admin required

**Parameters**:
- `employee_id`: Employee to delete permanently
- `csrf_token`: CSRF protection token

### Points Management

#### `POST /admin/adjust_points` - Adjust Employee Points
**Authentication**: Admin required

**Parameters**:
```json
{
  "employee_id": "EMP001",
  "points": 10,
  "reason": "Excellent customer service",
  "notes": "Customer complaint resolution",
  "csrf_token": "..."
}
```

#### `POST /admin/quick_adjust_points` - Quick Points Adjustment
**Authentication**: Admin required

**Parameters**:
- `employee_id`: Employee identifier
- `points`: Point adjustment (+/-)
- `reason`: Reason for adjustment
- `password`: Admin password verification
- `csrf_token`: CSRF protection token

#### `GET /quick_adjust` - Quick Adjust Interface
**Authentication**: Admin required

**Response**: HTML form for quick point adjustments

### Rules Management

#### `POST /admin/add_rule` - Add Point Rule
**Authentication**: Admin required

**Parameters**:
- `description`: Rule description
- `points`: Point value
- `details`: Additional details
- `csrf_token`: CSRF protection token

#### `POST /admin/edit_rule` - Edit Existing Rule
**Authentication**: Admin required

**Parameters**:
- `rule_id`: Rule to edit
- `description`: New description
- `points`: New point value
- `details`: New details
- `csrf_token`: CSRF protection token

#### `POST /admin/remove_rule` - Remove Rule
**Authentication**: Admin required

**Parameters**:
- `rule_id`: Rule to remove
- `csrf_token`: CSRF protection token

#### `POST /admin/reorder_rules` - Reorder Rule Display
**Authentication**: Admin required

**Parameters**:
- `rule_order`: JSON array of rule IDs in new order
- `csrf_token`: CSRF protection token

---

## Voting System Endpoints

### Voting Management

#### `POST /start_voting` - Start Voting Session
**Authentication**: Admin required

**Parameters**:
- `vote_code`: Session validation code
- `csrf_token`: CSRF protection token

#### `POST /close_voting` - Close Voting Session
**Authentication**: Admin required

**Parameters**:
- `csrf_token`: CSRF protection token

#### `POST /pause_voting` - Pause Voting Session
**Authentication**: Admin required

**Parameters**:
- `csrf_token`: CSRF protection token

#### `POST /resume_voting` - Resume Voting Session
**Authentication**: Admin required

**Parameters**:
- `csrf_token`: CSRF protection token

#### `POST /finalize_voting` - Finalize Voting Results
**Authentication**: Admin required

**Purpose**: Apply voting results and award points

**Parameters**:
- `csrf_token`: CSRF protection token

### Voting Operations

#### `POST /vote` - Cast Vote
**Authentication**: Public (initials-based)

**Parameters**:
```json
{
  "voter_initials": "JD",
  "votes": [
    {"employee_id": "EMP001", "vote": 1},
    {"employee_id": "EMP002", "vote": -1}
  ],
  "vote_code": "session_code",
  "csrf_token": "..."
}
```

#### `POST /check_vote` - Check Voting Eligibility
**Authentication**: Public

**Parameters**:
- `initials`: Voter initials
- `vote_code`: Session validation code
- `csrf_token`: CSRF protection token

**Response**:
```json
{
  "can_vote": true,
  "message": "You can participate in voting"
}
```

#### `GET /voting_results_popup` - Get Voting Results
**Purpose**: Display voting results in popup format

**Parameters**:
- `week` (optional): Specific week number

**Response**: HTML popup with voting results

---

## Data Export Endpoints

### Export Operations

#### `GET /export_payout` - Export Payout Data
**Authentication**: Admin required

**Purpose**: Download payout calculations as CSV

**Parameters**:
- `month` (optional): Specific month (YYYY-MM format)

**Response**: CSV file download

#### `GET /admin/export_data/<format>` - Export System Data
**Authentication**: Admin required

**Parameters**:
- `format`: Export format (csv, json)
- `table` (query param): Specific table to export
- `month` (query param): Date filter

**Response**: File download in specified format

#### `GET /admin/export_csv/<table_name>` - Export Table Data
**Authentication**: Admin required

**Purpose**: Export specific database table as CSV

**Example**:
```bash
curl -H "Cookie: session=..." \
  http://localhost:7409/admin/export_csv/employees
```

#### `GET /history_chart` - History Chart Data
**Authentication**: Public

**Purpose**: Generate historical performance chart

**Parameters**:
- `employee_id` (optional): Specific employee
- `days` (optional): Number of days back

**Response**: PNG image or JSON chart data

---

## Mini-Game Endpoints

### Game Management

#### `POST /admin/award_game` - Award Game Token
**Authentication**: Admin required

**Parameters**:
- `employee_id`: Employee to receive game
- `game_type`: Type of game (slot, scratch, roulette)
- `quantity`: Number of games to award
- `csrf_token`: CSRF protection token

#### `GET /admin/game_details/<int:game_id>` - Get Game Details
**Authentication**: Admin required

**Purpose**: Get detailed information about specific game

**Response**:
```json
{
  "game_id": 123,
  "employee_name": "John Doe",
  "game_type": "slot",
  "status": "played",
  "outcome": "win",
  "prize_amount": 25
}
```

### Game Playing

#### `POST /play_game/<int:game_id>` - Play Mini-Game
**Authentication**: Employee session required

**Purpose**: Play an awarded mini-game

**Parameters**:
- `game_id`: Game instance ID
- `csrf_token`: CSRF protection token

**Response**:
```json
{
  "result": "win",
  "prize_type": "points",
  "prize_amount": 25,
  "prize_description": "25 Bonus Points",
  "audio": "jackpot-horn"
}
```

#### `GET /api/game-config` - Game Configuration
**Authentication**: Employee session required

**Purpose**: Get game configuration and odds

**Response**:
```json
{
  "slot_machine": {
    "reels": 5,
    "symbols": ["🍒", "🍋", "🍊", "🍇", "⭐"],
    "win_combinations": {...}
  },
  "prizes": {
    "points": [5, 10, 25, 50],
    "special": ["Gift Card", "Extra Break"]
  }
}
```

### Game Analytics

#### `GET /admin/game_odds` - Game Odds Management
**Authentication**: Admin required

**Purpose**: View and edit game probability settings

#### `POST /admin/update_game_odds` - Update Game Odds
**Authentication**: Admin required

**Parameters**:
- `game_type`: Game to update
- `win_probability`: Base win chance (0-1)
- `jackpot_probability`: Jackpot chance (0-1)
- `csrf_token`: CSRF protection token

#### `GET /admin/payout_analytics` - Payout Analytics
**Authentication**: Admin required

**Purpose**: View game payout statistics and trends

**Response**: HTML dashboard with charts and analytics

---

## System Management Endpoints

### Administrative Interface

#### `GET /admin` - Admin Dashboard
**Authentication**: Admin required

**Response**: Main administrative interface

#### `POST /admin/logout` - Admin Logout
**Authentication**: Admin required

**Parameters**:
- `csrf_token`: CSRF protection token

### System Settings

#### `GET /admin/settings` - Settings Management
**Authentication**: Master Admin required

**Response**: System settings interface

#### `POST /admin/settings` - Update Settings
**Authentication**: Master Admin required

**Parameters**: Various setting key-value pairs
- `setting_key`: Setting value
- `csrf_token`: CSRF protection token

### System Control

#### `POST /admin/restart_service` - Restart Application
**Authentication**: Master Admin required

**Parameters**:
- `csrf_token`: CSRF protection token

#### `POST /admin/reboot_pi` - Reboot System
**Authentication**: Master Admin required

**Parameters**:
- `csrf_token`: CSRF protection token

#### `GET /admin/connection_pool_stats` - Connection Pool Statistics
**Authentication**: Admin required

**Response**:
```json
{
  "pool_size": 10,
  "active_connections": 8,
  "hit_ratio": 1.0,
  "health_score": 100,
  "recommendations": []
}
```

### Data Management

#### `POST /admin/import_database_dump` - Import Database
**Authentication**: Master Admin required

**Parameters**:
- `backup_file`: Database backup file
- `csrf_token`: CSRF protection token

#### `POST /admin/import_csv` - Import CSV Data
**Authentication**: Admin required

**Parameters**:
- `csv_file`: CSV file to import
- `table_name`: Target table
- `csrf_token`: CSRF protection token

---

## Error Handling

### Standard Error Responses

#### HTTP Status Codes
- `200`: Success
- `400`: Bad Request (validation error)
- `401`: Unauthorized (authentication required)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found (resource doesn't exist)
- `500`: Internal Server Error

#### Error Response Format
```json
{
  "status": "error",
  "error_code": "VALIDATION_ERROR",
  "message": "Invalid input provided",
  "details": {
    "field": "employee_id",
    "issue": "Employee not found"
  },
  "timestamp": "2025-08-28T10:15:23Z"
}
```

### Common Error Scenarios

**Authentication Errors:**
```json
{
  "status": "error",
  "error_code": "AUTH_REQUIRED",
  "message": "Admin authentication required",
  "redirect": "/admin_login"
}
```

**Validation Errors:**
```json
{
  "status": "error", 
  "error_code": "INVALID_INPUT",
  "message": "Points must be between -100 and 100",
  "field": "points"
}
```

**CSRF Errors:**
```json
{
  "status": "error",
  "error_code": "CSRF_ERROR", 
  "message": "CSRF token validation failed",
  "action": "refresh_page"
}
```

---

## Rate Limiting

### Connection Limits
- **Concurrent Connections**: 50 per IP
- **Request Rate**: 100 requests/minute per IP
- **Burst Limit**: 10 requests/second

### Game Play Limits  
- **Games per Employee**: No more than 10 unplayed games
- **Play Rate**: 1 game per 5 seconds per employee
- **Session Limits**: 50 game plays per session

---

## API Examples

### Complete Workflow Examples

#### 1. Admin Adding Employee and Awarding Points

```bash
# 1. Login as admin
curl -c cookies.txt -X POST http://localhost:7409/admin_login \
  -d "username=admin1&password=Broadway8101&csrf_token=..."

# 2. Add new employee
curl -b cookies.txt -X POST http://localhost:7409/admin/add \
  -d "employee_id=EMP123&name=Jane+Smith&initials=JS&role=Driver&score=50&csrf_token=..."

# 3. Adjust employee points
curl -b cookies.txt -X POST http://localhost:7409/admin/adjust_points \
  -d "employee_id=EMP123&points=15&reason=Excellent+customer+service&csrf_token=..."

# 4. Award mini-game
curl -b cookies.txt -X POST http://localhost:7409/admin/award_game \
  -d "employee_id=EMP123&game_type=slot&quantity=1&csrf_token=..."
```

#### 2. Employee Playing Game

```bash
# 1. Login to employee portal
curl -c emp_cookies.txt -X POST http://localhost:7409/employee_portal \
  -d "employee_id=EMP123&pin=1234&csrf_token=..."

# 2. Play awarded game (game_id from previous award)
curl -b emp_cookies.txt -X POST http://localhost:7409/play_game/456 \
  -d "csrf_token=..."

# Response:
# {
#   "result": "win",
#   "prize_type": "points", 
#   "prize_amount": 25,
#   "audio": "jackpot-horn"
# }
```

#### 3. Voting Workflow

```bash
# 1. Admin starts voting session
curl -b admin_cookies.txt -X POST http://localhost:7409/start_voting \
  -d "vote_code=VOTE2025&csrf_token=..."

# 2. Employee checks voting eligibility  
curl -X POST http://localhost:7409/check_vote \
  -d "initials=JS&vote_code=VOTE2025&csrf_token=..."

# 3. Employee casts votes
curl -X POST http://localhost:7409/vote \
  -d "voter_initials=JS&votes=[{\"employee_id\":\"EMP001\",\"vote\":1}]&vote_code=VOTE2025&csrf_token=..."

# 4. Admin closes voting and finalizes results
curl -b admin_cookies.txt -X POST http://localhost:7409/close_voting \
  -d "csrf_token=..."
  
curl -b admin_cookies.txt -X POST http://localhost:7409/finalize_voting \
  -d "csrf_token=..."
```

### Data Retrieval Examples

#### Get Scoreboard Data with Caching
```bash
# Get JSON scoreboard data
curl http://localhost:7409/data

# Get specific week results
curl http://localhost:7409/data?week=5

# Check cache performance
curl http://localhost:7409/cache-stats
```

#### Export Data for Analysis
```bash
# Export all employee data
curl -b admin_cookies.txt \
  http://localhost:7409/admin/export_csv/employees > employees.csv

# Export monthly payout data
curl -b admin_cookies.txt \
  "http://localhost:7409/export_payout?month=2025-08" > payout_august.csv

# Export game history
curl -b admin_cookies.txt \
  http://localhost:7409/admin/export_csv/game_history > game_history.csv
```

### System Monitoring Examples

#### Performance Monitoring
```bash
# Cache performance stats
curl http://localhost:7409/cache-stats | jq .

# Connection pool health
curl -b admin_cookies.txt \
  http://localhost:7409/admin/connection_pool_stats | jq .

# Voting system status
curl http://localhost:7409/voting_status | jq .
```

### JavaScript/AJAX Examples

#### Frontend Integration
```javascript
// Get scoreboard data with AJAX
async function updateScoreboard() {
  try {
    const response = await fetch('/data');
    const data = await response.json();
    
    // Update UI with scoreboard data
    updateScoreboardDisplay(data.scoreboard);
    updateVotingStatus(data.voting_active);
  } catch (error) {
    console.error('Failed to load scoreboard:', error);
  }
}

// Play mini-game via AJAX
async function playGame(gameId) {
  const csrf_token = document.querySelector('[name=csrf_token]').value;
  
  try {
    const response = await fetch(`/play_game/${gameId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: `csrf_token=${csrf_token}`
    });
    
    const result = await response.json();
    
    if (result.result === 'win') {
      showWinAnimation(result);
      playAudio(result.audio);
    }
  } catch (error) {
    console.error('Game play failed:', error);
  }
}

// Submit vote via AJAX
async function submitVote(votes) {
  const csrf_token = document.querySelector('[name=csrf_token]').value;
  const vote_code = document.querySelector('[name=vote_code]').value;
  const voter_initials = document.querySelector('[name=initials]').value;
  
  try {
    const response = await fetch('/vote', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: `voter_initials=${voter_initials}&votes=${JSON.stringify(votes)}&vote_code=${vote_code}&csrf_token=${csrf_token}`
    });
    
    const result = await response.json();
    
    if (result.status === 'success') {
      showSuccessMessage('Vote submitted successfully!');
      disableVotingForm();
    }
  } catch (error) {
    console.error('Vote submission failed:', error);
  }
}
```

---

## API Security Best Practices

### Authentication
- Always include CSRF tokens in POST requests
- Use secure session cookies
- Implement proper logout functionality
- Validate user permissions on every request

### Input Validation
- Sanitize all user input
- Validate data types and ranges
- Use parameterized queries for database operations
- Escape output appropriately

### Error Handling
- Don't expose sensitive information in error messages
- Log security-related events
- Implement rate limiting
- Use appropriate HTTP status codes

### Data Protection
- Hash passwords securely
- Protect sensitive endpoints with authentication
- Validate file uploads
- Implement proper access controls

This comprehensive API documentation provides all the information needed to integrate with and extend the A1 Rent-It Employee Incentive System effectively and securely.