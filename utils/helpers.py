# utils/helpers.py
# Helper functions and utilities

import json
from datetime import datetime
import time
import logging


def from_json(value):
    """Parse JSON value with error handling."""
    try:
        return json.loads(value) if value else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def get_score_class(score, index, threshold):
    """Determine CSS class for score based on position and threshold."""
    if index == 0:
        return "score-top"
    elif score >= threshold:
        return "score-mid"
    else:
        return "score-bottom"


def get_role_key_map(roles):
    """Create a mapping from role keys to role names."""
    return {role.get('role_key', ''): role.get('role_name', '') for role in roles}


def make_session_permanent():
    """Make the current session permanent."""
    from flask import session
    session.permanent = True