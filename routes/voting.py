# routes/voting.py
# Voting system routes

import logging
import traceback
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.security import check_password_hash
from flask_wtf.csrf import CSRFError
from incentive_service import (
    DatabaseConnection, start_voting_session, close_voting_session, 
    pause_voting_session, resume_voting_session, finalize_voting_session,
    is_voting_active, cast_votes, get_voting_results
)
from forms import StartVotingForm, CloseVotingForm, PauseVotingForm, VoteForm
from services.auth import admin_required
from services.cache import data_cache

try:
    from caching_service import get_cache_manager, get_invalidation_manager
    from config import Config
    CACHING_AVAILABLE = True
except ImportError:
    CACHING_AVAILABLE = False
    Config = None

voting_bp = Blueprint('voting', __name__, url_prefix='/voting')


@voting_bp.route("/start", methods=["GET", "POST"])
@admin_required
def start_voting():
    """Start a new voting session."""
    form = StartVotingForm()
    if request.method == "POST":
        try:
            logging.debug("Start voting form data received: %s", {k: '****' if k == 'password' else v for k, v in request.form.items()})
            if not form.validate_on_submit():
                logging.error("Start voting form validation failed: %s", form.errors)
                return jsonify({"success": False, "message": "Invalid form data: " + str(form.errors)}), 400
            
            username = form.username.data
            password = form.password.data
            
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
                if admin and check_password_hash(admin["password"], password):
                    success, message = start_voting_session(conn, session["admin_id"])
                    if not success:
                        logging.warning("start_voting_session failed: %s", message)
                        return jsonify({"success": False, "message": message}), 400
                    
                    # Invalidate caches
                    if CACHING_AVAILABLE and Config and Config.CACHE_ENABLED:
                        get_invalidation_manager().invalidate_voting()
                    
                    # Legacy cache invalidation
                    data_cache.clear()
                    
                    logging.debug("Voting session started by admin_id: %s", session["admin_id"])
                    return jsonify({"success": True, "message": message})
                
                logging.error("Invalid credentials for username: %s", username)
                return jsonify({"success": False, "message": "Invalid credentials"}), 403
                
        except CSRFError as e:
            logging.error(f"CSRF error in start voting: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "CSRF validation failed. Please try again."}), 400
        except Exception as e:
            logging.error(f"Error in start voting: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    
    return render_template("start_voting.html", form=form, is_master=session.get("admin_id") == "master", import_time=int(time.time()))


@voting_bp.route("/close", methods=["POST"])
@admin_required
def close_voting():
    """Close the current voting session."""
    form = CloseVotingForm(request.form)
    logging.debug("Raw close voting form data: %s", {k: '****' if k == 'password' else v for k, v in request.form.items()})
    
    if not form.validate_on_submit():
        logging.error("Close voting form validation failed: %s, form data: %s", form.errors, {k: '****' if k == 'password' else v for k, v in request.form.items()})
        # Attempt to recover password from malformed fields
        for key in request.form.keys():
            if key != 'csrf_token' and key != 'password' and 'password' in key.lower():
                logging.warning("Unexpected form field detected: %s, attempting recovery", key)
                form.password.data = request.form[key]
                if form.validate_on_submit():
                    logging.info("Recovered password validation successful")
                    break
        
        if not form.validate_on_submit():
            flash("Invalid form data: " + str(form.errors), "danger")
            return jsonify({"success": False, "message": "Invalid form data: " + str(form.errors)}), 400
    
    try:
        password = form.password.data
        with DatabaseConnection() as conn:
            admin = conn.execute("SELECT * FROM admins WHERE admin_id = ?", (session["admin_id"],)).fetchone()
            if not admin or not check_password_hash(admin["password"], password):
                logging.error("Invalid admin password for close voting: admin_id=%s", session["admin_id"])
                flash("Invalid admin password", "danger")
                return jsonify({"success": False, "message": "Invalid admin password"}), 403
            
            success, message = close_voting_session(conn, session["admin_id"])
            if not success:
                logging.error("Close voting failed: %s", message)
                flash(message, "danger")
                return jsonify({"success": False, "message": message}), 400
            
            conn.commit()
            
            # Clear cache
            data_cache.clear()
            
            logging.debug("Voting session closed by admin_id: %s", session["admin_id"])
            flash("Voting session closed", "success")
            return jsonify({"success": True, "message": "Voting session closed"})
            
    except Exception as e:
        logging.error(f"Error closing voting: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return jsonify({"success": False, "message": "Server error"}), 500


@voting_bp.route("/pause", methods=["POST"])
@admin_required
def pause_voting():
    """Pause the current voting session."""
    form = PauseVotingForm(request.form)
    if not form.validate_on_submit():
        logging.error("Pause voting form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    
    try:
        with DatabaseConnection() as conn:
            success, message = pause_voting_session(conn, session["admin_id"])
            return jsonify({'success': success, 'message': message})
    except Exception as e:
        logging.error(f"Error in pause_voting: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': 'Server error'}), 500


@voting_bp.route("/resume", methods=["POST"])
@admin_required
def resume_voting():
    """Resume the current voting session."""
    form = PauseVotingForm(request.form)
    if not form.validate_on_submit():
        logging.error("Resume voting form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    
    try:
        with DatabaseConnection() as conn:
            success, message = resume_voting_session(conn, session["admin_id"])
            return jsonify({'success': success, 'message': message})
    except Exception as e:
        logging.error(f"Error in resume_voting: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': 'Server error'}), 500


@voting_bp.route("/finalize", methods=["POST"])
@admin_required
def finalize_voting():
    """Finalize the current voting session."""
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    
    try:
        with DatabaseConnection() as conn:
            success, message = finalize_voting_session(conn, session["admin_id"])
            if success:
                flash(message, "success")
                # Clear cache after finalizing
                data_cache.clear()
                return jsonify({'success': True, 'message': message})
            else:
                flash(message, "warning")
                return jsonify({'success': False, 'message': message}), 400
    except Exception as e:
        logging.error(f"Error in finalize_voting: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return jsonify({'success': False, 'message': 'Server error'}), 500


@voting_bp.route("/vote", methods=["POST"])
def vote():
    """Cast votes in the current session."""
    form = VoteForm()
    if not form.validate_on_submit():
        return jsonify({'success': False, 'error': 'Invalid form data: ' + str(form.errors)}), 400
    
    try:
        votes = []
        for field in form:
            if field.name.startswith('employee_') and field.data:
                employee_id = field.name.replace('employee_', '')
                reason = getattr(form, f'reason_{employee_id}', None)
                reason_text = reason.data if reason else 'No reason specified'
                votes.append((employee_id, field.data, reason_text))
        
        if not votes:
            return jsonify({'success': False, 'error': 'No votes submitted'}), 400
        
        with DatabaseConnection() as conn:
            success, message = cast_votes(conn, votes)
            if success:
                # Clear cache after voting
                data_cache.clear()
                return jsonify({'success': True, 'message': message})
            else:
                return jsonify({'success': False, 'error': message}), 400
                
    except Exception as e:
        logging.error(f"Error in vote: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': 'Server error'}), 500


@voting_bp.route("/check", methods=["POST"])
def check_vote():
    """Check if user has already voted."""
    try:
        employee_id = request.form.get('employee_id')
        if not employee_id:
            return jsonify({'error': 'Employee ID required'}), 400
        
        with DatabaseConnection() as conn:
            # Check if employee has voted in current session
            has_voted = conn.execute("""
                SELECT COUNT(*) as count FROM votes v
                JOIN voting_sessions vs ON v.session_id = vs.id
                WHERE v.voter_id = ? AND vs.status IN ('active', 'paused')
            """, (employee_id,)).fetchone()['count'] > 0
            
            return jsonify({'has_voted': has_voted})
            
    except Exception as e:
        logging.error(f"Error in check_vote: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Server error'}), 500


@voting_bp.route("/status", methods=["GET"])
def voting_status():
    """Get current voting session status."""
    try:
        with DatabaseConnection() as conn:
            voting_active = is_voting_active(conn)
            
            # Get session info if active
            session_info = None
            if voting_active:
                session_info = conn.execute("""
                    SELECT id, status, created_at, finalized_at
                    FROM voting_sessions 
                    WHERE status IN ('active', 'paused')
                    ORDER BY created_at DESC 
                    LIMIT 1
                """).fetchone()
                
                if session_info:
                    session_info = dict(session_info)
            
            return jsonify({
                'voting_active': voting_active,
                'session_info': session_info
            })
            
    except Exception as e:
        logging.error(f"Error in voting_status: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Server error'}), 500


@voting_bp.route("/results", methods=["GET"])
def voting_results_popup():
    """Get voting results for display."""
    try:
        week_number = request.args.get("week", type=int)
        
        with DatabaseConnection() as conn:
            voting_results = get_voting_results(conn, is_admin=session.get("admin_id") is not None, week_number=week_number)
            
        return jsonify({
            'results': voting_results,
            'week': week_number
        })
        
    except Exception as e:
        logging.error(f"Error in voting_results_popup: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Server error'}), 500