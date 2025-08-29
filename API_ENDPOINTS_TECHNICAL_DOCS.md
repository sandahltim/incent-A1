# API Endpoints Technical Documentation

**Version**: 1.0.0  
**Date**: August 29, 2025  
**Target Audience**: Developers, System Administrators, Technical Staff  

## Table of Contents

1. [API Overview](#api-overview)
2. [Authentication and CSRF Protection](#authentication-and-csrf-protection)
3. [Dual Game System Endpoints](#dual-game-system-endpoints)
4. [Token Economy Endpoints](#token-economy-endpoints)
5. [Legacy Game Endpoints](#legacy-game-endpoints)
6. [Admin Endpoints](#admin-endpoints)
7. [Analytics and Monitoring Endpoints](#analytics-and-monitoring-endpoints)
8. [Error Handling](#error-handling)
9. [Rate Limiting](#rate-limiting)
10. [API Testing](#api-testing)

## API Overview

The system provides REST API endpoints for both the dual game system and legacy functionality. All endpoints require CSRF protection and follow consistent request/response patterns.

### Base Configuration

```
Base URL: http://localhost:7410 (changed from 7409)
Protocol: HTTP (HTTPS in production)
Content-Type: application/json or multipart/form-data
CSRF Protection: Required for all POST/PUT/DELETE requests
```

### Common Response Format

```json
{
    "success": true|false,
    "message": "Human readable message",
    "data": {...},  // Optional response data
    "error": "error_type",  // Only on errors
    "timestamp": "2025-08-29T12:00:00Z"
}
```

## Authentication and CSRF Protection

### CSRF Token Retrieval

All endpoints require a valid CSRF token for POST/PUT/DELETE operations.

#### Get CSRF Token from HTML Meta Tag

```html
<meta name="csrf-token" content="{{ csrf_token() }}">
```

```javascript
function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
}
```

### Request Patterns

#### FormData Pattern (Recommended)

```javascript
const formData = new FormData();
formData.append('csrf_token', getCSRFToken());
formData.append('parameter', 'value');

fetch('/api/endpoint', {
    method: 'POST',
    body: formData
});
```

#### JSON Pattern (Manual Validation)

```javascript
fetch('/api/endpoint', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken()
    },
    body: JSON.stringify({parameter: 'value'})
});
```

## Dual Game System Endpoints

### Category A: Guaranteed Reward Games

#### Play Category A Game

**Endpoint**: `POST /api/games/category-a/play/<game_id>`

**Description**: Play a guaranteed win reward game

**CSRF Protection**: Required (manual validation)

**Request**:
```javascript
const formData = new FormData();
formData.append('csrf_token', getCSRFToken());

fetch('/api/games/category-a/play/123', {
    method: 'POST',
    body: formData
});
```

**Response Success (200)**:
```json
{
    "success": true,
    "message": "Congratulations! You won: $50 Cash Prize",
    "data": {
        "prize_type": "jackpot_cash",
        "amount": 50,
        "description": "$50 Cash Prize",
        "game_id": 123,
        "remaining_limits": {
            "jackpot_cash": {"used": 1, "limit": 2},
            "pto_hours": {"used": 0, "limit": 4},
            "major_points": {"used": 2, "limit": 8}
        }
    }
}
```

**Response Error (400)**:
```json
{
    "success": false,
    "error": "csrf_error",
    "message": "CSRF validation failed. Please refresh and try again."
}
```

**Response Error (404)**:
```json
{
    "success": false,
    "error": "game_not_found", 
    "message": "Invalid or already played reward game"
}
```

#### Get Available Category A Games

**Endpoint**: `GET /api/games/category-a/available/<employee_id>`

**Description**: Get list of available guaranteed reward games for employee

**CSRF Protection**: Not required (GET request)

**Response Success (200)**:
```json
{
    "success": true,
    "data": {
        "available_games": [
            {
                "game_id": 123,
                "game_type": "reward_selection",
                "awarded_date": "2025-08-29T10:00:00Z",
                "tier_level": "silver",
                "guaranteed_win": true
            }
        ],
        "employee_tier": "silver",
        "monthly_limits": {
            "jackpot_cash": {"used": 1, "limit": 2, "remaining": 1},
            "pto_hours": {"used": 0, "limit": 4, "remaining": 4},
            "major_points": {"used": 2, "limit": 8, "remaining": 6}
        }
    }
}
```

### Category B: Token-Based Gambling Games

#### Play Category B Game

**Endpoint**: `POST /api/games/category-b/play`

**Description**: Play a token-based gambling game

**CSRF Protection**: Required (manual validation)

**Request**:
```javascript
const formData = new FormData();
formData.append('csrf_token', getCSRFToken());
formData.append('game_type', 'slots');
formData.append('token_cost', '5');

fetch('/api/games/category-b/play', {
    method: 'POST',
    body: formData
});
```

**Response Success - Win (200)**:
```json
{
    "success": true,
    "message": "Congratulations! You won: 500 Bonus Points",
    "data": {
        "outcome": "win",
        "prize_type": "major_points_500",
        "amount": 500,
        "description": "500 Bonus Points",
        "tokens_spent": 5,
        "remaining_tokens": 45,
        "game_id": 456
    }
}
```

**Response Success - Loss (200)**:
```json
{
    "success": true,
    "message": "Better luck next time!",
    "data": {
        "outcome": "loss",
        "tokens_spent": 5,
        "remaining_tokens": 45,
        "game_id": 456
    }
}
```

**Response Error - Insufficient Tokens (400)**:
```json
{
    "success": false,
    "error": "insufficient_tokens",
    "message": "Insufficient tokens (need 5, have 2)"
}
```

#### Get Category B Game Types

**Endpoint**: `GET /api/games/category-b/types`

**Description**: Get available gambling game types and their costs

**Response Success (200)**:
```json
{
    "success": true,
    "data": {
        "game_types": [
            {
                "type": "slots",
                "min_cost": 1,
                "max_cost": 10,
                "base_win_rate": {"bronze": 0.35, "silver": 0.38, "gold": 0.42, "platinum": 0.45}
            },
            {
                "type": "roulette", 
                "min_cost": 2,
                "max_cost": 20,
                "base_win_rate": {"bronze": 0.28, "silver": 0.31, "gold": 0.35, "platinum": 0.38}
            },
            {
                "type": "dice",
                "min_cost": 1,
                "max_cost": 15,
                "base_win_rate": {"bronze": 0.32, "silver": 0.35, "gold": 0.39, "platinum": 0.42}
            }
        ]
    }
}
```

## Token Economy Endpoints

### Get Token Account

**Endpoint**: `GET /api/tokens/account/<employee_id>`

**Description**: Get employee token account information

**Response Success (200)**:
```json
{
    "success": true,
    "data": {
        "employee_id": "E001",
        "token_balance": 50,
        "total_tokens_earned": 200,
        "total_tokens_spent": 150,
        "tier_level": "silver",
        "current_points": 250,
        "exchange_info": {
            "exchange_rate": 8,
            "daily_limit": 100,
            "daily_used": 25,
            "daily_remaining": 75,
            "cooldown_hours": 18,
            "next_exchange_available": "2025-08-30T06:00:00Z"
        }
    }
}
```

### Exchange Points for Tokens

**Endpoint**: `POST /api/tokens/exchange`

**Description**: Exchange employee points for tokens

**CSRF Protection**: Required (manual validation)

**Request**:
```javascript
const formData = new FormData();
formData.append('csrf_token', getCSRFToken());
formData.append('employee_id', 'E001');
formData.append('token_amount', '10');

fetch('/api/tokens/exchange', {
    method: 'POST',
    body: formData
});
```

**Response Success (200)**:
```json
{
    "success": true,
    "message": "Exchanged 80 points for 10 tokens",
    "data": {
        "tokens_received": 10,
        "points_spent": 80,
        "exchange_rate": 8,
        "new_token_balance": 60,
        "new_point_balance": 170,
        "daily_exchanges_remaining": 65,
        "next_exchange_available": "2025-08-30T06:00:00Z"
    }
}
```

**Response Error - Cooldown (429)**:
```json
{
    "success": false,
    "error": "exchange_cooldown",
    "message": "Cooldown active: 12 hours remaining",
    "data": {
        "cooldown_remaining_hours": 12,
        "next_available": "2025-08-30T06:00:00Z"
    }
}
```

**Response Error - Insufficient Points (400)**:
```json
{
    "success": false,
    "error": "insufficient_points",
    "message": "Insufficient points (need 80, have 50)"
}
```

### Get Token Transaction History

**Endpoint**: `GET /api/tokens/history/<employee_id>?limit=50&offset=0`

**Description**: Get token transaction history for employee

**Response Success (200)**:
```json
{
    "success": true,
    "data": {
        "transactions": [
            {
                "id": 123,
                "transaction_type": "purchase",
                "points_amount": -80,
                "token_amount": 10,
                "exchange_rate": 8.0,
                "transaction_date": "2025-08-29T10:00:00Z",
                "admin_notes": "Normal exchange"
            },
            {
                "id": 124,
                "transaction_type": "spend",
                "points_amount": null,
                "token_amount": -5,
                "exchange_rate": null,
                "transaction_date": "2025-08-29T11:00:00Z",
                "game_id": 456,
                "admin_notes": "Category B slots"
            }
        ],
        "total_count": 2,
        "has_more": false
    }
}
```

## Legacy Game Endpoints

### Play Legacy Mini-Game

**Endpoint**: `POST /play_game/<game_id>`

**Description**: Play traditional mini-game (legacy system)

**CSRF Protection**: Required (manual validation)

**Request**:
```javascript
const formData = new FormData();
formData.append('csrf_token', getCSRFToken());

fetch('/play_game/789', {
    method: 'POST',
    body: formData
});
```

**Response Success (200)**:
```json
{
    "success": true,
    "message": "You won 25 points!",
    "data": {
        "prize_type": "points",
        "amount": 25,
        "game_id": 789,
        "outcome": "win"
    }
}
```

### Award Legacy Mini-Game

**Endpoint**: `POST /award_game`

**Description**: Award a legacy mini-game to employee (admin only)

**CSRF Protection**: Required (automatic validation via FlaskForm)

**Request**:
```javascript
const formData = new FormData();
formData.append('csrf_token', getCSRFToken());
formData.append('employee_id', 'E001');
formData.append('game_type', 'slot');

fetch('/award_game', {
    method: 'POST',
    body: formData
});
```

## Admin Endpoints

### Award Category A Game

**Endpoint**: `POST /api/admin/dual-system/award-category-a`

**Description**: Award guaranteed reward game to employees (admin only)

**CSRF Protection**: Required (manual validation)

**Request**:
```javascript
const formData = new FormData();
formData.append('csrf_token', getCSRFToken());
formData.append('employee_ids', JSON.stringify([1, 2, 3]));
formData.append('prize_type', 'points');
formData.append('prize_amount', '10');
formData.append('source_description', 'Monthly performance bonus');

fetch('/api/admin/dual-system/award-category-a', {
    method: 'POST',
    body: formData
});
```

**Response Success (200)**:
```json
{
    "success": true,
    "message": "Awarded guaranteed reward games to 3 employees",
    "data": {
        "employees_awarded": [
            {"employee_id": 1, "name": "John Doe"},
            {"employee_id": 2, "name": "Jane Smith"},
            {"employee_id": 3, "name": "Bob Johnson"}
        ],
        "award_details": {
            "source": "admin_award",
            "source_description": "Monthly performance bonus",
            "admin_id": "admin1"
        }
    }
}
```

### Manage Global Prize Pools

**Endpoint**: `POST /api/admin/global-pools/update`

**Description**: Update global prize pool limits (admin only)

**CSRF Protection**: Required (manual validation)

**Request**:
```javascript
const formData = new FormData();
formData.append('csrf_token', getCSRFToken());
formData.append('prize_type', 'cash_prize_100');
formData.append('daily_limit', '5');
formData.append('weekly_limit', '20');
formData.append('monthly_limit', '60');

fetch('/api/admin/global-pools/update', {
    method: 'POST',
    body: formData
});
```

**Response Success (200)**:
```json
{
    "success": true,
    "message": "Global prize pool updated successfully",
    "data": {
        "prize_type": "cash_prize_100",
        "old_limits": {"daily": 2, "weekly": 8, "monthly": 25},
        "new_limits": {"daily": 5, "weekly": 20, "monthly": 60}
    }
}
```

### Get Admin Analytics

**Endpoint**: `GET /api/admin/analytics/dual-system?period=30`

**Description**: Get comprehensive dual system analytics (admin only)

**Response Success (200)**:
```json
{
    "success": true,
    "data": {
        "period": "30 days",
        "category_a": {
            "total_games": 150,
            "total_wins": 150,
            "total_payout": 12500,
            "avg_prize": 83.33,
            "by_tier": {
                "bronze": {"games": 50, "payout": 2500},
                "silver": {"games": 60, "payout": 4200},
                "gold": {"games": 30, "payout": 4500},
                "platinum": {"games": 10, "payout": 1300}
            }
        },
        "category_b": {
            "total_games": 800,
            "total_wins": 280,
            "win_rate": 0.35,
            "total_tokens_spent": 4000,
            "total_payout": 8500,
            "house_edge": 0.15
        },
        "token_economy": {
            "total_tokens_in_circulation": 2500,
            "total_tokens_earned": 15000,
            "total_tokens_spent": 12500,
            "active_token_users": 45,
            "weekly_exchanges": 120,
            "weekly_tokens_purchased": 800
        }
    }
}
```

## Analytics and Monitoring Endpoints

### Get Dual System Status

**Endpoint**: `GET /api/dual-system/status`

**Description**: Get comprehensive system health status

**Response Success (200)**:
```json
{
    "success": true,
    "data": {
        "system_health": "healthy",
        "database_status": "connected",
        "cache_status": "operational",
        "active_users": 25,
        "global_pools": {
            "cash_prize_100": {"daily_used": 1, "daily_limit": 2, "available": true},
            "major_points_500": {"daily_used": 3, "daily_limit": 3, "available": false}
        },
        "token_economy": {
            "total_circulation": 2500,
            "exchange_rate_health": "stable",
            "recent_activity": "normal"
        },
        "performance_metrics": {
            "avg_response_time": 150,
            "database_pool_utilization": 0.4,
            "cache_hit_rate": 0.85
        }
    }
}
```

### Get Employee Game Summary

**Endpoint**: `GET /api/games/summary/<employee_id>`

**Description**: Get comprehensive game summary for employee

**Response Success (200)**:
```json
{
    "success": true,
    "data": {
        "employee_id": "E001",
        "tier_level": "silver",
        "category_a": {
            "total_games": 5,
            "unused_games": 2,
            "wins": 3,
            "this_month_prizes": {
                "jackpot_cash": 1,
                "pto_hours": 0,
                "major_points": 2
            }
        },
        "category_b": {
            "total_games": 20,
            "wins": 7,
            "win_rate": 0.35,
            "total_tokens_spent": 100,
            "biggest_win": {"amount": 500, "type": "major_points_500"}
        },
        "token_account": {
            "balance": 50,
            "total_earned": 200,
            "total_spent": 150,
            "exchange_available": true
        }
    }
}
```

## Error Handling

### Standard Error Codes

| HTTP Code | Error Type | Description |
|-----------|------------|-------------|
| 400 | `csrf_error` | CSRF validation failed |
| 400 | `validation_error` | Request validation failed |
| 400 | `insufficient_tokens` | Not enough tokens for operation |
| 400 | `insufficient_points` | Not enough points for operation |
| 401 | `authentication_required` | Login required |
| 403 | `permission_denied` | Admin access required |
| 404 | `not_found` | Resource not found |
| 429 | `rate_limit_exceeded` | Too many requests |
| 429 | `exchange_cooldown` | Token exchange in cooldown |
| 500 | `internal_error` | Server error |
| 503 | `service_unavailable` | System temporarily unavailable |

### Error Response Format

```json
{
    "success": false,
    "error": "error_type",
    "message": "Human readable error message",
    "details": {
        "field_errors": {"field_name": ["error message"]},
        "error_code": "SPECIFIC_ERROR_CODE",
        "suggested_action": "refresh_page|retry|contact_admin"
    },
    "timestamp": "2025-08-29T12:00:00Z"
}
```

### Error Handling Examples

```javascript
async function handleAPIResponse(response) {
    const data = await response.json();
    
    if (!response.ok) {
        switch (data.error) {
            case 'csrf_error':
                // Refresh page to get new CSRF token
                if (data.details?.suggested_action === 'refresh_page') {
                    location.reload();
                }
                break;
                
            case 'exchange_cooldown':
                // Show cooldown timer
                showCooldownTimer(data.data.next_available);
                break;
                
            case 'insufficient_tokens':
                // Redirect to token exchange
                showTokenExchangeModal();
                break;
                
            default:
                // Generic error handling
                showErrorMessage(data.message);
        }
        throw new Error(data.message);
    }
    
    return data;
}
```

## Rate Limiting

### Global Rate Limits

- **Category A Games**: 5 games per employee per hour
- **Category B Games**: 20 games per employee per hour  
- **Token Exchange**: Based on tier daily limits
- **API Requests**: 1000 requests per IP per hour

### Rate Limit Headers

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1693315200
X-RateLimit-Type: global|user|endpoint
```

### Rate Limit Response

```json
{
    "success": false,
    "error": "rate_limit_exceeded",
    "message": "Too many requests. Try again in 3600 seconds.",
    "data": {
        "retry_after": 3600,
        "limit_type": "user_games",
        "reset_time": "2025-08-29T13:00:00Z"
    }
}
```

## API Testing

### CSRF Testing Script

The system includes a comprehensive API testing script:

```bash
# Run full API validation
python csrf_system_validation.py

# Run specific endpoint tests
python -m pytest tests/test_api.py::test_dual_game_endpoints
```

### Manual Testing with curl

#### Test CSRF Protection

```bash
# Should fail with 400 CSRF error
curl -X POST http://localhost:7410/api/games/category-a/play/1 \
     -H "Content-Type: application/json" \
     -d '{"test": "data"}'

# Should succeed with valid token
curl -X POST http://localhost:7410/api/games/category-a/play/1 \
     -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
     -F "csrf_token=YOUR_CSRF_TOKEN"
```

#### Test Token Exchange

```bash
# Get CSRF token first
CSRF_TOKEN=$(curl -s http://localhost:7410/ | grep -o 'csrf-token" content="[^"]*' | cut -d'"' -f3)

# Exchange tokens
curl -X POST http://localhost:7410/api/tokens/exchange \
     -F "csrf_token=$CSRF_TOKEN" \
     -F "employee_id=E001" \
     -F "token_amount=10"
```

### Testing Environment Setup

```python
# test_config.py
class TestConfig:
    TESTING = True
    WTF_CSRF_ENABLED = True  # Keep CSRF enabled for testing
    SECRET_KEY = "test_secret_key"
    INCENTIVE_DB_FILE = ":memory:"

# pytest fixtures
@pytest.fixture
def client():
    app.config.from_object('test_config.TestConfig')
    with app.test_client() as client:
        with app.app_context():
            init_test_database()
            yield client
```

---

## API Versioning

### Current Version: v1

All endpoints are currently version 1. Future versions will be prefixed:

```
/api/v1/games/category-a/play/<game_id>  # Explicit versioning
/api/v2/games/category-a/play/<game_id>  # Future version
```

### Version Headers

```http
API-Version: 1.0.0
Accept-Version: 1.x
```

## Related Documentation

- [CSRF Security Implementation](CSRF_SECURITY_TECHNICAL_DOCS.md)
- [Dual Game System Technical Architecture](DUAL_GAME_SYSTEM_TECHNICAL_DOCS.md)
- [Database Schema Documentation](DATABASE_SCHEMA_TECHNICAL_DOCS.md)
- [Testing and Validation Procedures](TESTING_VALIDATION_TECHNICAL_DOCS.md)

---

**Last Updated**: August 29, 2025  
**Next Review**: September 29, 2025  
**Maintained By**: Development Team