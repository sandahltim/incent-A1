# services/auth.py
# Authentication service

import logging
from flask import session, redirect, url_for, flash
from functools import wraps


def admin_required(f):
    """Decorator to require admin authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin' not in session:
            flash('Admin access required.', 'error')
            return redirect(url_for('admin'))
        return f(*args, **kwargs)
    return decorated_function


def employee_required(f):
    """Decorator to require employee authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'employee_id' not in session:
            flash('Employee access required.', 'error')
            return redirect(url_for('employee_portal'))
        return f(*args, **kwargs)
    return decorated_function


def check_admin_session():
    """Check if current session has admin privileges."""
    return 'admin' in session


def check_employee_session():
    """Check if current session has employee authentication."""
    return 'employee_id' in session


def clear_admin_session():
    """Clear admin session data."""
    session.pop('admin', None)
    logging.info("Admin logged out")


def clear_employee_session():
    """Clear employee session data."""
    employee_id = session.pop('employee_id', None)
    if employee_id:
        logging.info(f"Employee {employee_id} logged out")


def set_admin_session():
    """Set admin session."""
    session['admin'] = True
    logging.info("Admin logged in")


def set_employee_session(employee_id):
    """Set employee session."""
    session['employee_id'] = employee_id
    logging.info(f"Employee {employee_id} logged in")