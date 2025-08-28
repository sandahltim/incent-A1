
# app.py
# Version: 1.2.114
# Note: Added configurable scoreboard timing settings. Compatible with incentive_service.py (1.2.31), forms.py (1.2.22), settings.html (1.3.1), incentive.html (1.3.2), script.js (1.2.97), init_db.py (1.2.5).

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file, send_from_directory, flash
from werkzeug.security import check_password_hash, generate_password_hash
from flask_wtf.csrf import CSRFProtect, CSRFError
from incentive_service import DatabaseConnection, get_scoreboard, start_voting_session, is_voting_active, cast_votes, add_employee, reset_scores, get_history, adjust_points, get_rules, add_rule, edit_rule, remove_rule, get_pot_info, update_pot_info, close_voting_session, pause_voting_session, resume_voting_session, finalize_voting_session, get_voting_results, master_reset_all, get_roles, add_role, edit_role, remove_role, edit_employee, reorder_rules, retire_employee, reactivate_employee, delete_employee, set_point_decay, get_point_decay, deduct_points_daily, get_latest_voting_results, add_feedback, get_unread_feedback_count, get_feedback, mark_feedback_read, delete_feedback, get_settings, set_settings, get_recent_admin_adjustments, award_mini_game, play_mini_game, verify_pin
import logging
from logging_config import setup_logging

# Import caching services
try:
    from services.cache import (
        get_cache_manager, 
        get_invalidation_manager, 
        get_cache_config,
        get_cache_warmer,
        get_metrics_collector
    )
    CACHING_AVAILABLE = True
    logging.info("Caching system initialized successfully")
except ImportError as e:
    logging.warning(f"Caching system not available: {e}")
    CACHING_AVAILABLE = False
from config import Config
from forms import VoteForm, AdminLoginForm, StartVotingForm, AddEmployeeForm, AdjustPointsForm, AddRuleForm, EditRuleForm, RemoveRuleForm, EditEmployeeForm, RetireEmployeeForm, ReactivateEmployeeForm, DeleteEmployeeForm, UpdatePotForm, UpdatePriorYearSalesForm, SetPointDecayForm, UpdateAdminForm, AddRoleForm, EditRoleForm, RemoveRoleForm, MasterResetForm, FeedbackForm, LogoutForm, PauseVotingForm, CloseVotingForm, ResetScoresForm, VotingThresholdsForm, VoteLimitsForm, ScoreboardSettingsForm, QuickAdjustForm, AwardGameForm, EmployeeLoginForm, ChangePinForm, PortForm, RestartServiceForm, RebootPiForm
import time
import traceback
from datetime import datetime, timedelta
import calendar
import sqlite3
import threading
import io
import pandas as pd
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import os
import json
import random
import subprocess

# Legacy cache variables (kept for compatibility)
_data_cache = None
_cache_timestamp = None
_CACHE_DURATION = 60  # Cache for 60 seconds

setup_logging()
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
logging.debug("Application starting, initializing Flask app")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object('config.Config')
app.config['TEMPLATES_AUTO_RELOAD'] = True
csrf = CSRFProtect(app)
app.jinja_env.filters['zip'] = zip

# Add JSON parsing filter for templates
def from_json(value):
    try:
        return json.loads(value) if value else {}
    except (json.JSONDecodeError, TypeError):
        return {}

app.jinja_env.filters['from_json'] = from_json

# Validate database file existence
if not os.path.exists(Config.INCENTIVE_DB_FILE):
    logging.error(f"Database file not found: {Config.INCENTIVE_DB_FILE}")
    raise FileNotFoundError(f"Database file not found: {Config.INCENTIVE_DB_FILE}")

# Prevent module reload issues
if not hasattr(app, '_history_chart_defined'):
    app._history_chart_defined = True
else:
    logging.warning("Multiple imports of app.py detected, ensuring single history_chart definition")

# Context processor to inject settings and global forms
@app.context_processor
def inject_globals():
    with DatabaseConnection() as conn:
        settings = get_settings(conn)
    return dict(
        logout_form=LogoutForm(),
        site_name=settings.get('site_name', 'A1 Rent-It'),
        site_title=settings.get('site_title', 'A1 Rent-It'),
        primary_color=settings.get('primary_color', '#D4AF37'),
        secondary_color=settings.get('secondary_color', '#000000'),
        background_color=settings.get('background_color', '#3A3A3A'),
        surface_color=settings.get('surface_color', '#222222'),
        surface_alt_color=settings.get('surface_alt_color', '#1A1A1A'),
        score_top_color=settings.get('score_top_color', '#D4AF37'),
        score_mid_color=settings.get('score_mid_color', '#FFFFFF'),
        score_bottom_color=settings.get('score_bottom_color', '#FF6347'),
        reel_color=settings.get('reel_color', '#FFD700'),
        money_threshold=int(settings.get('money_threshold', 50)),
        scoreboard_spin_duration=int(settings.get('scoreboard_spin_duration', 10)),
        scoreboard_spin_iterations=int(settings.get('scoreboard_spin_iterations', 0)),
        scoreboard_spin_pause=int(settings.get('scoreboard_spin_pause', 0)),
        scoreboard_spin_delay=int(settings.get('scoreboard_spin_delay', 0)),
        scoreboard_refresh_interval=int(settings.get('scoreboard_refresh_interval', 60)),
        sound_on=settings.get('sound_on', '1'),
        strobe_mode=settings.get('strobe_mode', 'on'),
        banner_text=settings.get('banner_text', "JACKPOT TIME! GIVE 'EM THE MONEY! SLOTS SPINNING - WINNERS GRINNING!"),
        current_year=datetime.now().year,
        import_time=int(time.time())
    )

# Background thread for point decay
def point_decay_thread():
    logging.debug("Starting point_decay_thread")
    last_checked = None
    while True:
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        if last_checked != current_date:
            try:
                with DatabaseConnection() as conn:
                    last_run = conn.execute("SELECT value FROM settings WHERE key = 'last_decay_run'").fetchone()
                    if last_run and last_run['value'] == current_date:
                        logging.debug(f"Point decay already ran for {current_date}, skipping")
                        time.sleep(3600)  # Sleep for 1 hour before rechecking
                        continue
                    decay_settings = get_point_decay(conn)
                    today = now.strftime("%A")
                    any_decay_scheduled = False
                    for role_name, decay in decay_settings.items():
                        if today in decay["days"]:
                            any_decay_scheduled = True
                            success, message = deduct_points_daily(conn)
                            logging.debug(f"Point decay executed for {role_name}: {message}")
                    if not any_decay_scheduled:
                        logging.debug(f"No decay scheduled for {today}")
                    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('last_decay_run', current_date))
                    logging.debug(f"Updated last_decay_run to {current_date}")
                    conn.commit()
                last_checked = current_date
            except Exception as e:
                logging.error(f"Point decay error: {str(e)}\n{traceback.format_exc()}")
                time.sleep(300)  # Sleep 5 minutes on error to prevent rapid retries
            time.sleep(86400)  # Sleep for 24 hours after successful run
        else:
            time.sleep(3600)  # Sleep for 1 hour if already checked today
    logging.debug("Point_decay_thread terminated unexpectedly")

threading.Thread(target=point_decay_thread, daemon=True).start()
logging.debug("Point_decay_thread started")

def get_score_class(score, index, threshold):
    if index == 0:
        return 'score-top'
    elif score < threshold:
        return 'score-bottom'
    else:
        return 'score-mid'

def get_role_key_map(roles):
    """Generate dynamic role key map from roles, normalizing spaces to underscores."""
    role_key_map = {}
    for role in roles:
        role_name = role["role_name"]
        key = role_name.lower().replace(" ", "_")
        role_key_map[role_name] = key
    return role_key_map

@app.before_request
def make_session_permanent():
    session.permanent = True
    if 'admin_id' in session and request.endpoint in ['admin', 'admin_add', 'admin_adjust_points', 'admin_quick_adjust_points', 'admin_retire_employee', 'admin_reactivate_employee', 'admin_delete_employee', 'admin_edit_employee', 'admin_reset', 'admin_master_reset', 'admin_update_admin', 'admin_add_rule', 'admin_edit_rule', 'admin_remove_rule', 'admin_reorder_rules', 'admin_add_role', 'admin_edit_role', 'admin_remove_role', 'admin_update_pot_endpoint', 'admin_update_prior_year_sales', 'admin_set_point_decay', 'admin_mark_feedback_read', 'admin_delete_feedback', 'admin_settings', 'quick_adjust', 'export_payout', 'admin_toggle_section', 'admin_export_data', 'admin_start_voting_session', 'admin_end_voting_session', 'admin_game_details', 'admin_get_employee', 'admin_get_rule', 'admin_game_details_overview', 'admin_game_analytics', 'admin_game_settings', 'admin_award_game_manual', 'admin_revoke_game']:
        if 'last_activity' not in session:
            session.pop('admin_id', None)
            flash("Session expired. Please log in again.", "danger")
            return redirect(url_for('admin'))
        try:
            last_activity = datetime.fromisoformat(session['last_activity'])
            if (datetime.now() - last_activity).total_seconds() > 7200:
                session.pop('admin_id', None)
                session.pop('last_activity', None)
                flash("Session expired. Please log in again.", "danger")
                return redirect(url_for('admin'))
            session['last_activity'] = datetime.now().isoformat()
        except Exception as e:
            logging.error(f"Error in session check: {str(e)}\n{traceback.format_exc()}")
            session.pop('admin_id', None)
            session.pop('last_activity', None)
            flash("Session error. Please log in again.", "danger")
            return redirect(url_for('admin'))

        
@app.route("/", methods=["GET"])
def show_incentive():
    try:
        with DatabaseConnection() as conn:
            # Warm cache if available
            if CACHING_AVAILABLE and Config.CACHE_ENABLED:
                try:
                    warmer = get_cache_warmer()
                    warmer.warm_scoreboard_data(conn)
                    warmer.warm_configuration_data(conn)
                except Exception as e:
                    logging.warning(f"Cache warming failed: {e}")
            
            scoreboard = [{k: v for k, v in dict(row).items() if k != 'initials'} for row in get_scoreboard(conn)]
            voting_active = is_voting_active(conn)
            rules = get_rules(conn)
            pot_info = get_pot_info(conn)
            roles = get_roles(conn)
            role_key_map = get_role_key_map(roles)
            
            # Calculate payouts for each employee
            money_threshold = int(get_settings(conn).get('money_threshold', 50))
            for emp in scoreboard:
                role_key = emp['role'].lower().replace(' ', '_')
                point_value = pot_info.get(f'{role_key}_point_value', 0)
                if emp['score'] >= money_threshold:
                    emp['payout'] = round(emp['score'] * point_value, 2)
                else:
                    emp['payout'] = 0
            week_number = request.args.get("week", None, type=int)
            voting_results = get_voting_results(conn, is_admin=False, week_number=week_number)
            unread_feedback = get_unread_feedback_count(conn) if session.get("admin_id") else 0
            feedback = []
            employees = conn.execute(
                "SELECT employee_id, name, initials, score, role, active FROM employees WHERE LOWER(role) != 'master' AND active = 1"
            ).fetchall()
            employee_options = [
                (
                    emp["employee_id"],
                    f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} {'(Retired)' if emp['active'] == 0 else ''}"
                )
                for emp in employees
            ]
            reason_options = [(rule["description"], rule["description"]) for rule in rules] + [("Other", "Other")]
            week_options = [('', 'All Weeks')] + [(str(i), f"Week {i}") for i in range(1, 53)]
            total_pot = sum(pot_info[role_key_map.get(role['role_name'], role['role_name'].lower().replace(' ', '_')) + '_pot'] for role in roles)
            settings = get_settings(conn)
            max_plus_votes = int(settings.get('max_plus_votes', 2))
            max_minus_votes = int(settings.get('max_minus_votes', 3))
            max_total_votes = int(settings.get('max_total_votes', 3))
            recent_adjustments = get_recent_admin_adjustments(conn, limit=10)
        current_month = datetime.now().strftime("%B %Y")
        vote_form = VoteForm()
        feedback_form = FeedbackForm()
        adjust_form = QuickAdjustForm()
        adjust_form.employee_id.choices = employee_options
        logout_form = LogoutForm()
        logging.debug(f"Rendering incentive.html: voting_active={voting_active}, results_count={len(voting_results)}, total_pot={total_pot}")
        return render_template(
            "incentive.html",
            scoreboard=scoreboard,
            voting_active=voting_active,
            rules=rules,
            pot_info=pot_info,
            roles=roles,
            is_admin=bool(session.get("admin_id")),
            import_time=int(time.time()),
            voting_results=voting_results,
            current_month=current_month,
            selected_week=week_number,
            get_score_class=get_score_class,
            unread_feedback=unread_feedback,
            feedback=feedback,
            employee_options=employee_options,
            reason_options=reason_options,
            week_options=week_options,
            vote_form=vote_form,
            feedback_form=feedback_form,
            adjust_form=adjust_form,
            logout_form=logout_form,
            role_key_map=role_key_map,
            total_pot=total_pot,
            max_plus_votes=max_plus_votes,
            max_minus_votes=max_minus_votes,
            max_total_votes=max_total_votes,
            recent_adjustments=recent_adjustments,
            main_page=True
        )
    except Exception as e:
        logging.error(f"Error in show_incentive: {str(e)}\n{traceback.format_exc()}")
        flash("Internal server error", "danger")
        return render_template("error.html", error="Internal Server Error"), 500

@app.route("/data", methods=["GET"])
def incentive_data():
    start_time = time.time()
    try:
        # Try new caching system first
        if CACHING_AVAILABLE and Config.CACHE_ENABLED:
            cache = get_cache_manager()
            cached_data = cache.get('api_data')
            if cached_data is not None:
                request_time = time.time() - start_time
                logging.debug(f"Returning cached API data in {request_time:.3f} seconds")
                return jsonify(cached_data)
        
        # Fallback to legacy cache
        global _data_cache, _cache_timestamp
        if _data_cache and _cache_timestamp and (time.time() - _cache_timestamp) < _CACHE_DURATION:
            logging.debug("Returning legacy cached data for /data endpoint")
            return jsonify(_data_cache)
        
        logging.debug(f"Attempting to access database at: {Config.INCENTIVE_DB_FILE}")
        with DatabaseConnection() as conn:
            logging.debug("Database connection established")
            scoreboard = [{k: v for k, v in dict(row).items() if k != 'initials'} for row in get_scoreboard(conn)]
            voting_active = is_voting_active(conn)
            pot_info = get_pot_info(conn)
            
            if not scoreboard or not pot_info:
                logging.error("Failed to retrieve scoreboard or pot info from database")
                raise ValueError("Incomplete data retrieved")
            
            logging.debug(f"Scoreboard retrieved: {len(scoreboard)} entries")
            logging.debug(f"Voting active: {voting_active}")
            logging.debug(f"Pot info: {pot_info}")
            
            data = {"scoreboard": scoreboard, "voting_active": voting_active, "pot_info": pot_info}
            
            # Cache with new system
            if CACHING_AVAILABLE and Config.CACHE_ENABLED:
                cache.set('api_data', data, ttl=30, tags={'api', 'scoreboard', 'employee_data'})
                logging.debug("Cached API data with new caching system")
            
            # Legacy cache fallback
            _data_cache = data
            _cache_timestamp = time.time()
            
            request_time = time.time() - start_time
            logging.debug(f"API data request completed in {request_time:.3f} seconds")
            
        return jsonify(data)
    except sqlite3.OperationalError as e:
        logging.error(f"Database operational error in incentive_data: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": f"Database operational error: {str(e)}"}), 500
    except ValueError as ve:
        logging.error(f"Data validation error in incentive_data: {str(ve)}\n{traceback.format_exc()}")
        return jsonify({"error": f"Data validation error: {str(ve)}"}), 500
    except Exception as e:
        logging.error(f"Unexpected error in incentive_data: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

@app.route("/favicon.ico")
def favicon():
    favicon_path = os.path.join(app.static_folder, 'favicon.ico')
    if os.path.exists(favicon_path):
        return send_from_directory(app.static_folder, 'favicon.ico')
    logging.debug("favicon.ico not found in static folder, returning empty response")
    return '', 204

@app.route("/cache-stats", methods=["GET"])
def cache_stats():
    """Get cache performance statistics - admin only"""
    if "admin_id" not in session:
        return jsonify({"error": "Admin access required"}), 403
    
    if not CACHING_AVAILABLE:
        return jsonify({"error": "Caching system not available"}), 500
    
    try:
        metrics = get_metrics_collector()
        stats = metrics.get_performance_report()
        
        # Add pool statistics if available
        try:
            from incentive_service import get_pool_statistics
            pool_stats = get_pool_statistics()
            stats['database_pool'] = pool_stats
        except Exception as e:
            logging.warning(f"Could not get database pool stats: {e}")
        
        return jsonify({
            "cache_performance": stats,
            "timestamp": datetime.now().isoformat(),
            "cache_enabled": Config.CACHE_ENABLED
        })
    except Exception as e:
        logging.error(f"Error getting cache stats: {e}")
        return jsonify({"error": "Failed to get cache statistics"}), 500
@app.route("/start_voting", methods=["GET", "POST"])
def start_voting():
    global _data_cache, _cache_timestamp
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return jsonify({"success": False, "message": "Admin login required"}), 403
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
                    if CACHING_AVAILABLE and Config.CACHE_ENABLED:
                        get_invalidation_manager().invalidate_voting()
                    
                    # Legacy cache invalidation
                    _data_cache = None
                    _cache_timestamp = None
                    
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

@app.route("/close_voting", methods=["POST"])
def close_voting():
    global _data_cache, _cache_timestamp
    if "admin_id" not in session:
        logging.error("Close voting attempted without admin session")
        flash("Admin access required", "danger")
        return jsonify({"success": False, "message": "Admin access required"}), 403
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
            global _data_cache, _cache_timestamp
            _data_cache = None
            _cache_timestamp = None
            logging.debug("Voting session closed by admin_id: %s", session["admin_id"])
            flash("Voting session closed", "success")
            return jsonify({"success": True, "message": "Voting session closed"})
    except Exception as e:
        logging.error(f"Error closing voting: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/pause_voting", methods=["POST"])
def pause_voting():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
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

@app.route("/resume_voting", methods=["POST"])
def resume_voting():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
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

@app.route("/finalize_voting", methods=["POST"])
def finalize_voting():
    if "admin_id" not in session:
        flash("Admin access required", "danger")
        return jsonify({"success": False, "message": "Admin access required"}), 403
    form = CloseVotingForm(request.form)
    if not form.validate_on_submit():
        logging.error("Finalize voting form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    try:
        password = form.password.data
        with DatabaseConnection() as conn:
            admin = conn.execute("SELECT * FROM admins WHERE admin_id = ?", (session["admin_id"],)).fetchone()
            if not admin or not check_password_hash(admin["password"], password):
                logging.error("Invalid admin password for finalize voting: admin_id=%s", session["admin_id"])
                flash("Invalid admin password", "danger")
                return jsonify({"success": False, "message": "Invalid admin password"}), 403
            success, message = finalize_voting_session(conn, session["admin_id"])
            if not success:
                logging.error("Finalize voting failed: %s", message)
                flash(message, "danger")
                return jsonify({"success": False, "message": message}), 400
            conn.commit()
            global _data_cache, _cache_timestamp
            _data_cache = None
            _cache_timestamp = None
            logging.debug("Paused voting session finalized by admin_id: %s", session["admin_id"])
            flash("Voting session finalized", "success")
            return jsonify({"success": True, "message": "Voting session finalized"})
    except Exception as e:
        logging.error(f"Error finalizing voting: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/vote", methods=["POST"])
def vote():
    global _data_cache, _cache_timestamp
    logger = logging.getLogger(__name__)
    logger.debug("Received POST /vote request: %s", request.form)
    form = VoteForm(request.form)
    if not form.validate_on_submit():
        logger.error("Vote form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    voter_initials = form.initials.data.strip().lower()
    votes = {key.split("_")[1]: int(value) for key, value in request.form.items() if key.startswith("vote_") and value in ['-1', '0', '1']}
    try:
        with DatabaseConnection() as conn:
            if not is_voting_active(conn):
                logger.warning("Vote submission failed: Voting is not active")
                return jsonify({'success': False, 'message': 'Voting is not active'}), 400
            if not conn.execute("SELECT 1 FROM employees WHERE LOWER(initials) = ? AND active = 1", (voter_initials,)).fetchone():
                logger.warning("Vote submission failed: Invalid initials %s", voter_initials)
                return jsonify({'success': False, 'message': 'Invalid voter initials'}), 403
            success, message = cast_votes(conn, voter_initials, votes)
            if success and not is_voting_active(conn):
                close_voting_session(conn, 0)
                message += " Voting session closed."
                _data_cache = None
                _cache_timestamp = None
            logger.info("Vote result: initials=%s, success=%s, message=%s", voter_initials, success, message)
            return jsonify({'success': success, 'message': message})
    except Exception as e:
        logger.error("Error in vote: %s\n%s", str(e), traceback.format_exc())
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route("/check_vote", methods=["POST"])
def check_vote():
    try:
        initials = request.form.get("initials")
        if not initials or initials.strip() == '':
            return jsonify({"can_vote": False, "message": "Initials required"}), 400
        with DatabaseConnection() as conn:
            session = conn.execute("SELECT session_id FROM voting_sessions WHERE end_time IS NULL").fetchone()
            if not session:
                return jsonify({"can_vote": False, "message": "Voting is not active"}), 400
            if not conn.execute("SELECT 1 FROM employees WHERE LOWER(initials) = ? AND active = 1", (initials.lower(),)).fetchone():
                return jsonify({"can_vote": False, "message": "Invalid initials"})
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vote_participants (
                    session_id INTEGER,
                    voter_initials TEXT,
                    PRIMARY KEY (session_id, voter_initials),
                    FOREIGN KEY(session_id) REFERENCES voting_sessions(session_id)
                )
                """
            )
            existing_vote = conn.execute(
                "SELECT 1 FROM vote_participants WHERE session_id = ? AND LOWER(voter_initials) = ?",
                (session["session_id"], initials.lower())
            ).fetchone()
            if existing_vote:
                return jsonify({"can_vote": False, "message": "You have already voted in this session"})
            return jsonify({"can_vote": True})
    except Exception as e:
        logging.error(f"Error in check_vote: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"can_vote": False, "message": "Server error"}), 500

@app.route("/admin", methods=["GET", "POST"])
def admin():
    form = AdminLoginForm()
    logging.debug(f"Session state for /admin: {session}")
    logging.debug(f"Form CSRF token: {form.csrf_token.current_token if form.csrf_token else 'No CSRF token'}")
    if request.method == "POST" and "username" in request.form:
        try:
            if not form.validate_on_submit():
                logging.error("Admin login form validation failed: %s", form.errors)
                flash("Invalid form data: " + str(form.errors), "danger")
                return render_template("admin_login.html", form=form, import_time=int(time.time()))
            username = form.username.data
            password = form.password.data
            logging.debug(f"Attempting admin login for username: {username}")
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
                if admin and check_password_hash(admin["password"], password):
                    session["admin_id"] = admin["admin_id"]
                    session['last_activity'] = datetime.now().isoformat()
                    logging.debug(f"Admin login successful: {username}, session: {session}")
                    return redirect(url_for("admin"))
                flash("Invalid credentials", "danger")
                logging.debug(f"Admin login failed for {username}: Invalid credentials")
        except CSRFError as e:
            logging.error(f"CSRF error in admin login: {str(e)}\n{traceback.format_exc()}")
            flash("CSRF validation failed. Please try again.", "danger")
        except Exception as e:
            logging.error(f"Error in admin login: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
        return render_template("admin_login.html", form=form, import_time=int(time.time()))
    if "admin_id" not in session:
        logging.debug("Rendering admin_login.html: no admin_id in session")
        return render_template("admin_login.html", form=form, import_time=int(time.time()))
    try:
        with DatabaseConnection() as conn:
            logging.debug("Admin route: Opening database connection")
            employees = conn.execute("SELECT employee_id, name, initials, score, role, active FROM employees").fetchall()
            rules = get_rules(conn)
            pot_info = get_pot_info(conn)
            roles = get_roles(conn)
            role_key_map = get_role_key_map(roles)
            # Calculate total pot
            total_pot = sum(pot_info.get(f"{role_key_map.get(role['role_name'], role['role_name'].lower().replace(' ', '_'))}_pot", 0.0) for role in roles)
            decay = get_point_decay(conn)
            admins = conn.execute("SELECT admin_id, username FROM admins").fetchall() if session.get("admin_id") == "master" else []
            mini_games = [dict(row) for row in conn.execute("SELECT mg.id, e.name, mg.game_type, mg.status, mg.outcome FROM mini_games mg JOIN employees e ON mg.employee_id = e.employee_id").fetchall()]
            voting_results = []
            vote_totals = []
            sessions_list = []
            selected_session_id = None
            raw_votes = []
            now = datetime.now()
            history = [dict(row) for row in get_history(conn, datetime.now().strftime("%Y-%m"))]
            total_payout = 0
            # Calculate employee payouts
            employee_payouts = []
            for emp in employees:
                if emp["active"] == 1 and emp["score"] >= 50:
                    role_key = role_key_map.get(emp["role"].capitalize(), emp["role"].lower().replace(" ", "_"))
                    point_value = pot_info.get(f"{role_key}_point_value", 0)
                    payout = emp["score"] * point_value
                    total_payout += payout
                    employee_payouts.append({"employee_id": emp["employee_id"], "name": emp["name"], "score": emp["score"], "payout": payout})
            if session.get("admin_id") == "master":
                sessions_list = [dict(row) for row in conn.execute(
                    "SELECT session_id, start_time, end_time FROM voting_sessions ORDER BY start_time DESC"
                ).fetchall()]
                requested_session = request.args.get("session_id", type=int)
                if requested_session:
                    selected_session = conn.execute(
                        "SELECT session_id, start_time, end_time FROM voting_sessions WHERE session_id = ?",
                        (requested_session,)
                    ).fetchone()
                else:
                    selected_session = sessions_list[0] if sessions_list else None
                if selected_session:
                    selected_session_id = selected_session["session_id"]
                    results = conn.execute(
                        "SELECT vr.employee_id, e.name AS recipient_name, vr.plus_votes, vr.minus_votes, vr.plus_percent, vr.minus_percent, vr.points "
                        "FROM voting_results vr JOIN employees e ON vr.employee_id = e.employee_id "
                        "WHERE vr.session_id = ?",
                        (selected_session_id,),
                    ).fetchall()
                    voting_results = [dict(row) for row in results]
                    vote_totals = [
                        {
                            "recipient_name": row["recipient_name"],
                            "plus": row["plus_votes"],
                            "minus": row["minus_votes"],
                            "points": row["points"],
                        }
                        for row in voting_results
                    ]
                    start_date = selected_session["start_time"]
                    end_date = selected_session["end_time"] or now.strftime("%Y-%m-%d %H:%M:%S")
                    raw_vote_rows = conn.execute(
                        "SELECT v.voter_initials, e.name AS recipient_name, v.vote_value, v.vote_date "
                        "FROM votes v JOIN employees e ON v.recipient_id = e.employee_id "
                        "WHERE v.vote_date >= ? AND v.vote_date <= ? "
                        "ORDER BY v.vote_date DESC",
                        (start_date, end_date)
                    ).fetchall()
                    raw_votes = [dict(row) for row in raw_vote_rows]
            # Voting status
            active_session = conn.execute("SELECT session_id FROM voting_sessions WHERE end_time IS NULL").fetchone()
            voted_initials = set()
            if active_session:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS vote_participants (
                        session_id INTEGER,
                        voter_initials TEXT,
                        PRIMARY KEY (session_id, voter_initials),
                        FOREIGN KEY(session_id) REFERENCES voting_sessions(session_id)
                    )
                    """
                )
                voted_initials = set(
                    row["voter_initials"].lower()
                    for row in conn.execute(
                        "SELECT voter_initials FROM vote_participants WHERE session_id = ?",
                        (active_session["session_id"],),
                    ).fetchall()
                )
            active_employees = [emp for emp in employees if emp["active"] == 1]
            voting_status = [
                {"initials": emp["initials"], "voted": emp["initials"].lower() in voted_initials}
                for emp in active_employees
            ]
            voting_status.sort(key=lambda x: x["voted"])
            unread_feedback = get_unread_feedback_count(conn)
            feedback = get_feedback(conn) if session.get("admin_id") == "master" else []
            settings = get_settings(conn)
            section_permissions = {section: settings.get(f'allow_section_{section}', '0') == '1' for section in Config.ADMIN_SECTIONS}
            employee_options = [(emp["employee_id"], f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} {'(Retired)' if emp['active'] == 0 else ''}") for emp in employees]
            role_options = [(role["role_name"], role["role_name"]) for role in roles]
            admin_options = [(admin["username"], f"{admin['username']} ({admin['admin_id']})") for admin in admins] if session.get("admin_id") == "master" else []
            decay_role_options = [(role["role_name"], f"{role['role_name']} (Current: {decay.get(role['role_name'], {'points': 1, 'days': []})['points']} points, {', '.join(decay.get(role['role_name'], {'days': []})['days'])})") for role in roles]
            reason_options = [(r["description"], r["description"]) for r in rules] + [("Other", "Other")]
            voting_active = is_voting_active(conn)
            paused_session = conn.execute(
                """
                SELECT vs.session_id FROM voting_sessions vs
                LEFT JOIN voting_results vr ON vs.session_id = vr.session_id
                WHERE vs.end_time IS NOT NULL AND vr.session_id IS NULL
                ORDER BY vs.end_time DESC LIMIT 1
                """
            ).fetchone()
            voting_paused = paused_session is not None
            # Instantiate and populate forms with attributes for macro compatibility
            start_voting_form = StartVotingForm()
            pause_voting_form = PauseVotingForm()
            close_voting_form = CloseVotingForm()
            add_employee_form = AddEmployeeForm()
            add_employee_form.name.data = ''
            add_employee_form.initials.data = ''
            add_employee_form.role.data = 'Driver'
            add_employee_form.pin.data = '8101'  # Default PIN
            edit_employee_form = EditEmployeeForm()
            edit_employee_form.employee_id.data = employee_options[0][0] if employee_options else ''
            edit_employee_form.name.data = ''
            edit_employee_form.role.data = 'Driver'
            award_game_form = AwardGameForm()
            award_game_form.employee_id.data = employee_options[0][0] if employee_options else ''
            award_game_form.game_type.data = 'slot'
            close_voting_form.password.data = ''
            update_pot_form = UpdatePotForm()
            update_pot_form.sales_dollars.data = pot_info.get('sales_dollars', 100000)
            update_pot_form.bonus_percent.data = pot_info.get('bonus_percent', 10)
            update_prior_year_sales_form = UpdatePriorYearSalesForm()
            update_prior_year_sales_form.prior_year_sales.data = pot_info.get('prior_year_sales', 50000)
            update_admin_form = UpdateAdminForm()
            update_admin_form.old_username.data = admin_options[0][0] if admin_options else ''
            update_admin_form.new_username.data = ''
            update_admin_form.new_password.data = ''
            add_rule_form = AddRuleForm()
            add_rule_form.description.data = ''
            add_rule_form.points.data = 0
            add_rule_form.details.data = ''
            add_role_form = AddRoleForm()
            add_role_form.role_name.data = ''
            add_role_form.percentage.data = 0
            edit_role_form = EditRoleForm()
            edit_role_form.old_role_name.data = role_options[0][0] if role_options else ''
            edit_role_form.new_role_name.data = ''
            edit_role_form.percentage.data = 0
            remove_role_form = RemoveRoleForm()
            remove_role_form.role_name.data = role_options[0][0] if role_options else ''
            set_point_decay_form = SetPointDecayForm()
            default_role = decay_role_options[0][0] if decay_role_options else ''
            set_point_decay_form.role_name.data = default_role
            if default_role:
                set_point_decay_form.points.data = decay.get(default_role, {'points': 0})['points']
                set_point_decay_form.days.data = decay.get(default_role, {'days': []})['days']
            else:
                set_point_decay_form.points.data = 0
                set_point_decay_form.days.data = []
            thresholds_form = VotingThresholdsForm()
            thresholds_data = json.loads(settings.get('voting_thresholds', '{"positive":[{"threshold":90,"points":10},{"threshold":60,"points":5},{"threshold":25,"points":2}],"negative":[{"threshold":90,"points":-10},{"threshold":60,"points":-5},{"threshold":25,"points":-2}]}'))
            thresholds_form.pos_threshold_1.data = thresholds_data['positive'][0]['threshold']
            thresholds_form.pos_points_1.data = thresholds_data['positive'][0]['points']
            thresholds_form.pos_threshold_2.data = thresholds_data['positive'][1]['threshold']
            thresholds_form.pos_points_2.data = thresholds_data['positive'][1]['points']
            thresholds_form.pos_threshold_3.data = thresholds_data['positive'][2]['threshold']
            thresholds_form.pos_points_3.data = thresholds_data['positive'][2]['points']
            thresholds_form.neg_threshold_1.data = thresholds_data['negative'][0]['threshold']
            thresholds_form.neg_points_1.data = thresholds_data['negative'][0]['points']
            thresholds_form.neg_threshold_2.data = thresholds_data['negative'][1]['threshold']
            thresholds_form.neg_points_2.data = thresholds_data['negative'][1]['points']
            thresholds_form.neg_threshold_3.data = thresholds_data['negative'][2]['threshold']
            thresholds_form.neg_points_3.data = thresholds_data['negative'][2]['points']
            logging.debug(f"Form data populated: add_rule_form.description={add_rule_form.description.data}, update_pot_form.sales_dollars={update_pot_form.sales_dollars.data}")
        # Clear stale flashes
        session.pop('_flashes', None)
        logging.debug("Admin route: Database connection closed, rendering admin_manage.html")
        return render_template(
            "admin_manage.html",
            employees=employees,
            rules=rules,
            pot_info=pot_info,
            roles=roles,
            decay=decay,
            admins=admins,
            mini_games=mini_games,
            voting_results=voting_results,
            vote_totals=vote_totals,
            raw_votes=raw_votes,
            sessions=sessions_list,
            selected_session_id=selected_session_id,
            employee_payouts=employee_payouts,
            total_payout=total_payout,
            total_pot=total_pot,
            voting_status=voting_status,
            is_admin=True,
            is_master=session.get("admin_id") == "master",
            import_time=int(time.time()),
            admin_page=True,
            unread_feedback=unread_feedback,
            feedback=feedback,
            settings=settings,
            section_permissions=section_permissions,
            default_start_date=datetime.now().replace(day=1).strftime("%Y-%m-%d"),
            default_end_date=datetime.now().replace(day=calendar.monthrange(datetime.now().year, datetime.now().month)[1]).strftime("%Y-%m-%d"),
            employee_options=employee_options,
            role_options=role_options,
            admin_options=admin_options,
            decay_role_options=decay_role_options,
            reason_options=reason_options,
            history=history,
            voting_active=voting_active,
            voting_paused=voting_paused,
            voting_settings={'max_plus_votes': 2, 'max_minus_votes': 3, 'max_total_votes': 3},
            votes_today=0,
            unique_voters_today=0,
            plus_votes_today=0,
            minus_votes_today=0,
            voting_history=[],
            start_voting_form={
                'username': {'name': 'username', 'id': 'start_voting_username', 'label_text': 'Username', 'value': start_voting_form.username.data, 'class': 'form-control', 'required': True},
                'password': {'name': 'password', 'id': 'start_voting_password', 'label_text': 'Password', 'value': start_voting_form.password.data, 'class': 'form-control', 'type': 'password', 'required': True}
            },
            pause_voting_form={'submit': {'text': 'Pause Voting', 'class': 'btn btn-warning'}},
            resume_voting_form={'submit': {'text': 'Resume Voting', 'class': 'btn btn-success'}},
            close_voting_form={
                'password': {'name': 'password', 'id': 'close_voting_password', 'label_text': 'Admin Password', 'value': close_voting_form.password.data, 'class': 'form-control', 'type': 'password', 'required': True},
                'submit': {'text': 'Close Voting', 'class': 'btn btn-danger'}
            },
            finalize_voting_form={
                'password': {'name': 'password', 'id': 'finalize_voting_password', 'label_text': 'Admin Password', 'value': close_voting_form.password.data, 'class': 'form-control', 'type': 'password', 'required': True},
                'submit': {'text': 'Finalize Voting', 'class': 'btn btn-danger'}
            },
            add_employee_form={
                'name': {'name': 'name', 'id': 'add_employee_name', 'label_text': 'Name', 'value': add_employee_form.name.data, 'class': 'form-control', 'required': True},
                'initials': {'name': 'initials', 'id': 'add_employee_initials', 'label_text': 'Initials', 'value': add_employee_form.initials.data, 'class': 'form-control', 'required': True},
                'role': {'name': 'role', 'id': 'add_employee_role', 'label_text': 'Role', 'options': role_options, 'selected_value': add_employee_form.role.data, 'class': 'form-control'},
                'pin': {'name': 'pin', 'id': 'add_employee_pin', 'label_text': 'PIN', 'value': '', 'class': 'form-control', 'type': 'password', 'required': True}
            },
            adjust_points_form=AdjustPointsForm(),
            add_rule_form={
                'description': {'name': 'description', 'id': 'add_rule_description', 'label_text': 'Description', 'value': add_rule_form.description.data, 'class': 'form-control', 'required': True},
                'points': {'name': 'points', 'id': 'add_rule_points', 'label_text': 'Points', 'value': add_rule_form.points.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'details': {'name': 'details', 'id': 'add_rule_details', 'label_text': 'Notes', 'value': add_rule_form.details.data, 'class': 'form-control', 'type': 'textarea'}
            },
            edit_rule_form={
                'old_description': {'name': 'old_description', 'id': 'edit_rule_old_description', 'label_text': 'Old Description', 'value': '', 'class': 'form-control', 'required': True},
                'new_description': {'name': 'new_description', 'id': 'edit_rule_new_description', 'label_text': 'New Description', 'value': '', 'class': 'form-control', 'required': True},
                'points': {'name': 'points', 'id': 'edit_rule_points', 'label_text': 'Points', 'value': 0, 'class': 'form-control', 'type': 'number', 'required': True},
                'details': {'name': 'details', 'id': 'edit_rule_details', 'label_text': 'Notes', 'value': '', 'class': 'form-control', 'type': 'textarea'}
            },
            remove_rule_form=RemoveRuleForm(),
            edit_employee_form={
                'employee_id': {'name': 'employee_id', 'id': 'edit_employee_id', 'label_text': 'Employee', 'options': employee_options, 'selected_value': edit_employee_form.employee_id.data, 'class': 'form-control'},
                'name': {'name': 'name', 'id': 'edit_employee_name', 'label_text': 'Name', 'value': edit_employee_form.name.data, 'class': 'form-control', 'required': True},
                'role': {'name': 'role', 'id': 'edit_employee_role', 'label_text': 'Role', 'options': role_options, 'selected_value': edit_employee_form.role.data, 'class': 'form-control'},
                'pin': {'name': 'pin', 'id': 'edit_employee_pin', 'label_text': 'PIN', 'value': '', 'class': 'form-control', 'type': 'password', 'required': True}
            },
            retire_employee_form=RetireEmployeeForm(),
            reactivate_employee_form=ReactivateEmployeeForm(),
            delete_employee_form=DeleteEmployeeForm(),
            update_pot_form={
                'sales_dollars': {'name': 'sales_dollars', 'id': 'update_pot_sales_dollars', 'label_text': 'Sales Dollars ($)', 'value': update_pot_form.sales_dollars.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'bonus_percent': {'name': 'bonus_percent', 'id': 'update_pot_bonus_percent', 'label_text': 'Bonus Percent (%)', 'value': update_pot_form.bonus_percent.data, 'class': 'form-control', 'type': 'number', 'required': True}
            },
            update_prior_year_sales_form={
                'prior_year_sales': {'name': 'prior_year_sales', 'id': 'update_prior_year_sales_prior_year_sales', 'label_text': 'Prior Year Sales ($)', 'value': update_prior_year_sales_form.prior_year_sales.data, 'class': 'form-control', 'type': 'number', 'required': True}
            },
            update_admin_form={
                'old_username': {'name': 'old_username', 'id': 'update_admin_old_username', 'label_text': 'Old Username', 'options': admin_options, 'selected_value': update_admin_form.old_username.data, 'class': 'form-control'},
                'new_username': {'name': 'new_username', 'id': 'update_admin_new_username', 'label_text': 'New Username', 'value': update_admin_form.new_username.data, 'class': 'form-control', 'required': True},
                'new_password': {'name': 'new_password', 'id': 'update_admin_new_password', 'label_text': 'New Password', 'value': update_admin_form.new_password.data, 'class': 'form-control', 'type': 'password', 'required': True}
            },
            add_role_form={
                'role_name': {'name': 'role_name', 'id': 'add_role_name', 'label_text': 'Role Name', 'value': add_role_form.role_name.data, 'class': 'form-control', 'required': True},
                'percentage': {'name': 'percentage', 'id': 'add_role_percentage', 'label_text': 'Percentage', 'value': add_role_form.percentage.data, 'class': 'form-control', 'type': 'number', 'required': True}
            },
            edit_role_form={
                'old_role_name': {'name': 'old_role_name', 'id': 'edit_role_old_role_name', 'label_text': 'Old Role Name', 'options': role_options, 'selected_value': edit_role_form.old_role_name.data, 'class': 'form-control'},
                'new_role_name': {'name': 'new_role_name', 'id': 'edit_role_new_role_name', 'label_text': 'New Role Name', 'value': edit_role_form.new_role_name.data, 'class': 'form-control', 'required': True},
                'percentage': {'name': 'percentage', 'id': 'edit_role_percentage', 'label_text': 'Percentage', 'value': edit_role_form.percentage.data, 'class': 'form-control', 'type': 'number', 'required': True}
            },
            remove_role_form={
                'role_name': {'name': 'role_name', 'id': 'remove_role_name', 'label_text': 'Role Name', 'options': role_options, 'selected_value': remove_role_form.role_name.data, 'class': 'form-control'}
            },
            award_game_form={
                'employee_id': {'name': 'employee_id', 'id': 'award_game_employee', 'label_text': 'Employee', 'options': employee_options, 'selected_value': award_game_form.employee_id.data, 'class': 'form-control'},
                'game_type': {'name': 'game_type', 'id': 'award_game_type', 'label_text': 'Game Type', 'options': [('slot', 'Slot'), ('scratch', 'Scratch-Off'), ('roulette', 'Roulette')], 'selected_value': award_game_form.game_type.data, 'class': 'form-control'}
            },
            set_point_decay_form={
                'role_name': {'name': 'role_name', 'id': 'set_point_decay_role_name', 'label_text': 'Role', 'options': decay_role_options, 'selected_value': set_point_decay_form.role_name.data, 'class': 'form-control'},
                'points': {'name': 'points', 'id': 'set_point_decay_points', 'label_text': 'Points to Deduct Daily', 'value': set_point_decay_form.points.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'days': {'name': 'days', 'id': 'set_point_decay_days', 'label_text': 'Days to Trigger', 'options': [('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'), ('Thursday', 'Thursday'), ('Friday', 'Friday'), ('Saturday', 'Saturday'), ('Sunday', 'Sunday')], 'selected_values': set_point_decay_form.days.data, 'class': 'form-control', 'multiple': True}
            },
            thresholds_form={
                'pos_threshold_1': {'name': 'pos_threshold_1', 'id': 'pos_threshold_1', 'label_text': 'Positive Threshold 1 (%)', 'value': thresholds_form.pos_threshold_1.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'pos_points_1': {'name': 'pos_points_1', 'id': 'pos_points_1', 'label_text': 'Positive Points 1', 'value': thresholds_form.pos_points_1.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'pos_threshold_2': {'name': 'pos_threshold_2', 'id': 'pos_threshold_2', 'label_text': 'Positive Threshold 2 (%)', 'value': thresholds_form.pos_threshold_2.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'pos_points_2': {'name': 'pos_points_2', 'id': 'pos_points_2', 'label_text': 'Positive Points 2', 'value': thresholds_form.pos_points_2.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'pos_threshold_3': {'name': 'pos_threshold_3', 'id': 'pos_threshold_3', 'label_text': 'Positive Threshold 3 (%)', 'value': thresholds_form.pos_threshold_3.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'pos_points_3': {'name': 'pos_points_3', 'id': 'pos_points_3', 'label_text': 'Positive Points 3', 'value': thresholds_form.pos_points_3.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'neg_threshold_1': {'name': 'neg_threshold_1', 'id': 'neg_threshold_1', 'label_text': 'Negative Threshold 1 (%)', 'value': thresholds_form.neg_threshold_1.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'neg_points_1': {'name': 'neg_points_1', 'id': 'neg_points_1', 'label_text': 'Negative Points 1', 'value': thresholds_form.neg_points_1.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'neg_threshold_2': {'name': 'neg_threshold_2', 'id': 'neg_threshold_2', 'label_text': 'Negative Threshold 2 (%)', 'value': thresholds_form.neg_threshold_2.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'neg_points_2': {'name': 'neg_points_2', 'id': 'neg_points_2', 'label_text': 'Negative Points 2', 'value': thresholds_form.neg_points_2.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'neg_threshold_3': {'name': 'neg_threshold_3', 'id': 'neg_threshold_3', 'label_text': 'Negative Threshold 3 (%)', 'value': thresholds_form.neg_threshold_3.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'neg_points_3': {'name': 'neg_points_3', 'id': 'neg_points_3', 'label_text': 'Negative Points 3', 'value': thresholds_form.neg_points_3.data, 'class': 'form-control', 'type': 'number', 'required': True}
            },
            role_key_map=role_key_map
        )
    except Exception as e:
        logging.error(f"Error in admin: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('admin'))


@app.route("/admin/analytics", methods=["GET"])
def admin_analytics():
    """Advanced analytics dashboard for admins"""
    if "admin_id" not in session:
        return redirect(url_for("admin"))
    
    try:
        # Just render the analytics page - data will be loaded via API calls
        return render_template("admin_analytics.html")
    except Exception as e:
        logging.error(f"Error in admin analytics: {str(e)}")
        flash("Error loading analytics dashboard", "danger")
        return redirect(url_for("admin"))


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_id", None)
    session.pop("last_activity", None)
    flash("Logged out successfully", "success")
    return redirect(url_for("show_incentive"))

@app.route("/admin/add", methods=["POST"])
def admin_add():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    try:
        with DatabaseConnection() as conn:
            roles = get_roles(conn)
            role_options = [(role["role_name"], role["role_name"]) for role in roles]
        form = AddEmployeeForm(request.form)
        form.role.choices = role_options
        logging.debug("Add employee form data received: %s", {k: v for k, v in request.form.items()})
        logging.debug("Role choices: %s", form.role.choices)
        if not form.validate_on_submit():
            logging.error("Add employee form validation failed: %s, form data: %s", form.errors, {k: v for k, v in request.form.items()})
            return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
        name = form.name.data
        initials = form.initials.data
        role = form.role.data
        pin = form.pin.data
        with DatabaseConnection() as conn:
            success, message = add_employee(conn, name, initials, role, pin)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_add: {str(e)}\n{traceback.format_exc()}, form data: %s", {k: v for k, v in request.form.items()})
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500
    
@app.route("/admin/adjust_points", methods=["POST"])
def admin_adjust_points():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = AdjustPointsForm(request.form)
    if not form.validate_on_submit():
        logging.error("Adjust points form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    employee_id = form.employee_id.data
    points = form.points.data
    reason = form.reason.data
    notes = form.notes.data or ""
    try:
        with DatabaseConnection() as conn:
            role_row = conn.execute(
                "SELECT LOWER(role) AS role FROM employees WHERE employee_id = ?",
                (employee_id,)
            ).fetchone()
            if role_row and role_row["role"] == "master":
                logging.warning(
                    "Attempt to adjust points for master account: employee_id=%s", employee_id
                )
                return (
                    jsonify({"success": False, "message": "Cannot adjust points for master account"}),
                    400,
                )
            success, message = adjust_points(
                conn, employee_id, points, session["admin_id"], reason, notes
            )
        script = "playJackpot();" if points and points > 0 else ""
        return jsonify({"success": success, "message": message, "script": script})
    except Exception as e:
        logging.error(f"Error in admin_adjust_points: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/quick_adjust", methods=["GET"])
def quick_adjust():
    start_time = time.time()
    try:
        points = request.args.get('points', type=int)
        reason = request.args.get('reason', '')
        logging.debug(f"Redirecting /quick_adjust to / with points={points}, reason={reason}")
        session['quick_adjust_data'] = {'points': points, 'reason': reason}
        return redirect(url_for('show_incentive'))
    except Exception as e:
        logging.error(f"Error in quick_adjust: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('show_incentive'))

@app.route("/admin/quick_adjust_points", methods=["POST"])
def admin_quick_adjust_points():
    start_time = time.time()
    try:
        with DatabaseConnection() as conn:
            employees = conn.execute(
                "SELECT employee_id, name, initials, score, role, active FROM employees WHERE LOWER(role) != 'master'"
            ).fetchall()
            employee_options = [
                (
                    emp["employee_id"],
                    f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} {'(Retired)' if emp['active'] == 0 else ''}"
                )
                for emp in employees
            ]
        form = QuickAdjustForm(request.form)
        form.employee_id.choices = employee_options
        logging.debug("Quick adjust form data received: %s", {k: v if k != 'password' else '****' for k, v in request.form.items()})
        if not form.validate():
            logging.error("Quick adjust form validation failed: %s, form data: %s", form.errors, {k: v if k != 'password' else '****' for k, v in request.form.items()})
            return jsonify({"success": False, "message": "Invalid form data: " + str(form.errors)}), 400
        if "admin_id" not in session:
            if not form.username.data or not form.password.data:
                logging.error("Quick adjust form missing username or password for non-admin")
                return jsonify({"success": False, "message": "Username and password required for non-admin users"}), 400
            username = form.username.data
            password = form.password.data
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
                if not admin or not check_password_hash(admin["password"], password):
                    logging.error("Invalid admin credentials for username: %s", username)
                    return jsonify({"success": False, "message": "Invalid admin credentials"}), 403
                session["admin_id"] = admin["admin_id"]
                session["last_activity"] = datetime.now().isoformat()
        employee_id = form.employee_id.data
        points = form.points.data
        reason = form.reason.data
        notes = form.notes.data or ""
        with DatabaseConnection() as conn:
            role_row = conn.execute(
                "SELECT LOWER(role) AS role FROM employees WHERE employee_id = ?",
                (employee_id,)
            ).fetchone()
            if role_row and role_row["role"] == "master":
                logging.warning(
                    "Attempt to quick adjust points for master account: employee_id=%s", employee_id
                )
                return (
                    jsonify({"success": False, "message": "Cannot adjust points for master account"}),
                    400,
                )
            success, message = adjust_points(
                conn, employee_id, points, session["admin_id"], reason, notes
            )
            if not success:
                logging.error("Quick adjust failed: %s", message)
                return jsonify({"success": False, "message": message}), 400
            conn.commit()
        global _data_cache, _cache_timestamp
        _data_cache = None
        _cache_timestamp = None
        logging.debug(f"Route /admin/quick_adjust_points took {time.time() - start_time:.2f} seconds")
        script = "playJackpot();" if points and points > 0 else ""
        return jsonify({"success": True, "message": f"Adjusted {points} points for employee {employee_id}", "script": script})
    except Exception as e:
        logging.error(f"Error in quick_adjust_points: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500
    
@app.route("/admin/retire_employee", methods=["POST"])
def admin_retire_employee():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    try:
        with DatabaseConnection() as conn:
            employees = conn.execute("SELECT employee_id, name, initials, score, active FROM employees").fetchall()
            employee_options = [(emp["employee_id"], f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} {'(Retired)' if emp['active'] == 0 else ''}") for emp in employees]
        form = RetireEmployeeForm(request.form)
        form.employee_id.choices = employee_options
        logging.debug("Retire employee form data: %s", dict(request.form))
        logging.debug("Employee ID choices: %s", form.employee_id.choices)
        if not form.validate_on_submit():
            logging.error("Retire employee form validation failed: %s", form.errors)
            return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
        employee_id = form.employee_id.data
        with DatabaseConnection() as conn:
            success, message = retire_employee(conn, employee_id)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_retire_employee: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/reactivate_employee", methods=["POST"])
def admin_reactivate_employee():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    try:
        with DatabaseConnection() as conn:
            employees = conn.execute("SELECT employee_id, name, initials, score, active FROM employees WHERE active = 0").fetchall()
            employee_options = [(emp["employee_id"], f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} (Retired)") for emp in employees]
        form = ReactivateEmployeeForm(request.form)
        form.employee_id.choices = employee_options
        logging.debug("Reactivate employee form data: %s", dict(request.form))
        logging.debug("Employee ID choices: %s", form.employee_id.choices)
        try:
            valid = form.validate_on_submit()
        except Exception as e:
            logging.error("Reactivate employee form validation exception: %s", str(e))
            return jsonify({'success': False, 'message': 'Invalid form data: ' + str(e)}), 400
        if not valid:
            logging.error("Reactivate employee form validation failed: %s", form.errors)
            return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
        employee_id = form.employee_id.data
        with DatabaseConnection() as conn:
            success, message = reactivate_employee(conn, employee_id)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_reactivate_employee: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/delete_employee", methods=["POST"])
def admin_delete_employee():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    try:
        with DatabaseConnection() as conn:
            employees = conn.execute("SELECT employee_id, name, initials, score, active FROM employees").fetchall()
            employee_options = [(emp["employee_id"], f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} {'(Retired)' if emp['active'] == 0 else ''}") for emp in employees]
        form = DeleteEmployeeForm(request.form)
        form.employee_id.choices = employee_options
        logging.debug("Delete employee form data: %s", dict(request.form))
        logging.debug("Employee ID choices: %s", form.employee_id.choices)
        if not form.validate_on_submit():
            logging.error("Delete employee form validation failed: %s", form.errors)
            return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
        employee_id = form.employee_id.data
        with DatabaseConnection() as conn:
            success, message = delete_employee(conn, employee_id)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_delete_employee: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/edit_employee", methods=["POST"])
def admin_edit_employee():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    try:
        with DatabaseConnection() as conn:
            employees = conn.execute("SELECT employee_id, name, initials, score, role, active FROM employees").fetchall()
            roles = get_roles(conn)
            employee_options = [(emp["employee_id"], f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} {'(Retired)' if emp['active'] == 0 else ''}") for emp in employees]
            role_options = [(role["role_name"], role["role_name"]) for role in roles]
        form = EditEmployeeForm(request.form)
        form.employee_id.choices = employee_options
        form.role.choices = role_options
        logging.debug("Edit employee form data: %s", dict(request.form))
        logging.debug("Employee ID choices: %s", form.employee_id.choices)
        logging.debug("Role choices: %s", form.role.choices)
        if not form.validate_on_submit():
            logging.error("Edit employee form validation failed: %s", form.errors)
            return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
        employee_id = form.employee_id.data
        name = form.name.data
        role = form.role.data
        pin = form.pin.data
        with DatabaseConnection() as conn:
            success, message = edit_employee(conn, employee_id, name, role, pin)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_edit_employee: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500


@app.route("/admin/award_game", methods=["POST"])
def admin_award_game():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    try:
        with DatabaseConnection() as conn:
            employees = conn.execute("SELECT employee_id, name, initials, score, role, active FROM employees").fetchall()
            employee_options = [
                (emp["employee_id"], f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} {'(Retired)' if emp['active'] == 0 else ''}")
                for emp in employees
            ]
        form = AwardGameForm(request.form)
        form.employee_id.choices = employee_options
        if not form.validate_on_submit():
            return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
        employee_id = form.employee_id.data
        game_type = form.game_type.data
        with DatabaseConnection() as conn:
            success, gt = award_mini_game(conn, employee_id, game_type)
        return jsonify({'success': success, 'message': f'Awarded {gt} game'})
    except Exception as e:
        logging.error(f"Error in admin_award_game: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/reset", methods=["POST"])
def admin_reset():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = ResetScoresForm(request.form)
    if not form.validate_on_submit():
        logging.error("Reset scores form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    try:
        with DatabaseConnection() as conn:
            success, message = reset_scores(conn, session["admin_id"], reason="Admin reset to 50")
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_reset: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/master_reset", methods=["POST"])
def admin_master_reset():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    form = MasterResetForm(request.form)
    if not form.validate_on_submit():
        logging.error("Master reset form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    password = form.password.data
    try:
        with DatabaseConnection() as conn:
            admin = conn.execute("SELECT * FROM admins WHERE admin_id = 'master'").fetchone()
            if not admin or not check_password_hash(admin["password"], password):
                return jsonify({'success': False, 'message': 'Invalid master password'}), 403
            success, message = master_reset_all(conn)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_master_reset: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/update_admin", methods=["POST"])
def admin_update_admin():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    form = UpdateAdminForm(request.form)
    with DatabaseConnection() as conn:
        admins = conn.execute("SELECT username FROM admins").fetchall()
    form.old_username.choices = [(row["username"], row["username"]) for row in admins]
    if not form.validate_on_submit():
        logging.error("Update admin form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    old_username = form.old_username.data
    new_username = form.new_username.data
    new_password = form.new_password.data
    try:
        with DatabaseConnection() as conn:
            admin = conn.execute("SELECT * FROM admins WHERE username = ?", (old_username,)).fetchone()
            if not admin:
                return jsonify({"success": False, "message": "Admin not found"}), 404
            conn.execute(
                "UPDATE admins SET username = ?, password = ? WHERE username = ?",
                (new_username, generate_password_hash(new_password), old_username)
            )
        return jsonify({"success": True, "message": f"Admin '{old_username}' updated to '{new_username}'"})
    except sqlite3.IntegrityError:
        logging.error("Update admin failed: username '%s' already exists", new_username)
        return jsonify({"success": False, "message": "Username already exists"}), 400
    except Exception as e:
        logging.error(f"Error in admin_update_admin: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/add_rule", methods=["POST"])
def admin_add_rule():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = AddRuleForm(request.form)
    if not form.validate_on_submit():
        logging.error("Add rule form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    description = form.description.data
    points = form.points.data
    details = form.details.data or ""
    try:
        with DatabaseConnection() as conn:
            existing_rule = conn.execute("SELECT 1 FROM incentive_rules WHERE description = ?", (description,)).fetchone()
            if existing_rule:
                return jsonify({"success": False, "message": "Rule already exists"}), 400
            success, message = add_rule(conn, description, points, details)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_add_rule: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/edit_rule", methods=["POST"])
def admin_edit_rule():
    start_time = time.time()
    try:
        form = EditRuleForm()
        logging.debug("Edit rule form data received: %s", {k: v for k, v in request.form.items()})
        if not form.validate_on_submit():
            logging.error("Edit rule form validation failed: %s, form data: %s", form.errors, {k: v for k, v in request.form.items()})
            flash(f"Invalid form data: {form.errors}", "danger")
            return jsonify({"success": False, "message": f"Invalid form data: {form.errors}"}), 400
        with DatabaseConnection() as conn:
            success, message = edit_rule(
                conn,
                form.old_description.data,
                form.new_description.data,
                form.points.data,
                form.details.data or ""
            )
            if not success:
                logging.error("Edit rule failed: %s", message)
                flash(message, "danger")
                return jsonify({"success": False, "message": message}), 400
            conn.commit()
        logging.debug(f"Route /admin/edit_rule took {time.time() - start_time:.2f} seconds")
        flash("Rule updated successfully", "success")
        return jsonify({"success": True, "message": "Rule updated successfully"})
    except Exception as e:
        logging.error(f"Error in admin_edit_rule: {str(e)}\n{traceback.format_exc()}")
        flash(f"Server error: {str(e)}", "danger")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500
    
@app.route("/admin/remove_rule", methods=["POST"])
def admin_remove_rule():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = RemoveRuleForm(request.form)
    logging.debug("Remove rule form data received: %s", {k: v for k, v in request.form.items()})
    if not form.validate_on_submit():
        logging.error("Remove rule form validation failed: %s, form data: %s", form.errors, {k: v for k, v in request.form.items()})
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    description = form.description.data
    try:
        with DatabaseConnection() as conn:
            success, message = remove_rule(conn, description)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_remove_rule: {str(e)}\n{traceback.format_exc()}, form data: %s", {k: v for k, v in request.form.items()})
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/admin/reorder_rules", methods=["POST"])
def admin_reorder_rules():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    order = request.form.getlist("order[]")
    try:
        with DatabaseConnection() as conn:
            success, message = reorder_rules(conn, order)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_reorder_rules: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/add_role", methods=["POST"])
def admin_add_role():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    form = AddRoleForm(request.form)
    logging.debug("Add role form data: %s", dict(request.form))
    if not form.validate_on_submit():
        logging.error("Add role form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    try:
        with DatabaseConnection() as conn:
            roles = get_roles(conn)
            if len(roles) >= 6:
                return jsonify({"success": False, "message": "Maximum of 6 roles reached"}), 400
            role_name = form.role_name.data
            percentage = 0.0 if role_name.lower() == "master" else form.percentage.data
            total_percentage = sum(r["percentage"] for r in roles if r["role_name"].lower() != "master") + percentage
            if total_percentage > 100:
                return jsonify({"success": False, "message": f"Total percentage for non-Master roles cannot exceed 100% (got {total_percentage}%)"}), 400
            success, message = add_role(conn, role_name, percentage)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in add_role: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/edit_role", methods=["POST"])
def admin_edit_role():
    if "admin_id" not in session:
        logging.error("Edit role attempted without admin session")
        return jsonify({"success": False, "message": "Admin access required"}), 403
    form = EditRoleForm(request.form)
    logging.debug("Edit role form data received: %s", {k: v for k, v in request.form.items()})
    if not form.validate_on_submit():
        logging.error("Edit role form validation failed: %s, form data: %s", form.errors, {k: v for k, v in request.form.items()})
        return jsonify({"success": False, "message": "Invalid form data: " + str(form.errors)}), 400
    try:
        old_role_name = form.old_role_name.data
        new_role_name = form.new_role_name.data
        percentage = float(form.percentage.data or 0)  # Handle None case
        with DatabaseConnection() as conn:
            # Check total percentage
            roles = conn.execute("SELECT role_name, percentage FROM roles WHERE role_name != ?", (old_role_name,)).fetchall()
            total_percentage = sum(role["percentage"] for role in roles) + percentage
            if total_percentage > 100:
                logging.error("Total percentage exceeds 100: %s", total_percentage)
                return jsonify({"success": False, "message": f"Total role percentages cannot exceed 100% (got {total_percentage}%)"}), 400
            
            # Verify role exists
            existing_role = conn.execute("SELECT role_name FROM roles WHERE role_name = ?", (old_role_name,)).fetchone()
            if not existing_role:
                logging.error("Role not found: %s", old_role_name)
                return jsonify({"success": False, "message": f"Role {old_role_name} not found"}), 404
            
            # Perform updates in a single transaction
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                "UPDATE roles SET role_name = ?, percentage = ? WHERE role_name = ?",
                (new_role_name, percentage, old_role_name)
            )
            conn.execute(
                "UPDATE employees SET role = ? WHERE role = ?",
                (new_role_name.lower(), old_role_name.lower())
            )
            conn.execute(
                "UPDATE point_decay SET role_name = ? WHERE role_name = ?",
                (new_role_name, old_role_name)
            )
            conn.commit()
            logging.debug("Role updated: old_name=%s, new_name=%s, percentage=%s", old_role_name, new_role_name, percentage)
            return jsonify({"success": True, "message": f"Role {new_role_name} updated"})
    except Exception as e:
        logging.error(f"Error editing role: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500
    
@app.route("/admin/remove_role", methods=["POST"])
def admin_remove_role():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, 'message': "Master account required"}), 403
    form = RemoveRoleForm(request.form)
    if not form.validate_on_submit():
        logging.error("Remove role form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    role_name = form.role_name.data
    try:
        with DatabaseConnection() as conn:
            success, message = remove_role(conn, role_name)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_remove_role: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/toggle_section", methods=["POST"])
def admin_toggle_section():
    if session.get("admin_id") != "master":
        return redirect(url_for("admin"))
    section = request.form.get("section")
    allow = '1' if request.form.get("allow") == 'on' else '0'
    try:
        with DatabaseConnection() as conn:
            set_settings(conn, f"allow_section_{section}", allow)
        flash("Section permissions updated", "success")
    except Exception as e:
        logging.error(f"Error toggling section permission: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
    return redirect(url_for("admin"))

@app.route("/admin/update_pot", methods=["POST"], endpoint="admin_update_pot_endpoint")
def admin_update_pot():
    logging.debug("Registering route: /admin/update_pot")
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = UpdatePotForm(request.form)
    if not form.validate_on_submit():
        logging.error("Update pot form validation failed: %s", form.errors)
        logging.debug("Form data received: %s", dict(request.form))
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    sales_dollars = form.sales_dollars.data
    bonus_percent = form.bonus_percent.data
    try:
        with DatabaseConnection() as conn:
            conn.execute(
                "UPDATE incentive_pot SET sales_dollars = ?, bonus_percent = ? WHERE id = 1",
                (sales_dollars, bonus_percent)
            )
            success = True
            message = "Pot sales and bonus updated"
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_update_pot: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/update_prior_year_sales", methods=["POST"])
def admin_update_prior_year_sales():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    form = UpdatePriorYearSalesForm(request.form)
    logging.debug("Update prior year sales form data: %s", dict(request.form))
    # Handle malformed keys by explicitly checking for prior_year_sales
    prior_year_sales = request.form.get('prior_year_sales')
    if not prior_year_sales:
        logging.error("Update prior year sales: prior_year_sales field missing in form data")
        return jsonify({'success': False, 'message': 'Invalid form data: prior_year_sales is required'}), 400
    form.prior_year_sales.data = int(prior_year_sales)
    if not form.validate_on_submit():
        logging.error("Update prior year sales form validation failed: %s, form data: %s", form.errors, dict(request.form))
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    try:
        with DatabaseConnection() as conn:
            conn.execute(
                "UPDATE incentive_pot SET prior_year_sales = ? WHERE id = 1",
                (form.prior_year_sales.data,)
            )
        logging.debug("Prior year sales updated: %s", form.prior_year_sales.data)
        return jsonify({"success": True, "message": "Prior year sales updated"})
    except Exception as e:
        logging.error(f"Error in update_prior_year_sales: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/set_point_decay", methods=["POST"])
def admin_set_point_decay():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    try:
        with DatabaseConnection() as conn:
            roles = get_roles(conn)
            role_options = [(role["role_name"], role["role_name"]) for role in roles]
        form = SetPointDecayForm(request.form)
        form.role_name.choices = role_options
        if not form.validate_on_submit():
            logging.error("Set point decay form validation failed: %s", form.errors)
            return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
        role_name = form.role_name.data
        points = form.points.data
        days = form.days.data
        logging.debug("Set point decay form data: %s", {k: v if k != 'password' else '****' for k, v in request.form.items()})
        logging.debug("Role choices: %s", form.role_name.choices)
        logging.debug("Days received: %s", days)
        with DatabaseConnection() as conn:
            success, message = set_point_decay(conn, role_name, points, days)
        return jsonify({"success": success, "message": message, "role_name": role_name, "points": points, "days": days})
    except Exception as e:
        logging.error(f"Error in set_point_decay: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@app.route("/admin/delete_feedback", methods=["POST"])
def admin_delete_feedback():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    feedback_id = request.form.get("feedback_id")
    try:
        with DatabaseConnection() as conn:
            success, message = delete_feedback(conn, feedback_id)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_delete_feedback: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/voting_results_popup", methods=["GET"])
def voting_results_popup():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    try:
        with DatabaseConnection() as conn:
            results = get_latest_voting_results(conn)
        return jsonify({"success": True, "results": results})
    except Exception as e:
        logging.error(f"Error in voting_results_popup: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/voting_status", methods=["GET"])
def voting_status():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin access required"}), 403
    try:
        with DatabaseConnection() as conn:
            active_session = conn.execute(
                "SELECT session_id FROM voting_sessions WHERE end_time IS NULL"
            ).fetchone()
            if not active_session:
                return jsonify({"success": True, "status": []})
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vote_participants (
                    session_id INTEGER,
                    voter_initials TEXT,
                    PRIMARY KEY (session_id, voter_initials),
                    FOREIGN KEY(session_id) REFERENCES voting_sessions(session_id)
                )
                """
            )
            voted_initials = set(
                row["voter_initials"].lower()
                for row in conn.execute(
                    "SELECT voter_initials FROM vote_participants WHERE session_id = ?",
                    (active_session["session_id"],),
                ).fetchall()
            )
            active_emps = conn.execute(
                "SELECT initials FROM employees WHERE active = 1 AND LOWER(role) != 'master'"
            ).fetchall()
            status = [
                {"initials": emp["initials"], "voted": emp["initials"].lower() in voted_initials}
                for emp in active_emps
            ]
            status.sort(key=lambda x: x["voted"])
        response = jsonify({"success": True, "status": status})
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    except Exception as e:
        logging.error(f"Error in voting_status: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/history", methods=["GET"])
def history():
    start_date = request.args.get("start_date") or None
    end_date = request.args.get("end_date") or None
    employee_id = request.args.get("employee_id") or None
    try:
        with DatabaseConnection() as conn:
            history = [dict(row) for row in get_history(
                conn,
                employee_id=employee_id,
                start_date=start_date if start_date and end_date else None,
                end_date=end_date if start_date and end_date else None,
            )]
            employees = conn.execute(
                "SELECT employee_id, name FROM employees ORDER BY name"
            ).fetchall()
            employee_options = [('', 'All Employees')] + [
                (str(e["employee_id"]), e["name"]) for e in employees
            ]
        logging.debug(
            f"Rendering history.html: history_count={len(history)}, employee_count={len(employee_options)}"
        )
        return render_template(
            "history.html",
            history=history,
            employees=employee_options,
            is_admin=bool(session.get("admin_id")),
            import_time=int(time.time()),
            start_date=start_date,
            end_date=end_date,
            selected_employee=employee_id,
        )
    except Exception as e:
        logging.error(f"Error in history: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('show_incentive'))


@app.route("/export_payout", methods=["GET"])
def export_payout():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    if not start_date or not end_date:
        flash("Start and end dates are required", "danger")
        return redirect(url_for('admin'))
    try:
        with DatabaseConnection() as conn:
            history = [dict(row) for row in get_history(conn, start_date=start_date, end_date=end_date)]
            pot_info = get_pot_info(conn)
            employees = conn.execute("SELECT employee_id, name, role FROM employees WHERE active = 1").fetchall()
            df = pd.DataFrame(history)
            grouped = {}
            if not df.empty:
                grouped = {emp_id: group for emp_id, group in df.groupby('employee_id')}
            output_lines = []
            for emp in employees:
                employee_id = emp['employee_id']
                name = emp['name']
                role = emp['role'].lower().replace(" ", "_")
                group = grouped.get(employee_id)
                total_points = group['points'].sum() if group is not None else 0
                point_value = pot_info.get(f"{role}_point_value", 0.0)
                total_dollars = total_points * point_value if total_points > 0 and total_points >= 50 else 0.0
                output_lines.append(f"Employee: {name}")
                output_lines.append("Employee ID,Name,Role,Total Points,Total Dollars")
                output_lines.append(f"{employee_id},{name},{role},{total_points},{total_dollars:.2f}")
                output_lines.append("")
                output_lines.append("Date,Reason,Points,Dollar Value,Changed By,Notes")
                if group is not None:
                    for _, row in group.iterrows():
                        dollar_value = row['points'] * point_value if row['points'] > 0 else 0.0
                        notes = row.get('notes', '')
                        output_lines.append(f"{row['date']},\"{row['reason']}\",{row['points']},{dollar_value:.2f},{row['changed_by']},\"{notes}\"")
                output_lines.append("")
            output = io.BytesIO()
            output.write("\n".join(output_lines).encode())
            output.seek(0)
        filename = f"payout_{start_date}_to_{end_date}.csv"
        return send_file(output, mimetype='text/csv', as_attachment=True, download_name=filename)
    except Exception as e:
        logging.error(f"Error in export_payout: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('admin'))

@app.route("/admin/export_data/<format>", methods=["GET"])
def admin_export_data(format):
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    
    try:
        with DatabaseConnection() as conn:
            current_date = datetime.now()
            
            if format == "all":
                # Export all historical data
                history = [dict(row) for row in get_history(conn)]
                filename = f"all_data_{current_date.strftime('%Y%m%d')}.csv"
                
            elif format == "month":
                # Export current month data
                start_date = current_date.replace(day=1).strftime('%Y-%m-%d')
                end_date = current_date.strftime('%Y-%m-%d')
                history = [dict(row) for row in get_history(conn, start_date=start_date, end_date=end_date)]
                filename = f"month_data_{current_date.strftime('%Y%m')}.csv"
                
            elif format == "payouts":
                # Export payout data for current month
                start_date = current_date.replace(day=1).strftime('%Y-%m-%d')
                end_date = current_date.strftime('%Y-%m-%d')
                return redirect(url_for('export_payout', start_date=start_date, end_date=end_date))
                
            else:
                flash("Invalid export format", "danger")
                return redirect(url_for('admin'))
            
            # Create CSV for all/month formats
            if not history:
                flash("No data found for the specified period", "warning")
                return redirect(url_for('admin'))
            
            df = pd.DataFrame(history)
            output = io.BytesIO()
            df.to_csv(output, index=False)
            output.seek(0)
            
            return send_file(output, mimetype='text/csv', as_attachment=True, download_name=filename)
            
    except Exception as e:
        logging.error(f"Error in admin_export_data: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('admin'))

@app.route("/history_chart", methods=["GET"])
def history_chart():
    employee_id = request.args.get("employee_id") or None
    start_date = request.args.get("start_date") or None
    end_date = request.args.get("end_date") or None
    try:
        with DatabaseConnection() as conn:
            history = [
                dict(row)
                for row in get_history(
                    conn,
                    employee_id=employee_id,
                    start_date=start_date if start_date and end_date else None,
                    end_date=end_date if start_date and end_date else None,
                )
            ]
        if not history:
            fig, ax = plt.subplots(figsize=(5, 3))
            ax.text(0.5, 0.5, "No Data", ha="center", va="center")
            ax.axis("off")
            output = io.BytesIO()
            fig.savefig(output, format="png")
            plt.close(fig)
            output.seek(0)
            return send_file(output, mimetype="image/png")
        df = pd.DataFrame(history)
        df["date"] = pd.to_datetime(df["date"], format="mixed")
        df.sort_values("date", inplace=True)
        df["cumulative_points"] = df["points"].cumsum()
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df["date"], df["cumulative_points"])
        ax.set_xlabel("Date")
        ax.set_ylabel("Cumulative Points")
        emp_name = df.iloc[0]["name"]
        ax.set_title(f"{emp_name} Points Over Time")
        ax.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        output = io.BytesIO()
        fig.savefig(output, format="png")
        plt.close(fig)
        output.seek(0)
        return send_file(output, mimetype="image/png")
    except Exception as e:
        logging.error(f"Error in history_chart: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/mark_feedback_read", methods=["POST"])
def admin_mark_feedback_read():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    feedback_id = request.form.get("feedback_id")
    try:
        with DatabaseConnection() as conn:
            success, message = mark_feedback_read(conn, feedback_id)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_mark_feedback_read: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    form = FeedbackForm(request.form)
    if not form.validate_on_submit():
        logging.error("Feedback form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    comment = form.comment.data
    submitter = form.initials.data if "admin_id" not in session else session["admin_id"]
    try:
        with DatabaseConnection() as conn:
            success, message = add_feedback(conn, comment, submitter)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in submit_feedback: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/settings", methods=["GET", "POST"])
def admin_settings():
    logging.debug(f"Admin settings access attempt. Session: {dict(session)}")
    logging.debug(f"Session admin_id: {session.get('admin_id')}")
    if "admin_id" not in session or session.get("admin_id") != "master":
        logging.debug(f"Settings access denied. admin_id in session: {'admin_id' in session}, session admin_id: {session.get('admin_id')}")
        flash("Master admin required", "danger")
        return redirect(url_for('admin'))
    if request.method == "POST":
        if 'port' in request.form:
            form = PortForm(request.form)
            if not form.validate_on_submit():
                flash("Invalid port", "danger")
                return redirect(url_for('admin_settings'))
            try:
                with DatabaseConnection() as conn:
                    set_settings(conn, 'port', str(form.port.data))
                try:
                    service_file = f"/etc/systemd/system/{Config.SERVICE_NAME}"
                    try:
                        subprocess.run([
                            "sudo", "bash", "-c",
                            f"sed -i 's/--bind 0\\.0\\.0\\.0:[0-9]\\+/--bind 0.0.0.0:{form.port.data}/' {service_file}"
                        ], check=True)
                        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
                    except Exception as e:
                        logging.warning(f"Failed to update service file port: {str(e)}\n{traceback.format_exc()}")
                    subprocess.run(["sudo", "systemctl", "restart", Config.SERVICE_NAME], check=True)
                    flash('Port updated and service restarted', 'success')
                except Exception as e:
                    logging.error(f"Service restart failed after port update: {str(e)}\n{traceback.format_exc()}")
                    flash('Port updated but failed to restart service', 'warning')
                return redirect(url_for('admin_settings'))
            except Exception as e:
                logging.error(f"Error updating port: {str(e)}\n{traceback.format_exc()}")
                flash('Server error updating port', 'danger')
                return redirect(url_for('admin_settings'))
        elif 'pos_threshold_1' in request.form:  # Handle VotingThresholdsForm
            form = VotingThresholdsForm(request.form)
            if not form.validate_on_submit():
                logging.error("Voting thresholds form validation failed: %s", form.errors)
                flash("Invalid voting thresholds data: " + str(form.errors), "danger")
                return redirect(url_for('admin_settings'))
            thresholds = {
                "positive": [
                    {"threshold": form.pos_threshold_1.data, "points": form.pos_points_1.data},
                    {"threshold": form.pos_threshold_2.data, "points": form.pos_points_2.data},
                    {"threshold": form.pos_threshold_3.data, "points": form.pos_points_3.data}
                ],
                "negative": [
                    {"threshold": form.neg_threshold_1.data, "points": form.neg_points_1.data},
                    {"threshold": form.neg_threshold_2.data, "points": form.neg_points_2.data},
                    {"threshold": form.neg_threshold_3.data, "points": form.neg_points_3.data}
                ]
            }
            try:
                with DatabaseConnection() as conn:
                    success, message = set_settings(conn, 'voting_thresholds', json.dumps(thresholds))
                flash(message, "success")
                return redirect(url_for('admin_settings'))
            except Exception as e:
                logging.error(f"Error updating voting thresholds: {str(e)}\n{traceback.format_exc()}")
                flash("Server error updating voting thresholds", "danger")
                return redirect(url_for('admin_settings'))
        elif 'max_total_votes' in request.form:  # Handle vote limits form
            form = VoteLimitsForm(request.form)
            if not form.validate_on_submit():
                logging.error("Vote limits form validation failed: %s", form.errors)
                flash("Invalid vote limits data: " + str(form.errors), "danger")
                return redirect(url_for('admin_settings'))
            try:
                with DatabaseConnection() as conn:
                    set_settings(conn, 'max_total_votes', str(form.max_total_votes.data))
                    set_settings(conn, 'max_plus_votes', str(form.max_plus_votes.data))
                    set_settings(conn, 'max_minus_votes', str(form.max_minus_votes.data))
                flash('Vote limits updated', 'success')
                return redirect(url_for('admin_settings'))
            except Exception as e:
                logging.error(f"Error updating vote limits: {str(e)}\n{traceback.format_exc()}")
                flash("Server error updating vote limits", "danger")
                return redirect(url_for('admin_settings'))
        elif 'money_threshold' in request.form:  # Handle scoreboard settings form
            form = ScoreboardSettingsForm(request.form)
            if not form.validate_on_submit():
                logging.error("Scoreboard settings form validation failed: %s", form.errors)
                flash("Invalid scoreboard settings data: " + str(form.errors), "danger")
                return redirect(url_for('admin_settings'))
            try:
                with DatabaseConnection() as conn:
                    set_settings(conn, 'money_threshold', str(form.money_threshold.data))
                    set_settings(conn, 'score_top_color', form.top_color.data)
                    set_settings(conn, 'score_mid_color', form.mid_color.data)
                    set_settings(conn, 'score_bottom_color', form.bottom_color.data)
                    set_settings(conn, 'reel_color', form.reel_color.data)
                    set_settings(conn, 'scoreboard_spin_duration', str(form.spin_duration.data))
                    set_settings(conn, 'scoreboard_spin_iterations', str(form.spin_iterations.data))
                    set_settings(conn, 'scoreboard_spin_pause', str(form.spin_pause.data))
                    set_settings(conn, 'scoreboard_spin_delay', str(form.spin_delay.data))
                    set_settings(conn, 'scoreboard_refresh_interval', str(form.refresh_interval.data))
                flash('Scoreboard settings updated', 'success')
                return redirect(url_for('admin_settings'))
            except Exception as e:
                logging.error(f"Error updating scoreboard settings: {str(e)}\n{traceback.format_exc()}")
                flash('Server error updating scoreboard settings', 'danger')
                return redirect(url_for('admin_settings'))
        elif 'month_mode' in request.form:  # Handle reporting settings form
            month_mode = request.form.get('month_mode')
            week_start_day = request.form.get('week_start_day')
            auto_vote_day = request.form.get('auto_vote_day')
            try:
                with DatabaseConnection() as conn:
                    set_settings(conn, 'month_mode', month_mode)
                    set_settings(conn, 'week_start_day', week_start_day)
                    set_settings(conn, 'auto_vote_day', auto_vote_day)
                flash('Reporting settings updated', 'success')
                return redirect(url_for('admin_settings'))
            except Exception as e:
                logging.error(f"Error updating reporting settings: {str(e)}\n{traceback.format_exc()}")
                flash("Server error updating reporting settings", "danger")
                return redirect(url_for('admin_settings'))
        elif any(key.startswith('role_weight_') for key in request.form.keys()):
            try:
                with DatabaseConnection() as conn:
                    roles = [row['role_name'] for row in conn.execute('SELECT role_name FROM roles').fetchall()]
                    weights = {}
                    for role in roles:
                        field = f'role_weight_{role}'
                        weight_str = request.form.get(field)
                        try:
                            weight = float(weight_str)
                        except (TypeError, ValueError):
                            flash(f"Invalid weight for role {role}", 'danger')
                            return redirect(url_for('admin_settings'))
                        weights[role] = weight
                    set_settings(conn, 'role_vote_weights', json.dumps(weights))
                flash('Role vote weights updated', 'success')
                return redirect(url_for('admin_settings'))
            except Exception as e:
                logging.error(f"Error updating role vote weights: {str(e)}\n{traceback.format_exc()}")
                flash('Server error updating role vote weights', 'danger')
                return redirect(url_for('admin_settings'))
        elif 'theme_settings' in request.form:
            try:
                with DatabaseConnection() as conn:
                    set_settings(conn, 'site_name', request.form.get('site_name', ''))
                    set_settings(conn, 'site_title', request.form.get('site_title', ''))
                    set_settings(conn, 'primary_color', request.form.get('primary_color', '#D4AF37'))
                    set_settings(conn, 'secondary_color', request.form.get('secondary_color', '#000000'))
                    set_settings(conn, 'background_color', request.form.get('background_color', '#3A3A3A'))
                    set_settings(conn, 'surface_color', request.form.get('surface_color', '#222222'))
                    set_settings(conn, 'surface_alt_color', request.form.get('surface_alt_color', '#1A1A1A'))
                    set_settings(conn, 'banner_text', request.form.get('banner_text', "JACKPOT TIME! GIVE 'EM THE MONEY! SLOTS SPINNING - WINNERS GRINNING!"))
                    set_settings(conn, 'strobe_mode', 'on' if request.form.get('strobe_mode') == 'on' else 'off')
                flash('Theme settings updated', 'success')
                return redirect(url_for('admin_settings'))
            except Exception as e:
                logging.error(f"Error updating theme settings: {str(e)}\n{traceback.format_exc()}")
                flash('Server error updating theme settings', 'danger')
                return redirect(url_for('admin_settings'))
        elif 'mini_game_settings' in request.form:  # Handle mini-game settings form
            try:
                with DatabaseConnection() as conn:
                    # Build mini-game config JSON from form data
                    mini_game_config = {
                        "award_chance_points": int(request.form.get('award_chance_points', 10)),
                        "award_chance_vote": int(request.form.get('award_chance_vote', 15)),
                        "prizes": {
                            "points": {
                                "amount": int(request.form.get('points_prize_amount', 5)),
                                "chance": int(request.form.get('points_prize_chance', 20))
                            },
                            "prize1": {
                                "desc": "Gift Card",
                                "value": int(request.form.get('gift_card_value', 25)),
                                "chance": int(request.form.get('gift_card_chance', 10))
                            },
                            "prize2": {
                                "desc": request.form.get('prize2_desc', 'Extra Break'),
                                "value": 0,
                                "chance": int(request.form.get('prize2_chance', 30))
                            },
                            "prize3": {
                                "desc": request.form.get('prize3_desc', 'Company Swag'),
                                "value": int(request.form.get('prize3_value', 10)),
                                "chance": int(request.form.get('prize3_chance', 5))
                            }
                        },
                        "game_types": ["slot", "scratch", "roulette"]
                    }
                    set_settings(conn, 'mini_game_settings', json.dumps(mini_game_config))
                flash('Mini-game settings updated', 'success')
                return redirect(url_for('admin_settings'))
            except Exception as e:
                logging.error(f"Error updating mini-game settings: {str(e)}\n{traceback.format_exc()}")
                flash('Server error updating mini-game settings', 'danger')
                return redirect(url_for('admin_settings'))
        elif 'system_settings' in request.form:  # Handle system settings form
            try:
                with DatabaseConnection() as conn:
                    set_settings(conn, 'program_end_date', request.form.get('program_end_date', ''))
                    set_settings(conn, 'sound_on', '1' if request.form.get('sound_on') == '1' else '0')
                    set_settings(conn, 'allow_section_rules', '1' if request.form.get('allow_section_rules') == '1' else '0')
                    set_settings(conn, 'allow_section_manage_roles', '1' if request.form.get('allow_section_manage_roles') == '1' else '0')
                flash('System settings updated', 'success')
                return redirect(url_for('admin_settings'))
            except Exception as e:
                logging.error(f"Error updating system settings: {str(e)}\n{traceback.format_exc()}")
                flash('Server error updating system settings', 'danger')
                return redirect(url_for('admin_settings'))
        else:  # Handle generic settings form
            key = request.form.get("key")
            value = request.form.get("value")
            if not key or not value:
                flash("Key and value are required", "danger")
                return redirect(url_for('admin_settings'))
            try:
                with DatabaseConnection() as conn:
                    success, message = set_settings(conn, key, value)
                flash(message, "success")
                return redirect(url_for('admin_settings'))
            except Exception as e:
                logging.error(f"Error updating settings: {str(e)}\n{traceback.format_exc()}")
                flash("Server error updating settings", "danger")
                return redirect(url_for('admin_settings'))

    try:
        with DatabaseConnection() as conn:
            settings = get_settings(conn)
            logging.debug("Rendering settings.html")
            form = VotingThresholdsForm()
            thresholds_data = json.loads(settings.get('voting_thresholds', '{"positive":[{"threshold":90,"points":10},{"threshold":60,"points":5},{"threshold":25,"points":2}],"negative":[{"threshold":90,"points":-10},{"threshold":60,"points":-5},{"threshold":25,"points":-2}]}'))
            form.pos_threshold_1.data = thresholds_data['positive'][0]['threshold']
            form.pos_points_1.data = thresholds_data['positive'][0]['points']
            form.pos_threshold_2.data = thresholds_data['positive'][1]['threshold']
            form.pos_points_2.data = thresholds_data['positive'][1]['points']
            form.pos_threshold_3.data = thresholds_data['positive'][2]['threshold']
            form.pos_points_3.data = thresholds_data['positive'][2]['points']
            form.neg_threshold_1.data = thresholds_data['negative'][0]['threshold']
            form.neg_points_1.data = thresholds_data['negative'][0]['points']
            form.neg_threshold_2.data = thresholds_data['negative'][1]['threshold']
            form.neg_points_2.data = thresholds_data['negative'][1]['points']
            form.neg_threshold_3.data = thresholds_data['negative'][2]['threshold']
            form.neg_points_3.data = thresholds_data['negative'][2]['points']
            vote_limits_form = VoteLimitsForm()
            vote_limits_form.max_total_votes.data = int(settings.get('max_total_votes', 3))
            vote_limits_form.max_plus_votes.data = int(settings.get('max_plus_votes', 2))
            vote_limits_form.max_minus_votes.data = int(settings.get('max_minus_votes', 3))
            scoreboard_form = ScoreboardSettingsForm()
            scoreboard_form.money_threshold.data = int(settings.get('money_threshold', 50))
            scoreboard_form.top_color.data = settings.get('score_top_color', '#D4AF37')
            scoreboard_form.mid_color.data = settings.get('score_mid_color', '#FFFFFF')
            scoreboard_form.bottom_color.data = settings.get('score_bottom_color', '#FF6347')
            scoreboard_form.reel_color.data = settings.get('reel_color', '#FFD700')
            scoreboard_form.spin_duration.data = int(settings.get('scoreboard_spin_duration', 10))
            scoreboard_form.spin_iterations.data = int(settings.get('scoreboard_spin_iterations', 0))
            scoreboard_form.spin_pause.data = int(settings.get('scoreboard_spin_pause', 0))
            scoreboard_form.spin_delay.data = int(settings.get('scoreboard_spin_delay', 0))
            scoreboard_form.refresh_interval.data = int(settings.get('scoreboard_refresh_interval', 60))
            roles = [row['role_name'] for row in conn.execute('SELECT role_name FROM roles').fetchall()]
            try:
                role_weights = json.loads(settings.get('role_vote_weights', '{}'))
            except json.JSONDecodeError:
                role_weights = {}
            if not role_weights:
                for role in roles:
                    if role.lower() == 'supervisor':
                        role_weights[role] = 2.0
                    elif role.lower() == 'master':
                        role_weights[role] = 3.0
                    else:
                        role_weights[role] = 1.0
                set_settings(conn, 'role_vote_weights', json.dumps(role_weights))
            master_reset_form = MasterResetForm()
            port_form = PortForm()
            port_form.port.data = int(settings.get('port', 8101))
            restart_service_form = RestartServiceForm()
            reboot_pi_form = RebootPiForm()
            
            # Parse mini-game settings for template
            mini_game_config = {}
            try:
                mini_game_config = json.loads(settings.get('mini_game_settings', '{}'))
            except json.JSONDecodeError:
                mini_game_config = {}

        return render_template(
            "settings.html",
            settings=settings,
            is_master=session.get("admin_id") == "master",
            import_time=int(time.time()),
            admin_page=True,
            form=form,
            thresholds_form=form,
            vote_limits_form=vote_limits_form,
            scoreboard_form=scoreboard_form,
            master_reset_form=master_reset_form,
            port_form=port_form,
            restart_service_form=restart_service_form,
            reboot_pi_form=reboot_pi_form,
            month_mode=settings.get('month_mode', 'calendar'),
            week_start_day=settings.get('week_start_day', 'Monday'),
            auto_vote_day=settings.get('auto_vote_day', ''),
            roles=roles,
            role_weights=role_weights,
            mini_game_config=mini_game_config,
        )
    except Exception as e:
        logging.error(f"Error in admin_settings GET: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('admin'))


@app.route("/admin/restart_service", methods=["POST"])
def admin_restart_service():
    if "admin_id" not in session or session.get("admin_id") != "master":
        flash("Master admin required", "danger")
        return redirect(url_for('admin'))
    form = RestartServiceForm()
    if form.validate_on_submit():
        try:
            subprocess.run(["sudo", "systemctl", "restart", Config.SERVICE_NAME], check=True)
            flash("Service restart initiated", "success")
        except Exception as e:
            logging.error(f"Service restart failed: {str(e)}\n{traceback.format_exc()}")
            flash("Failed to restart service", "danger")
    return redirect(url_for('admin_settings'))


@app.route("/admin/reboot_pi", methods=["POST"])
def admin_reboot_pi():
    if "admin_id" not in session or session.get("admin_id") != "master":
        flash("Master admin required", "danger")
        return redirect(url_for('admin'))
    form = RebootPiForm()
    if form.validate_on_submit():
        try:
            subprocess.run(["sudo", "reboot"], check=True)
            flash("Rebooting", "success")
        except Exception as e:
            logging.error(f"Reboot failed: {str(e)}\n{traceback.format_exc()}")
            flash("Failed to reboot", "danger")
    return redirect(url_for('admin_settings'))


@app.route("/admin/start_voting_session", methods=["POST"])
def admin_start_voting_session():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    
    try:
        with DatabaseConnection() as conn:
            success, message = start_voting_session(conn, session["admin_id"])
            return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_start_voting_session: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500


@app.route("/admin/end_voting_session", methods=["POST"])
def admin_end_voting_session():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    
    try:
        with DatabaseConnection() as conn:
            success, message = close_voting_session(conn)
            return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_end_voting_session: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500


@app.route("/admin/game_details/<int:game_id>", methods=["GET"])
def admin_game_details(game_id):
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    
    try:
        with DatabaseConnection() as conn:
            game = conn.execute("""
                SELECT mg.id, mg.game_type, mg.status, mg.outcome, mg.awarded_date, mg.played_date,
                       e.name as employee_name
                FROM mini_games mg 
                LEFT JOIN employees e ON mg.employee_id = e.employee_id 
                WHERE mg.id = ?
            """, (game_id,)).fetchone()
            
            if game:
                return jsonify({
                    "success": True,
                    "game": {
                        "id": game["id"],
                        "game_type": game["game_type"],
                        "status": game["status"],
                        "outcome": game["outcome"],
                        "awarded_date": game["awarded_date"],
                        "played_date": game["played_date"],
                        "employee_name": game["employee_name"]
                    }
                })
            else:
                return jsonify({"success": False, "message": "Game not found"}), 404
                
    except Exception as e:
        logging.error(f"Error in admin_game_details: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500


@app.route("/admin/get_employee/<employee_id>", methods=["GET"])
def admin_get_employee(employee_id):
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    
    try:
        with DatabaseConnection() as conn:
            employee = conn.execute("SELECT employee_id, name, initials, role FROM employees WHERE employee_id = ?", 
                                  (employee_id,)).fetchone()
            
            if employee:
                return jsonify({
                    "success": True,
                    "employee": {
                        "employee_id": employee["employee_id"],
                        "name": employee["name"], 
                        "initials": employee["initials"],
                        "role": employee["role"]
                    }
                })
            else:
                return jsonify({"success": False, "message": "Employee not found"}), 404
                
    except Exception as e:
        logging.error(f"Error in admin_get_employee: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500


@app.route("/admin/get_rule/<int:rule_id>", methods=["GET"])
def admin_get_rule(rule_id):
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    
    try:
        with DatabaseConnection() as conn:
            rule = conn.execute("SELECT rule_id, description, points, details FROM rules WHERE rule_id = ?", 
                              (rule_id,)).fetchone()
            
            if rule:
                return jsonify({
                    "success": True,
                    "rule": {
                        "rule_id": rule["rule_id"],
                        "description": rule["description"],
                        "points": rule["points"],
                        "details": rule["details"] or ""
                    }
                })
            else:
                return jsonify({"success": False, "message": "Rule not found"}), 404
                
    except Exception as e:
        logging.error(f"Error in admin_get_rule: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500


@app.route("/admin/export_csv/<table_name>", methods=["GET"])
def admin_export_csv(table_name):
    """Export database table to CSV"""
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    
    # Define allowed tables and their columns
    allowed_tables = {
        'employees': ['employee_id', 'name', 'initials', 'score', 'role', 'active'],
        'votes': ['vote_id', 'voter_initials', 'recipient_id', 'vote_value', 'vote_date'],
        'score_history': ['history_id', 'employee_id', 'name', 'points', 'reason', 'date', 'admin_id'],
        'voting_sessions': ['session_id', 'start_time', 'end_time', 'status', 'total_participants'],
        'incentive_rules': ['rule_id', 'description', 'points', 'details', 'order_index'],
        'roles': ['role_id', 'role_name', 'description'],
        'mini_games': ['id', 'employee_id', 'game_type', 'outcome', 'awarded_date', 'played_date', 'status'],
        'feedback': ['feedback_id', 'employee_id', 'message', 'created_at', 'read_status', 'admin_response']
    }
    
    if table_name not in allowed_tables:
        return jsonify({"success": False, "message": "Invalid table name"}), 400
    
    try:
        with DatabaseConnection() as conn:
            # Get table data
            columns = allowed_tables[table_name]
            column_str = ', '.join(columns)
            
            # Handle different table names (some have different actual table names)
            actual_table_name = table_name
            if table_name == 'incentive_rules':
                actual_table_name = 'rules'
            
            cursor = conn.execute(f"SELECT {column_str} FROM {actual_table_name} ORDER BY 1")
            rows = cursor.fetchall()
            
            if not rows:
                flash(f"No data found in {table_name}", "warning")
                return redirect(url_for('admin'))
            
            # Convert to DataFrame
            data = []
            for row in rows:
                data.append(dict(row))
            
            df = pd.DataFrame(data)
            
            # Create CSV output
            output = io.BytesIO()
            df.to_csv(output, index=False)
            output.seek(0)
            
            filename = f"{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            return send_file(
                output, 
                mimetype='text/csv', 
                as_attachment=True, 
                download_name=filename
            )
            
    except Exception as e:
        logging.error(f"Error in admin_export_csv: {str(e)}\n{traceback.format_exc()}")
        flash("Export failed", "danger")
        return redirect(url_for('admin'))


@app.route("/admin/import_database_dump", methods=["POST"])
def admin_import_database_dump():
    """Import multi-table database dump from old program"""
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    
    try:
        if 'dump_file' not in request.files:
            return jsonify({"success": False, "message": "No file provided"}), 400
        
        file = request.files['dump_file']
        import_mode = request.form.get('dump_import_mode', 'merge')  # 'merge' or 'replace'
        
        if file.filename == '':
            return jsonify({"success": False, "message": "No file selected"}), 400
        
        # Read the dump file
        try:
            content = file.read().decode('utf-8')
        except Exception as e:
            return jsonify({"success": False, "message": f"Error reading file: {str(e)}"}), 400
        
        # Parse multi-table dump format
        tables_data = {}
        current_table = None
        current_data = []
        
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('# TABLE:'):
                # Save previous table data
                if current_table and current_data:
                    # First line should be headers, rest should be data
                    if len(current_data) > 1:
                        headers = current_data[0].split(',')
                        data_rows = []
                        for data_line in current_data[1:]:
                            if data_line.strip():  # Skip empty lines
                                data_rows.append(data_line.split(','))
                        tables_data[current_table] = {'headers': headers, 'rows': data_rows}
                
                # Start new table
                current_table = line.replace('# TABLE:', '').strip()
                current_data = []
            else:
                # Add data line
                if current_table:
                    current_data.append(line)
        
        # Don't forget the last table
        if current_table and current_data:
            if len(current_data) > 1:
                headers = current_data[0].split(',')
                data_rows = []
                for data_line in current_data[1:]:
                    if data_line.strip():
                        data_rows.append(data_line.split(','))
                tables_data[current_table] = {'headers': headers, 'rows': data_rows}
        
        if not tables_data:
            return jsonify({"success": False, "message": "No valid table data found in dump file"}), 400
        
        # Import each table
        import_results = {}
        total_success = 0
        total_errors = 0
        
        with DatabaseConnection() as conn:
            # If replace mode, clear existing data (only for master admin)
            if import_mode == 'replace' and session.get("admin_id") == "master":
                # Clear tables in reverse dependency order
                clear_tables = ['votes', 'score_history', 'voting_sessions', 'employees', 'incentive_rules', 'roles']
                for table in clear_tables:
                    if table in tables_data:
                        actual_table = 'rules' if table == 'incentive_rules' else table
                        try:
                            conn.execute(f"DELETE FROM {actual_table}")
                            logging.info(f"Cleared table {actual_table}")
                        except Exception as e:
                            logging.warning(f"Could not clear table {actual_table}: {e}")
            
            # Import tables in dependency order
            table_order = ['roles', 'employees', 'incentive_rules', 'voting_sessions', 'votes', 'score_history', 'settings']
            
            for table_name in table_order:
                if table_name not in tables_data:
                    continue
                    
                table_data = tables_data[table_name]
                headers = table_data['headers']
                rows = table_data['rows']
                
                success_count = 0
                error_count = 0
                errors = []
                
                for row_idx, row in enumerate(rows):
                    try:
                        # Clean row data (handle quoted values and empty fields)
                        clean_row = []
                        for cell in row:
                            cell = cell.strip()
                            if cell.startswith('"') and cell.endswith('"'):
                                cell = cell[1:-1]  # Remove quotes
                            clean_row.append(cell if cell else None)
                        
                        if table_name == 'employees':
                            if len(clean_row) >= 3:  # Need at least employee_id, name, initials
                                employee_id = clean_row[0]
                                name = clean_row[1]
                                initials = clean_row[2]
                                score = int(clean_row[3]) if len(clean_row) > 3 and clean_row[3] else 50
                                role = clean_row[4] if len(clean_row) > 4 and clean_row[4] else None
                                active = int(clean_row[5]) if len(clean_row) > 5 and clean_row[5] else 1
                                
                                # Check if employee exists
                                existing = conn.execute("SELECT employee_id FROM employees WHERE employee_id = ?", (employee_id,)).fetchone()
                                
                                if existing and import_mode == 'merge':
                                    # Update existing employee
                                    conn.execute("""
                                        UPDATE employees 
                                        SET name=?, initials=?, score=?, role=?, active=?
                                        WHERE employee_id=?
                                    """, (name, initials, score, role, active, employee_id))
                                elif not existing:
                                    # Insert new employee
                                    conn.execute("""
                                        INSERT INTO employees (employee_id, name, initials, score, role, active)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    """, (employee_id, name, initials, score, role, active))
                                
                        elif table_name == 'incentive_rules':
                            if len(clean_row) >= 2:  # Need at least description and points
                                rule_id = int(clean_row[0]) if clean_row[0] else None
                                description = clean_row[1]
                                points = int(clean_row[2]) if len(clean_row) > 2 and clean_row[2] else 0
                                details = clean_row[3] if len(clean_row) > 3 and clean_row[3] else None
                                order_index = int(clean_row[4]) if len(clean_row) > 4 and clean_row[4] else 0
                                
                                if rule_id:
                                    # Try to update existing rule first
                                    existing = conn.execute("SELECT rule_id FROM rules WHERE rule_id = ?", (rule_id,)).fetchone()
                                    if existing and import_mode == 'merge':
                                        conn.execute("""
                                            UPDATE rules 
                                            SET description=?, points=?, details=?, order_index=?
                                            WHERE rule_id=?
                                        """, (description, points, details, order_index, rule_id))
                                    elif not existing:
                                        conn.execute("""
                                            INSERT INTO rules (rule_id, description, points, details, order_index)
                                            VALUES (?, ?, ?, ?, ?)
                                        """, (rule_id, description, points, details, order_index))
                                else:
                                    # Insert without rule_id (auto-increment)
                                    conn.execute("""
                                        INSERT INTO rules (description, points, details, order_index)
                                        VALUES (?, ?, ?, ?)
                                    """, (description, points, details, order_index))
                        
                        elif table_name == 'roles':
                            if len(clean_row) >= 1:
                                role_id = int(clean_row[0]) if clean_row[0] else None
                                role_name = clean_row[1] if len(clean_row) > 1 else clean_row[0]
                                description = clean_row[2] if len(clean_row) > 2 and clean_row[2] else None
                                
                                if role_id:
                                    # Try to update existing role first
                                    existing = conn.execute("SELECT role_id FROM roles WHERE role_id = ?", (role_id,)).fetchone()
                                    if existing and import_mode == 'merge':
                                        conn.execute("""
                                            UPDATE roles SET role_name=?, description=? WHERE role_id=?
                                        """, (role_name, description, role_id))
                                    elif not existing:
                                        conn.execute("""
                                            INSERT INTO roles (role_id, role_name, description) VALUES (?, ?, ?)
                                        """, (role_id, role_name, description))
                                else:
                                    # Insert without role_id (auto-increment)
                                    conn.execute("""
                                        INSERT INTO roles (role_name, description) VALUES (?, ?)
                                    """, (role_name, description))
                        
                        elif table_name == 'votes':
                            if len(clean_row) >= 4:
                                vote_id = int(clean_row[0]) if clean_row[0] else None
                                voter_initials = clean_row[1]
                                recipient_id = clean_row[2]  
                                vote_value = int(clean_row[3]) if clean_row[3] else 0
                                vote_date = clean_row[4] if len(clean_row) > 4 and clean_row[4] else None
                                
                                # Only insert if not exists (votes are unique by voter, recipient, date)
                                if vote_date and voter_initials and recipient_id:
                                    existing = conn.execute("""
                                        SELECT vote_id FROM votes 
                                        WHERE voter_initials=? AND recipient_id=? AND vote_date=?
                                    """, (voter_initials, recipient_id, vote_date)).fetchone()
                                    
                                    if not existing:
                                        conn.execute("""
                                            INSERT INTO votes (voter_initials, recipient_id, vote_value, vote_date)
                                            VALUES (?, ?, ?, ?)
                                        """, (voter_initials, recipient_id, vote_value, vote_date))
                        
                        elif table_name == 'score_history':
                            if len(clean_row) >= 4:
                                history_id = int(clean_row[0]) if clean_row[0] else None
                                employee_id = clean_row[1]
                                name = clean_row[2] if len(clean_row) > 2 else None
                                points = int(clean_row[3]) if len(clean_row) > 3 and clean_row[3] else 0
                                reason = clean_row[4] if len(clean_row) > 4 and clean_row[4] else None
                                date = clean_row[5] if len(clean_row) > 5 and clean_row[5] else None
                                admin_id = clean_row[6] if len(clean_row) > 6 and clean_row[6] else None
                                
                                if employee_id and date:
                                    # Check if this exact record exists
                                    existing = conn.execute("""
                                        SELECT history_id FROM score_history 
                                        WHERE employee_id=? AND date=? AND points=? AND reason=?
                                    """, (employee_id, date, points, reason)).fetchone()
                                    
                                    if not existing:
                                        conn.execute("""
                                            INSERT INTO score_history (employee_id, name, points, reason, date, admin_id)
                                            VALUES (?, ?, ?, ?, ?, ?)
                                        """, (employee_id, name, points, reason, date, admin_id))
                        
                        success_count += 1
                        
                    except Exception as row_error:
                        error_count += 1
                        errors.append(f"Row {row_idx + 1}: {str(row_error)}")
                        continue
                
                import_results[table_name] = {
                    'success': success_count,
                    'errors': error_count,
                    'error_details': errors[:5]  # Limit to first 5 errors per table
                }
                total_success += success_count
                total_errors += error_count
            
            # Commit all changes
            conn.commit()
            
            return jsonify({
                "success": True,
                "message": f"Database dump imported successfully! {total_success} records imported, {total_errors} errors",
                "details": {
                    "total_success": total_success,
                    "total_errors": total_errors,
                    "tables_imported": list(tables_data.keys()),
                    "table_results": import_results
                }
            })
            
    except Exception as e:
        logging.error(f"Error in admin_import_database_dump: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": f"Database dump import failed: {str(e)}"}), 500


@app.route("/admin/import_csv", methods=["POST"])
def admin_import_csv():
    """Import CSV data to database tables"""
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    
    try:
        if 'csv_file' not in request.files:
            return jsonify({"success": False, "message": "No file provided"}), 400
        
        file = request.files['csv_file']
        table_name = request.form.get('table_name')
        import_mode = request.form.get('import_mode', 'append')  # 'append' or 'replace'
        
        if file.filename == '':
            return jsonify({"success": False, "message": "No file selected"}), 400
        
        # Define allowed tables for import (more restrictive than export)
        allowed_import_tables = {
            'employees': {
                'required_columns': ['employee_id', 'name', 'initials'],
                'optional_columns': ['score', 'role', 'active'],
                'table_name': 'employees'
            },
            'incentive_rules': {
                'required_columns': ['description', 'points'],
                'optional_columns': ['details', 'order_index'],
                'table_name': 'rules'
            },
            'roles': {
                'required_columns': ['role_name'],
                'optional_columns': ['description'],
                'table_name': 'roles'
            }
        }
        
        if table_name not in allowed_import_tables:
            return jsonify({"success": False, "message": "Invalid table for import"}), 400
        
        # Read CSV file
        try:
            df = pd.read_csv(file)
        except Exception as e:
            return jsonify({"success": False, "message": f"Error reading CSV: {str(e)}"}), 400
        
        if df.empty:
            return jsonify({"success": False, "message": "CSV file is empty"}), 400
        
        # Validate required columns
        table_config = allowed_import_tables[table_name]
        required_cols = table_config['required_columns']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            return jsonify({
                "success": False, 
                "message": f"Missing required columns: {', '.join(missing_cols)}"
            }), 400
        
        with DatabaseConnection() as conn:
            actual_table_name = table_config['table_name']
            
            # If replace mode, clear existing data (only for master admin)
            if import_mode == 'replace' and session.get("admin_id") == "master":
                if table_name == 'employees':
                    # Don't delete employees, just update them
                    pass
                else:
                    conn.execute(f"DELETE FROM {actual_table_name}")
            
            # Process each row
            success_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    if table_name == 'employees':
                        # Handle employee import
                        employee_id = str(row['employee_id']).strip()
                        name = str(row['name']).strip()
                        initials = str(row['initials']).strip()
                        score = int(row.get('score', 50))
                        role = str(row.get('role', '')).strip() if pd.notna(row.get('role')) else None
                        active = int(row.get('active', 1)) if pd.notna(row.get('active')) else 1
                        
                        # Check if employee exists
                        existing = conn.execute(
                            "SELECT employee_id FROM employees WHERE employee_id = ?", 
                            (employee_id,)
                        ).fetchone()
                        
                        if existing:
                            # Update existing employee
                            conn.execute("""
                                UPDATE employees 
                                SET name=?, initials=?, score=?, role=?, active=?
                                WHERE employee_id=?
                            """, (name, initials, score, role, active, employee_id))
                        else:
                            # Insert new employee
                            conn.execute("""
                                INSERT INTO employees (employee_id, name, initials, score, role, active)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (employee_id, name, initials, score, role, active))
                    
                    elif table_name == 'incentive_rules':
                        # Handle rules import
                        description = str(row['description']).strip()
                        points = int(row['points'])
                        details = str(row.get('details', '')).strip() if pd.notna(row.get('details')) else None
                        order_index = int(row.get('order_index', 0)) if pd.notna(row.get('order_index')) else 0
                        
                        conn.execute("""
                            INSERT INTO rules (description, points, details, order_index)
                            VALUES (?, ?, ?, ?)
                        """, (description, points, details, order_index))
                    
                    elif table_name == 'roles':
                        # Handle roles import
                        role_name = str(row['role_name']).strip()
                        description = str(row.get('description', '')).strip() if pd.notna(row.get('description')) else None
                        
                        conn.execute("""
                            INSERT INTO roles (role_name, description)
                            VALUES (?, ?)
                        """, (role_name, description))
                    
                    success_count += 1
                    
                except Exception as row_error:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(row_error)}")
                    continue
            
            # Commit all changes
            conn.commit()
            
            message = f"Import completed: {success_count} successful"
            if error_count > 0:
                message += f", {error_count} errors"
            
            return jsonify({
                "success": True, 
                "message": message,
                "details": {
                    "success_count": success_count,
                    "error_count": error_count,
                    "errors": errors[:10]  # Limit to first 10 errors
                }
            })
            
    except Exception as e:
        logging.error(f"Error in admin_import_csv: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": f"Import failed: {str(e)}"}), 500


@app.route("/admin/import_json", methods=["POST"])
def admin_import_json():
    """Import JSON data to database tables - supports both simple arrays and complete export format"""
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    
    try:
        if 'json_file' not in request.files:
            return jsonify({"success": False, "message": "No file provided"}), 400
        
        file = request.files['json_file']
        table_name = request.form.get('table_name')  # Can be 'all' for complete import
        import_mode = request.form.get('import_mode', 'append')  # 'append' or 'replace'
        
        if file.filename == '':
            return jsonify({"success": False, "message": "No file selected"}), 400
        
        # Read JSON file
        try:
            file_content = file.read().decode('utf-8')
            json_data = json.loads(file_content)
        except Exception as e:
            return jsonify({"success": False, "message": f"Error reading JSON: {str(e)}"}), 400
        
        # Determine JSON format: complete export or simple array
        is_complete_export = isinstance(json_data, dict) and 'metadata' in json_data and 'data' in json_data
        
        if is_complete_export:
            # Handle complete database export format
            data_section = json_data.get('data', {})
            metadata = json_data.get('metadata', {})
            
            if table_name == 'all':
                # Import all tables from complete export
                return _import_all_tables(data_section, import_mode, metadata)
            else:
                # Import specific table from complete export
                if table_name not in data_section:
                    available_tables = list(data_section.keys())
                    return jsonify({
                        "success": False, 
                        "message": f"Table '{table_name}' not found. Available tables: {', '.join(available_tables)}"
                    }), 400
                
                table_data = data_section[table_name]
                return _import_single_table(table_name, table_data, import_mode)
        else:
            # Handle simple array format (legacy)
            if table_name == 'all':
                return jsonify({"success": False, "message": "Cannot import all tables from simple array format. Use complete export format."}), 400
            
            if not isinstance(json_data, list):
                return jsonify({"success": False, "message": "Simple format must be an array of records"}), 400
            
            return _import_single_table(table_name, json_data, import_mode)
            
    except Exception as e:
        logging.error(f"Error in admin_import_json: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": f"JSON import failed: {str(e)}"}), 500


def _import_all_tables(data_section, import_mode, metadata=None):
    """Import all tables from complete export format"""
    try:
        # Define table import order to handle foreign key dependencies
        table_order = [
            'employees',     # No dependencies
            'roles',         # No dependencies  
            'admins',        # No dependencies
            'incentive_rules',  # No dependencies
            'incentive_pot', # No dependencies
            'point_decay',   # References roles
            'settings',      # No dependencies
            'voting_sessions',  # References admins
            'votes',         # References employees
            'vote_participants',  # References voting_sessions
            'voting_results',    # References voting_sessions, employees
            'score_history',     # References employees
            'feedback'       # No dependencies
        ]
        
        # Only process tables that exist in the data
        available_tables = list(data_section.keys())
        tables_to_import = [table for table in table_order if table in available_tables]
        
        # Add any remaining tables not in the ordered list
        for table in available_tables:
            if table not in tables_to_import:
                tables_to_import.append(table)
        
        total_success = 0
        total_errors = 0
        results = {}
        
        with DatabaseConnection() as conn:
            # If replace mode, clear all data (master admin only)
            if import_mode == 'replace' and session.get("admin_id") == "master":
                # Clear tables in reverse dependency order
                for table in reversed(tables_to_import):
                    if table != 'employees':  # Preserve employees in replace mode
                        try:
                            conn.execute(f"DELETE FROM {table}")
                        except Exception as e:
                            logging.warning(f"Could not clear table {table}: {e}")
            
            # Import each table
            for table_name in tables_to_import:
                table_data = data_section[table_name]
                if not table_data:  # Skip empty tables
                    continue
                    
                try:
                    result = _process_table_data(conn, table_name, table_data, import_mode)
                    results[table_name] = result
                    total_success += result['success_count']
                    total_errors += result['error_count']
                except Exception as e:
                    error_msg = f"Failed to import table {table_name}: {str(e)}"
                    results[table_name] = {'success_count': 0, 'error_count': len(table_data), 'error': error_msg}
                    total_errors += len(table_data)
            
            conn.commit()
        
        # Format response
        table_count = len([r for r in results.values() if r['success_count'] > 0])
        message = f"Complete import: {table_count} tables, {total_success} records imported"
        if total_errors > 0:
            message += f", {total_errors} errors"
            
        if metadata:
            message += f" (Export: {metadata.get('export_timestamp', 'Unknown date')})"
        
        return jsonify({
            "success": True,
            "message": message,
            "details": {
                "total_success": total_success,
                "total_errors": total_errors,
                "table_results": results
            }
        })
        
    except Exception as e:
        logging.error(f"Error in _import_all_tables: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": f"Complete import failed: {str(e)}"}), 500


def _import_single_table(table_name, table_data, import_mode):
    """Import data for a single table"""
    if not isinstance(table_data, list):
        return jsonify({"success": False, "message": f"Data for table '{table_name}' must be an array"}), 400
    
    if len(table_data) == 0:
        return jsonify({"success": False, "message": f"No data found for table '{table_name}'"}), 400
    
    try:
        with DatabaseConnection() as conn:
            # If replace mode, clear existing data (master admin only)
            if import_mode == 'replace' and session.get("admin_id") == "master":
                if table_name != 'employees':  # Don't clear employees
                    conn.execute(f"DELETE FROM {table_name}")
            
            result = _process_table_data(conn, table_name, table_data, import_mode)
            conn.commit()
            
            message = f"{table_name} import: {result['success_count']} successful"
            if result['error_count'] > 0:
                message += f", {result['error_count']} errors"
            
            return jsonify({
                "success": True,
                "message": message,
                "details": result
            })
            
    except Exception as e:
        logging.error(f"Error in _import_single_table: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": f"Table import failed: {str(e)}"}), 500


def _process_table_data(conn, table_name, table_data, import_mode):
    """Process data for a specific table"""
    success_count = 0
    error_count = 0
    errors = []
    
    for index, record in enumerate(table_data):
        try:
            if table_name == 'employees':
                _import_employee_record(conn, record)
            elif table_name == 'votes':
                _import_vote_record(conn, record)
            elif table_name == 'voting_sessions':
                _import_voting_session_record(conn, record)
            elif table_name == 'vote_participants':
                _import_vote_participant_record(conn, record)
            elif table_name == 'admins':
                _import_admin_record(conn, record)
            elif table_name == 'score_history':
                _import_score_history_record(conn, record)
            elif table_name == 'incentive_rules':
                _import_incentive_rule_record(conn, record)
            elif table_name == 'incentive_pot':
                _import_incentive_pot_record(conn, record)
            elif table_name == 'roles':
                _import_role_record(conn, record)
            elif table_name == 'point_decay':
                _import_point_decay_record(conn, record)
            elif table_name == 'voting_results':
                _import_voting_results_record(conn, record)
            elif table_name == 'feedback':
                _import_feedback_record(conn, record)
            elif table_name == 'settings':
                _import_settings_record(conn, record)
            else:
                raise Exception(f"Unsupported table: {table_name}")
            
            success_count += 1
            
        except Exception as row_error:
            error_count += 1
            errors.append(f"Record {index + 1}: {str(row_error)}")
            continue
    
    return {
        'success_count': success_count,
        'error_count': error_count,
        'errors': errors[:10]  # Limit to first 10 errors
    }


# Helper functions for importing specific table records

def _import_employee_record(conn, record):
    """Import a single employee record"""
    employee_id = str(record['employee_id']).strip()
    name = str(record['name']).strip()
    initials = str(record['initials']).strip()
    score = int(record.get('score', 50))
    role = str(record.get('role', '')).strip() if record.get('role') else None
    active = int(record.get('active', 1))
    last_decay_date = record.get('last_decay_date')
    
    # Check if employee exists
    existing = conn.execute("SELECT employee_id FROM employees WHERE employee_id = ?", (employee_id,)).fetchone()
    
    if existing:
        conn.execute("""
            UPDATE employees 
            SET name=?, initials=?, score=?, role=?, active=?, last_decay_date=?
            WHERE employee_id=?
        """, (name, initials, score, role, active, last_decay_date, employee_id))
    else:
        conn.execute("""
            INSERT INTO employees (employee_id, name, initials, score, role, active, last_decay_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (employee_id, name, initials, score, role, active, last_decay_date))


def _import_vote_record(conn, record):
    """Import a single vote record"""
    vote_id = record.get('vote_id')  # May be auto-generated
    voter_initials = record['voter_initials']
    recipient_id = record['recipient_id']
    vote_value = int(record['vote_value'])
    vote_date = record['vote_date']
    
    if vote_id:
        conn.execute("""
            INSERT OR REPLACE INTO votes (vote_id, voter_initials, recipient_id, vote_value, vote_date)
            VALUES (?, ?, ?, ?, ?)
        """, (vote_id, voter_initials, recipient_id, vote_value, vote_date))
    else:
        conn.execute("""
            INSERT INTO votes (voter_initials, recipient_id, vote_value, vote_date)
            VALUES (?, ?, ?, ?)
        """, (voter_initials, recipient_id, vote_value, vote_date))


def _import_voting_session_record(conn, record):
    """Import a single voting session record"""
    session_id = record.get('session_id')
    vote_code = record['vote_code']
    admin_id = record['admin_id']
    start_time = record['start_time']
    end_time = record.get('end_time')
    
    if session_id:
        conn.execute("""
            INSERT OR REPLACE INTO voting_sessions (session_id, vote_code, admin_id, start_time, end_time)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, vote_code, admin_id, start_time, end_time))
    else:
        conn.execute("""
            INSERT INTO voting_sessions (vote_code, admin_id, start_time, end_time)
            VALUES (?, ?, ?, ?)
        """, (vote_code, admin_id, start_time, end_time))


def _import_vote_participant_record(conn, record):
    """Import a single vote participant record"""
    session_id = record['session_id']
    voter_initials = record['voter_initials']
    
    conn.execute("""
        INSERT OR IGNORE INTO vote_participants (session_id, voter_initials)
        VALUES (?, ?)
    """, (session_id, voter_initials))


def _import_admin_record(conn, record):
    """Import a single admin record"""
    admin_id = record['admin_id']
    username = record['username']
    password = record['password']  # Should be already hashed
    is_master = int(record.get('is_master', 0))
    
    existing = conn.execute("SELECT admin_id FROM admins WHERE admin_id = ?", (admin_id,)).fetchone()
    
    if existing:
        conn.execute("""
            UPDATE admins SET username=?, password=?, is_master=?
            WHERE admin_id=?
        """, (username, password, is_master, admin_id))
    else:
        conn.execute("""
            INSERT INTO admins (admin_id, username, password, is_master)
            VALUES (?, ?, ?, ?)
        """, (admin_id, username, password, is_master))


def _import_score_history_record(conn, record):
    """Import a single score history record"""
    history_id = record.get('history_id')
    employee_id = record['employee_id']
    changed_by = record['changed_by']
    points = int(record['points'])
    reason = record.get('reason')
    change_date = record.get('change_date')
    
    if history_id:
        conn.execute("""
            INSERT OR REPLACE INTO score_history (history_id, employee_id, changed_by, points, reason, change_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (history_id, employee_id, changed_by, points, reason, change_date))
    else:
        conn.execute("""
            INSERT INTO score_history (employee_id, changed_by, points, reason, change_date)
            VALUES (?, ?, ?, ?, ?)
        """, (employee_id, changed_by, points, reason, change_date))


def _import_incentive_rule_record(conn, record):
    """Import a single incentive rule record"""
    rule_id = record.get('rule_id')
    description = record['description']
    points = int(record['points'])
    details = record.get('details')
    order_index = int(record.get('order_index', 0))
    
    if rule_id:
        conn.execute("""
            INSERT OR REPLACE INTO rules (rule_id, description, points, details, order_index)
            VALUES (?, ?, ?, ?, ?)
        """, (rule_id, description, points, details, order_index))
    else:
        conn.execute("""
            INSERT INTO rules (description, points, details, order_index)
            VALUES (?, ?, ?, ?)
        """, (description, points, details, order_index))


def _import_incentive_pot_record(conn, record):
    """Import a single incentive pot record"""
    pot_id = record.get('id')
    sales_dollars = float(record.get('sales_dollars', 0))
    bonus_percent = float(record.get('bonus_percent', 0))
    prior_year_sales = float(record.get('prior_year_sales', 0))
    
    if pot_id:
        conn.execute("""
            INSERT OR REPLACE INTO incentive_pot (id, sales_dollars, bonus_percent, prior_year_sales)
            VALUES (?, ?, ?, ?)
        """, (pot_id, sales_dollars, bonus_percent, prior_year_sales))
    else:
        conn.execute("""
            INSERT INTO incentive_pot (sales_dollars, bonus_percent, prior_year_sales)
            VALUES (?, ?, ?)
        """, (sales_dollars, bonus_percent, prior_year_sales))


def _import_role_record(conn, record):
    """Import a single role record"""
    role_name = record['role_name']
    percentage = float(record.get('percentage', 0))
    
    conn.execute("""
        INSERT OR REPLACE INTO roles (role_name, percentage)
        VALUES (?, ?)
    """, (role_name, percentage))


def _import_point_decay_record(conn, record):
    """Import a single point decay record"""
    decay_id = record.get('id')
    role_name = record['role_name']
    points = int(record['points'])
    days = record['days']  # JSON string
    
    if decay_id:
        conn.execute("""
            INSERT OR REPLACE INTO point_decay (id, role_name, points, days)
            VALUES (?, ?, ?, ?)
        """, (decay_id, role_name, points, days))
    else:
        conn.execute("""
            INSERT INTO point_decay (role_name, points, days)
            VALUES (?, ?, ?)
        """, (role_name, points, days))


def _import_voting_results_record(conn, record):
    """Import a single voting results record"""
    session_id = record['session_id']
    employee_id = record['employee_id']
    plus_votes = int(record.get('plus_votes', 0))
    minus_votes = int(record.get('minus_votes', 0))
    net_score = int(record.get('net_score', 0))
    
    conn.execute("""
        INSERT OR REPLACE INTO voting_results (session_id, employee_id, plus_votes, minus_votes, net_score)
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, employee_id, plus_votes, minus_votes, net_score))


def _import_feedback_record(conn, record):
    """Import a single feedback record"""
    feedback_id = record.get('id')
    employee_id = record['employee_id']
    feedback_text = record['feedback_text']
    submitted_date = record.get('submitted_date')
    
    if feedback_id:
        conn.execute("""
            INSERT OR REPLACE INTO feedback (id, employee_id, feedback_text, submitted_date)
            VALUES (?, ?, ?, ?)
        """, (feedback_id, employee_id, feedback_text, submitted_date))
    else:
        conn.execute("""
            INSERT INTO feedback (employee_id, feedback_text, submitted_date)
            VALUES (?, ?, ?)
        """, (employee_id, feedback_text, submitted_date))


def _import_settings_record(conn, record):
    """Import a single settings record"""
    key = record['key']
    value = record['value']
    
    conn.execute("""
        INSERT OR REPLACE INTO settings (key, value)
        VALUES (?, ?)
    """, (key, value))


@app.route("/admin/game_odds", methods=["GET"])
def admin_game_odds():
    """API endpoint to get game odds configuration"""
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    try:
        with DatabaseConnection() as conn:
            # Get all game odds
            odds = conn.execute("""
                SELECT game_type, win_probability, jackpot_probability, updated_at 
                FROM game_odds 
                ORDER BY game_type
            """).fetchall()
            
            # Get all prizes grouped by game type
            prizes = conn.execute("""
                SELECT game_type, prize_type, prize_amount, prize_description, probability, is_jackpot 
                FROM game_prizes 
                ORDER BY game_type, probability DESC
            """).fetchall()
            
            # Group prizes by game type
            prizes_by_game = {}
            for prize in prizes:
                game_type = prize['game_type']
                if game_type not in prizes_by_game:
                    prizes_by_game[game_type] = []
                prizes_by_game[game_type].append(dict(prize))
            
            return jsonify({
                "success": True,
                "odds": [dict(row) for row in odds],
                "prizes": prizes_by_game
            })
            
    except Exception as e:
        logging.error(f"Error getting game odds: {str(e)}")
        return jsonify({"success": False, "message": "Failed to get game configuration"}), 500


@app.route("/admin/update_game_odds", methods=["POST"])
def admin_update_game_odds():
    """Update game odds configuration"""
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    try:
        data = request.get_json()
        game_type = data.get('game_type')
        win_probability = float(data.get('win_probability', 0))
        jackpot_probability = float(data.get('jackpot_probability', 0))
        
        # Validate probabilities
        if not (0 <= win_probability <= 1) or not (0 <= jackpot_probability <= 1):
            return jsonify({"success": False, "message": "Probabilities must be between 0 and 1"}), 400
        
        if jackpot_probability > win_probability:
            return jsonify({"success": False, "message": "Jackpot probability cannot exceed win probability"}), 400
        
        with DatabaseConnection() as conn:
            # Update or insert odds
            conn.execute("""
                INSERT OR REPLACE INTO game_odds (game_type, win_probability, jackpot_probability, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (game_type, win_probability, jackpot_probability))
            conn.commit()
            
            logging.info(f"Updated odds for {game_type}: win={win_probability}, jackpot={jackpot_probability}")
            return jsonify({"success": True, "message": f"Updated odds for {game_type}"})
            
    except Exception as e:
        logging.error(f"Error updating game odds: {str(e)}")
        return jsonify({"success": False, "message": "Failed to update odds"}), 500


@app.route("/admin/update_game_prize", methods=["POST"])
def admin_update_game_prize():
    """Update or add game prize configuration"""
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    try:
        data = request.get_json()
        game_type = data.get('game_type')
        prize_type = data.get('prize_type')
        prize_amount = data.get('prize_amount')
        prize_description = data.get('prize_description')
        probability = float(data.get('probability', 0))
        is_jackpot = bool(data.get('is_jackpot', False))
        prize_id = data.get('id')  # For updates
        
        # Validate probability
        if not (0 <= probability <= 1):
            return jsonify({"success": False, "message": "Probability must be between 0 and 1"}), 400
        
        with DatabaseConnection() as conn:
            if prize_id:
                # Update existing prize
                conn.execute("""
                    UPDATE game_prizes 
                    SET prize_type=?, prize_amount=?, prize_description=?, probability=?, is_jackpot=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                """, (prize_type, prize_amount, prize_description, probability, is_jackpot, prize_id))
                message = f"Updated prize for {game_type}"
            else:
                # Add new prize
                conn.execute("""
                    INSERT INTO game_prizes (game_type, prize_type, prize_amount, prize_description, probability, is_jackpot)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (game_type, prize_type, prize_amount, prize_description, probability, is_jackpot))
                message = f"Added new prize for {game_type}"
            
            conn.commit()
            logging.info(f"Prize updated for {game_type}: {prize_description}")
            return jsonify({"success": True, "message": message})
            
    except Exception as e:
        logging.error(f"Error updating game prize: {str(e)}")
        return jsonify({"success": False, "message": "Failed to update prize"}), 500


@app.route("/admin/delete_game_prize", methods=["POST"])
def admin_delete_game_prize():
    """Delete a game prize"""
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    try:
        data = request.get_json()
        prize_id = data.get('id')
        
        with DatabaseConnection() as conn:
            conn.execute("DELETE FROM game_prizes WHERE id=?", (prize_id,))
            conn.commit()
            
            return jsonify({"success": True, "message": "Prize deleted successfully"})
            
    except Exception as e:
        logging.error(f"Error deleting game prize: {str(e)}")
        return jsonify({"success": False, "message": "Failed to delete prize"}), 500


@app.route("/admin/prize_values", methods=["GET"])
def admin_get_prize_values():
    """Get all prize value configurations for master admin"""
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    try:
        with DatabaseConnection() as conn:
            prize_values = conn.execute("""
                SELECT id, prize_type, prize_description, base_dollar_value, 
                       point_to_dollar_rate, is_system_managed, updated_by, updated_at
                FROM prize_values
                ORDER BY prize_type, prize_description
            """).fetchall()
            
            return jsonify({
                "success": True, 
                "prize_values": [dict(row) for row in prize_values]
            })
            
    except Exception as e:
        logging.error(f"Error getting prize values: {str(e)}")
        return jsonify({"success": False, "message": "Failed to get prize values"}), 500


@app.route("/admin/update_prize_value", methods=["POST"])
def admin_update_prize_value():
    """Update dollar values for prize types"""
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    try:
        data = request.get_json()
        prize_type = data.get('prize_type')
        prize_description = data.get('prize_description')
        base_dollar_value = float(data.get('base_dollar_value', 0.0))
        point_to_dollar_rate = data.get('point_to_dollar_rate')
        
        if point_to_dollar_rate is not None:
            point_to_dollar_rate = float(point_to_dollar_rate)
        
        with DatabaseConnection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO prize_values 
                (prize_type, prize_description, base_dollar_value, point_to_dollar_rate, updated_by, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (prize_type, prize_description, base_dollar_value, point_to_dollar_rate, session['admin_id']))
            
            # Update existing game prizes with new dollar values
            if prize_type == 'points' and point_to_dollar_rate:
                conn.execute("""
                    UPDATE game_prizes 
                    SET dollar_value = prize_amount * ?
                    WHERE prize_type = 'points'
                """, (point_to_dollar_rate,))
            else:
                conn.execute("""
                    UPDATE game_prizes 
                    SET dollar_value = ?
                    WHERE prize_type = ?
                """, (base_dollar_value, prize_type))
            
            conn.commit()
            return jsonify({"success": True, "message": f"Updated {prize_type} value configuration"})
            
    except Exception as e:
        logging.error(f"Error updating prize value: {str(e)}")
        return jsonify({"success": False, "message": "Failed to update prize value"}), 500


@app.route("/admin/payout_analytics", methods=["GET"])
def admin_get_payout_analytics():
    """Get payout analytics and trends"""
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    try:
        days = int(request.args.get('days', 30))
        
        with DatabaseConnection() as conn:
            # Get payout summary
            payout_summary = conn.execute("""
                SELECT 
                    COUNT(*) as total_payouts,
                    SUM(dollar_value) as total_payout_value,
                    AVG(dollar_value) as avg_payout_value,
                    game_type,
                    prize_type
                FROM mini_game_payouts 
                WHERE payout_date >= date('now', '-{} days')
                GROUP BY game_type, prize_type
                ORDER BY total_payout_value DESC
            """.format(days)).fetchall()
            
            # Get daily trends
            daily_trends = conn.execute("""
                SELECT 
                    DATE(payout_date) as payout_date,
                    COUNT(*) as daily_payouts,
                    SUM(dollar_value) as daily_value,
                    COUNT(DISTINCT employee_id) as unique_players
                FROM mini_game_payouts 
                WHERE payout_date >= date('now', '-{} days')
                GROUP BY DATE(payout_date)
                ORDER BY payout_date
            """.format(days)).fetchall()
            
            # Get win rates by game type
            win_rates = conn.execute("""
                SELECT 
                    mg.game_type,
                    COUNT(*) as total_games,
                    COUNT(mp.id) as winning_games,
                    ROUND(CAST(COUNT(mp.id) AS FLOAT) / COUNT(*) * 100, 2) as win_rate_percent
                FROM mini_games mg
                LEFT JOIN mini_game_payouts mp ON mg.id = mp.game_id
                WHERE mg.played_date >= date('now', '-{} days')
                GROUP BY mg.game_type
                ORDER BY win_rate_percent DESC
            """.format(days)).fetchall()
            
            return jsonify({
                "success": True,
                "analytics": {
                    "payout_summary": [dict(row) for row in payout_summary],
                    "daily_trends": [dict(row) for row in daily_trends],
                    "win_rates": [dict(row) for row in win_rates],
                    "period_days": days
                }
            })
            
    except Exception as e:
        logging.error(f"Error getting payout analytics: {str(e)}")
        return jsonify({"success": False, "message": "Failed to get analytics"}), 500


@app.route("/admin/adjust_odds_by_payout", methods=["POST"])
def admin_adjust_odds_by_payout():
    """Automatically adjust odds based on payout analysis"""
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    try:
        data = request.get_json()
        target_payout_rate = float(data.get('target_payout_rate', 0.15))  # 15% default
        adjustment_factor = float(data.get('adjustment_factor', 0.1))  # 10% adjustment
        days_analysis = int(data.get('days', 30))
        
        with DatabaseConnection() as conn:
            # Get current payout rates by game type
            payout_analysis = conn.execute("""
                SELECT 
                    mg.game_type,
                    COUNT(*) as total_games,
                    COALESCE(SUM(mp.dollar_value), 0) as total_payout,
                    go.win_probability as current_win_prob,
                    go.jackpot_probability as current_jackpot_prob
                FROM mini_games mg
                LEFT JOIN mini_game_payouts mp ON mg.id = mp.game_id
                LEFT JOIN game_odds go ON mg.game_type = go.game_type
                WHERE mg.played_date >= date('now', '-{} days')
                GROUP BY mg.game_type, go.win_probability, go.jackpot_probability
            """.format(days_analysis)).fetchall()
            
            adjustments_made = []
            
            for analysis in payout_analysis:
                game_type = analysis['game_type']
                total_games = analysis['total_games']
                total_payout = analysis['total_payout'] or 0
                current_win_prob = analysis['current_win_prob']
                current_jackpot_prob = analysis['current_jackpot_prob']
                
                if total_games > 0:
                    # Calculate average payout per game
                    avg_payout_per_game = total_payout / total_games
                    # Estimate target payout per game (this is simplified - could be more sophisticated)
                    target_avg_payout = target_payout_rate * 5  # Assuming $5 baseline value per game
                    
                    if avg_payout_per_game > target_avg_payout * 1.2:
                        # Payout too high - reduce win probability
                        new_win_prob = max(0.05, current_win_prob * (1 - adjustment_factor))
                        new_jackpot_prob = max(0.01, current_jackpot_prob * (1 - adjustment_factor))
                        adjustment_type = "REDUCED"
                    elif avg_payout_per_game < target_avg_payout * 0.8:
                        # Payout too low - increase win probability
                        new_win_prob = min(0.8, current_win_prob * (1 + adjustment_factor))
                        new_jackpot_prob = min(0.3, current_jackpot_prob * (1 + adjustment_factor))
                        adjustment_type = "INCREASED"
                    else:
                        # Payout is within acceptable range
                        continue
                    
                    # Update the odds
                    conn.execute("""
                        UPDATE game_odds 
                        SET win_probability = ?, jackpot_probability = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE game_type = ?
                    """, (new_win_prob, new_jackpot_prob, game_type))
                    
                    adjustments_made.append({
                        "game_type": game_type,
                        "adjustment_type": adjustment_type,
                        "old_win_prob": current_win_prob,
                        "new_win_prob": new_win_prob,
                        "old_jackpot_prob": current_jackpot_prob,
                        "new_jackpot_prob": new_jackpot_prob,
                        "avg_payout_per_game": round(avg_payout_per_game, 2),
                        "target_payout": round(target_avg_payout, 2)
                    })
            
            conn.commit()
            
            return jsonify({
                "success": True, 
                "message": f"Adjusted odds for {len(adjustments_made)} game types",
                "adjustments": adjustments_made
            })
            
    except Exception as e:
        logging.error(f"Error adjusting odds by payout: {str(e)}")
        return jsonify({"success": False, "message": "Failed to adjust odds"}), 500


@app.route("/admin/system_trends", methods=["GET"])
def admin_get_system_trends():
    """Get comprehensive system trends analysis across points, voting, payouts, and minigames"""
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    try:
        days = int(request.args.get('days', 90))  # Default 3 months
        
        with DatabaseConnection() as conn:
            # Points trend analysis
            points_trends = conn.execute("""
                SELECT 
                    DATE(timestamp) as date,
                    SUM(CASE WHEN points > 0 THEN points ELSE 0 END) as points_awarded,
                    SUM(CASE WHEN points < 0 THEN ABS(points) ELSE 0 END) as points_deducted,
                    COUNT(DISTINCT employee_id) as active_employees,
                    COUNT(*) as total_adjustments
                FROM point_history 
                WHERE timestamp >= date('now', '-{} days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """.format(days)).fetchall()
            
            # Voting patterns
            voting_trends = conn.execute("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as votes_cast,
                    COUNT(DISTINCT voter_employee_id) as voting_employees,
                    COUNT(DISTINCT voted_employee_id) as employees_voted_for,
                    AVG(CAST(votes AS FLOAT)) as avg_votes_per_session
                FROM vote_history 
                WHERE created_at >= date('now', '-{} days')
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """.format(days)).fetchall()
            
            # Mini-game trends
            minigame_trends = conn.execute("""
                SELECT 
                    DATE(mg.played_date) as date,
                    mg.game_type,
                    COUNT(*) as games_played,
                    COUNT(mp.id) as games_won,
                    COALESCE(SUM(mp.dollar_value), 0) as daily_payout_value,
                    COUNT(DISTINCT mg.employee_id) as unique_players
                FROM mini_games mg
                LEFT JOIN mini_game_payouts mp ON mg.id = mp.game_id
                WHERE mg.played_date >= date('now', '-{} days')
                  AND mg.status = 'played'
                GROUP BY DATE(mg.played_date), mg.game_type
                ORDER BY date DESC, games_played DESC
            """.format(days)).fetchall()
            
            # Employee engagement correlation
            engagement_analysis = conn.execute("""
                SELECT 
                    e.employee_id,
                    e.name,
                    e.role,
                    e.score as current_points,
                    COALESCE(mg_stats.games_played, 0) as games_played,
                    COALESCE(mg_stats.games_won, 0) as games_won,
                    COALESCE(mg_stats.total_winnings, 0) as total_winnings,
                    COALESCE(vote_stats.votes_cast, 0) as votes_cast,
                    COALESCE(vote_stats.votes_received, 0) as votes_received
                FROM employees e
                LEFT JOIN (
                    SELECT 
                        mg.employee_id,
                        COUNT(*) as games_played,
                        COUNT(mp.id) as games_won,
                        COALESCE(SUM(mp.dollar_value), 0) as total_winnings
                    FROM mini_games mg
                    LEFT JOIN mini_game_payouts mp ON mg.id = mp.game_id
                    WHERE mg.played_date >= date('now', '-{} days')
                    GROUP BY mg.employee_id
                ) mg_stats ON e.employee_id = mg_stats.employee_id
                LEFT JOIN (
                    SELECT 
                        voter_employee_id as employee_id,
                        COUNT(*) as votes_cast
                    FROM vote_history 
                    WHERE created_at >= date('now', '-{} days')
                    GROUP BY voter_employee_id
                ) vote_stats ON e.employee_id = vote_stats.employee_id
                LEFT JOIN (
                    SELECT 
                        voted_employee_id as employee_id,
                        SUM(votes) as votes_received
                    FROM vote_history 
                    WHERE created_at >= date('now', '-{} days')
                    GROUP BY voted_employee_id
                ) vote_received ON e.employee_id = vote_received.employee_id
                WHERE e.active = 1
                ORDER BY current_points DESC
            """.format(days, days, days, days)).fetchall()
            
            # Calculate correlation metrics
            total_points_awarded = sum(row['points_awarded'] for row in points_trends if row['points_awarded'])
            total_payout_value = sum(row['daily_payout_value'] for row in minigame_trends if row['daily_payout_value'])
            total_games_played = sum(row['games_played'] for row in minigame_trends if row['games_played'])
            total_votes_cast = sum(row['votes_cast'] for row in voting_trends if row['votes_cast'])
            
            return jsonify({
                "success": True,
                "trends": {
                    "period_days": days,
                    "summary_metrics": {
                        "total_points_awarded": total_points_awarded,
                        "total_payout_value": round(total_payout_value, 2),
                        "total_games_played": total_games_played,
                        "total_votes_cast": total_votes_cast,
                        "payout_per_point_ratio": round(total_payout_value / max(total_points_awarded, 1), 4),
                        "games_per_vote_ratio": round(total_games_played / max(total_votes_cast, 1), 2)
                    },
                    "points_trends": [dict(row) for row in points_trends],
                    "voting_trends": [dict(row) for row in voting_trends],
                    "minigame_trends": [dict(row) for row in minigame_trends],
                    "engagement_analysis": [dict(row) for row in engagement_analysis]
                }
            })
            
    except Exception as e:
        logging.error(f"Error getting system trends: {str(e)}")
        return jsonify({"success": False, "message": "Failed to get system trends"}), 500


@app.route("/admin/connection_pool_stats", methods=["GET"])
def admin_connection_pool_stats():
    """Get connection pool statistics for monitoring and performance analysis"""
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    try:
        from incentive_service import get_pool_statistics
        stats = get_pool_statistics()
        
        return jsonify({
            "success": True,
            "stats": stats,
            "performance_metrics": {
                "efficiency": f"{stats['hit_ratio']:.2%}",
                "utilization": f"{stats['active_connections'] / stats['pool_size']:.2%}",
                "overflow_usage": f"{stats['overflow_connections'] / max(1, stats['pool_size']):.2%}",
                "health_score": "Good" if stats['failed_connections'] < 10 else "Needs attention"
            },
            "recommendations": get_pool_recommendations(stats)
        })
        
    except Exception as e:
        logging.error(f"Error getting connection pool stats: {str(e)}")
        return jsonify({"success": False, "message": "Failed to get pool statistics"}), 500

def get_pool_recommendations(stats):
    """Generate recommendations based on pool statistics"""
    recommendations = []
    
    if stats['hit_ratio'] < 0.8:
        recommendations.append("Consider increasing pool size - low hit ratio indicates frequent overflow usage")
    
    if stats['overflow_connections'] > stats['pool_size'] * 0.5:
        recommendations.append("High overflow usage detected - increase base pool size")
        
    if stats['failed_connections'] > stats['total_created'] * 0.1:
        recommendations.append("High connection failure rate - check database health")
        
    if stats['active_connections'] / stats['pool_size'] > 0.9:
        recommendations.append("Pool utilization very high - consider increasing pool size")
        
    if not recommendations:
        recommendations.append("Connection pool performance is optimal")
        
    return recommendations


# Missing Mini-games Admin Routes

@app.route("/admin/game_details", methods=["GET"])
def admin_game_details_overview():
    """Overview of all mini-games without requiring specific game ID"""
    if "admin_id" not in session:
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({"success": False, "message": "Admin login required"}), 403
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    
    try:
        with DatabaseConnection() as conn:
            # Get all games with employee information
            games = conn.execute("""
                SELECT mg.id, mg.game_type, mg.status, mg.outcome, mg.awarded_date, mg.played_date,
                       e.name as employee_name, e.initials as employee_initials
                FROM mini_games mg 
                LEFT JOIN employees e ON mg.employee_id = e.employee_id 
                ORDER BY mg.awarded_date DESC
            """).fetchall()
            
            # Get game statistics
            stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_games,
                    COUNT(CASE WHEN status = 'unused' THEN 1 END) as unused_games,
                    COUNT(CASE WHEN status = 'played' THEN 1 END) as played_games,
                    COUNT(CASE WHEN status = 'played' AND outcome LIKE '%"win":true%' THEN 1 END) as won_games
                FROM mini_games
            """).fetchone()
            
            # Get game type breakdown
            type_breakdown = conn.execute("""
                SELECT game_type, 
                       COUNT(*) as total,
                       COUNT(CASE WHEN status = 'unused' THEN 1 END) as unused,
                       COUNT(CASE WHEN status = 'played' THEN 1 END) as played,
                       COUNT(CASE WHEN status = 'played' AND outcome LIKE '%"win":true%' THEN 1 END) as won
                FROM mini_games 
                GROUP BY game_type
                ORDER BY game_type
            """).fetchall()
            
            # Check if this is a JSON request
            if request.headers.get('Content-Type') == 'application/json' or request.args.get('format') == 'json':
                return jsonify({
                    "success": True,
                    "games": [dict(game) for game in games],
                    "statistics": dict(stats) if stats else {},
                    "type_breakdown": [dict(tb) for tb in type_breakdown]
                })
            
            # Return HTML template for browser access
            is_master = session.get('admin_id') == 'master'
            return render_template('admin_game_details.html',
                                   games=[dict(game) for game in games],
                                   statistics=dict(stats) if stats else {},
                                   type_breakdown=[dict(tb) for tb in type_breakdown],
                                   is_master=is_master)
                
    except Exception as e:
        logging.error(f"Error in admin_game_details_overview: {str(e)}\n{traceback.format_exc()}")
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({"success": False, "message": "Server error"}), 500
        flash("Server error occurred", "danger")
        return redirect(url_for('admin'))

@app.route("/admin/game_analytics", methods=["GET"])
def admin_game_analytics():
    """Game analytics dashboard with comprehensive statistics"""
    if "admin_id" not in session:
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({"success": False, "message": "Admin login required"}), 403
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    
    try:
        with DatabaseConnection() as conn:
            # Overall statistics
            overall_stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_games_awarded,
                    COUNT(CASE WHEN status = 'played' THEN 1 END) as total_games_played,
                    COUNT(CASE WHEN status = 'unused' THEN 1 END) as unused_games,
                    COUNT(CASE WHEN status = 'played' AND outcome LIKE '%"win":true%' THEN 1 END) as total_wins,
                    CAST(AVG(CASE WHEN status = 'played' AND outcome LIKE '%"win":true%' THEN 1.0 ELSE 0.0 END) * 100 as REAL) as win_percentage
                FROM mini_games
            """).fetchone()
            
            # Game type performance
            type_performance = conn.execute("""
                SELECT 
                    game_type,
                    COUNT(*) as total_awarded,
                    COUNT(CASE WHEN status = 'played' THEN 1 END) as played,
                    COUNT(CASE WHEN status = 'played' AND outcome LIKE '%"win":true%' THEN 1 END) as wins,
                    CAST(AVG(CASE WHEN status = 'played' AND outcome LIKE '%"win":true%' THEN 1.0 ELSE 0.0 END) * 100 as REAL) as win_rate,
                    COUNT(CASE WHEN status = 'unused' THEN 1 END) as unused
                FROM mini_games 
                GROUP BY game_type
                ORDER BY game_type
            """).fetchall()
            
            # Employee game activity
            employee_activity = conn.execute("""
                SELECT 
                    e.name,
                    e.initials,
                    COUNT(mg.id) as games_awarded,
                    COUNT(CASE WHEN mg.status = 'played' THEN 1 END) as games_played,
                    COUNT(CASE WHEN mg.status = 'played' AND mg.outcome LIKE '%"win":true%' THEN 1 END) as wins,
                    COUNT(CASE WHEN mg.status = 'unused' THEN 1 END) as unused_games
                FROM employees e
                LEFT JOIN mini_games mg ON e.employee_id = mg.employee_id
                WHERE e.active = 1
                GROUP BY e.employee_id, e.name, e.initials
                HAVING COUNT(mg.id) > 0
                ORDER BY games_awarded DESC
            """).fetchall()
            
            # Recent activity (last 30 days)
            recent_activity = conn.execute("""
                SELECT 
                    DATE(awarded_date) as date,
                    COUNT(*) as games_awarded,
                    COUNT(CASE WHEN status = 'played' THEN 1 END) as games_played
                FROM mini_games 
                WHERE awarded_date >= date('now', '-30 days')
                GROUP BY DATE(awarded_date)
                ORDER BY date DESC
                LIMIT 30
            """).fetchall()
            
            # Prize distribution (if outcome data exists)
            prize_distribution = conn.execute("""
                SELECT 
                    json_extract(outcome, '$.prize_type') as prize_type,
                    json_extract(outcome, '$.prize_amount') as prize_amount,
                    COUNT(*) as frequency
                FROM mini_games 
                WHERE status = 'played' 
                    AND outcome IS NOT NULL 
                    AND outcome LIKE '%"win":true%'
                    AND json_extract(outcome, '$.prize_type') IS NOT NULL
                GROUP BY json_extract(outcome, '$.prize_type'), json_extract(outcome, '$.prize_amount')
                ORDER BY frequency DESC
            """).fetchall()
            
            # Check if this is a JSON request
            if request.headers.get('Content-Type') == 'application/json' or request.args.get('format') == 'json':
                return jsonify({
                    "success": True,
                    "overall_stats": dict(overall_stats) if overall_stats else {},
                    "type_performance": [dict(tp) for tp in type_performance],
                    "employee_activity": [dict(ea) for ea in employee_activity],
                    "recent_activity": [dict(ra) for ra in recent_activity],
                    "prize_distribution": [dict(pd) for pd in prize_distribution]
                })
            
            # Return HTML template for browser access
            is_master = session.get('admin_id') == 'master'
            return render_template('admin_game_analytics.html',
                                   overall_stats=dict(overall_stats) if overall_stats else {},
                                   type_performance=[dict(tp) for tp in type_performance],
                                   employee_activity=[dict(ea) for ea in employee_activity],
                                   recent_activity=[dict(ra) for ra in recent_activity],
                                   prize_distribution=[dict(pd) for pd in prize_distribution],
                                   is_master=is_master)
                
    except Exception as e:
        logging.error(f"Error in admin_game_analytics: {str(e)}\n{traceback.format_exc()}")
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({"success": False, "message": "Server error"}), 500
        flash("Server error occurred", "danger")
        return redirect(url_for('admin'))

@app.route("/admin/game_settings", methods=["GET", "POST"])
def admin_game_settings():
    """Game settings and configuration management"""
    if "admin_id" not in session:
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({"success": False, "message": "Admin login required"}), 403
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    
    try:
        with DatabaseConnection() as conn:
            if request.method == "GET":
                # Get current game odds
                game_odds = conn.execute("""
                    SELECT game_type, win_probability, jackpot_probability, updated_at 
                    FROM game_odds 
                    ORDER BY game_type
                """).fetchall()
                
                # Get game prizes
                game_prizes = conn.execute("""
                    SELECT id, game_type, prize_type, prize_amount, prize_description, probability 
                    FROM game_prizes 
                    ORDER BY game_type, prize_amount DESC
                """).fetchall()
                
                # Get prize values
                prize_values = conn.execute("""
                    SELECT prize_type, point_value, description 
                    FROM prize_values 
                    ORDER BY point_value DESC
                """).fetchall()
                
                # Check if this is a JSON request
                if request.headers.get('Content-Type') == 'application/json' or request.args.get('format') == 'json':
                    return jsonify({
                        "success": True,
                        "game_odds": [dict(go) for go in game_odds],
                        "game_prizes": [dict(gp) for gp in game_prizes],
                        "prize_values": [dict(pv) for pv in prize_values]
                    })
                
                # Return HTML template for browser access
                is_master = session.get('admin_id') == 'master'
                return render_template('admin_game_settings.html',
                                       game_odds=[dict(go) for go in game_odds],
                                       game_prizes=[dict(gp) for gp in game_prizes],
                                       prize_values=[dict(pv) for pv in prize_values],
                                       is_master=is_master)
            
            elif request.method == "POST":
                # Handle settings updates
                data = request.get_json()
                action = data.get('action')
                
                if action == 'update_odds':
                    game_type = data.get('game_type')
                    win_probability = float(data.get('win_probability', 0))
                    jackpot_probability = float(data.get('jackpot_probability', 0))
                    
                    # Validate probabilities
                    if not (0 <= win_probability <= 1) or not (0 <= jackpot_probability <= 1):
                        return jsonify({"success": False, "message": "Probabilities must be between 0 and 1"}), 400
                    
                    if jackpot_probability > win_probability:
                        return jsonify({"success": False, "message": "Jackpot probability cannot exceed win probability"}), 400
                    
                    # Update odds
                    conn.execute("""
                        INSERT OR REPLACE INTO game_odds (game_type, win_probability, jackpot_probability, updated_at)
                        VALUES (?, ?, ?, datetime('now'))
                    """, (game_type, win_probability, jackpot_probability))
                    
                    return jsonify({"success": True, "message": f"Updated odds for {game_type}"})
                
                elif action == 'add_prize':
                    game_type = data.get('game_type')
                    prize_type = data.get('prize_type')
                    prize_amount = data.get('prize_amount')
                    prize_description = data.get('prize_description')
                    probability = float(data.get('probability', 0))
                    
                    if not (0 <= probability <= 1):
                        return jsonify({"success": False, "message": "Probability must be between 0 and 1"}), 400
                    
                    conn.execute("""
                        INSERT INTO game_prizes (game_type, prize_type, prize_amount, prize_description, probability)
                        VALUES (?, ?, ?, ?, ?)
                    """, (game_type, prize_type, prize_amount, prize_description, probability))
                    
                    return jsonify({"success": True, "message": "Prize added successfully"})
                
                elif action == 'delete_prize':
                    prize_id = data.get('prize_id')
                    conn.execute("DELETE FROM game_prizes WHERE id = ?", (prize_id,))
                    return jsonify({"success": True, "message": "Prize deleted successfully"})
                
                elif action == 'update_prize_value':
                    prize_type = data.get('prize_type')
                    point_value = data.get('point_value')
                    description = data.get('description')
                    
                    conn.execute("""
                        INSERT OR REPLACE INTO prize_values (prize_type, point_value, description)
                        VALUES (?, ?, ?)
                    """, (prize_type, point_value, description))
                    
                    return jsonify({"success": True, "message": f"Updated prize value for {prize_type}"})
                
                else:
                    return jsonify({"success": False, "message": "Unknown action"}), 400
                
    except Exception as e:
        logging.error(f"Error in admin_game_settings: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/award_game_manual", methods=["GET", "POST"])
def admin_award_game_manual():
    """Manual game awarding interface with enhanced functionality"""
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    
    try:
        with DatabaseConnection() as conn:
            if request.method == "GET":
                # Get active employees
                employees = conn.execute("""
                    SELECT employee_id, name, initials, score, role 
                    FROM employees 
                    WHERE active = 1 
                    ORDER BY name
                """).fetchall()
                
                # Get available game types
                game_types = ['slot', 'scratch', 'roulette', 'wheel', 'dice']
                
                return jsonify({
                    "success": True,
                    "employees": [dict(emp) for emp in employees],
                    "game_types": game_types
                })
            
            elif request.method == "POST":
                # Handle manual game awarding
                data = request.get_json() if request.is_json else request.form.to_dict()
                
                employee_id = data.get('employee_id')
                game_type = data.get('game_type')
                quantity = int(data.get('quantity', 1))
                reason = data.get('reason', 'Manual admin award')
                
                if not employee_id or not game_type:
                    return jsonify({"success": False, "message": "Employee and game type are required"}), 400
                
                if quantity < 1 or quantity > 10:
                    return jsonify({"success": False, "message": "Quantity must be between 1 and 10"}), 400
                
                # Verify employee exists and is active
                employee = conn.execute("""
                    SELECT name, active FROM employees WHERE employee_id = ?
                """, (employee_id,)).fetchone()
                
                if not employee:
                    return jsonify({"success": False, "message": "Employee not found"}), 404
                
                if not employee['active']:
                    return jsonify({"success": False, "message": "Cannot award games to inactive employees"}), 400
                
                # Award the games
                awarded_games = []
                for _ in range(quantity):
                    conn.execute("""
                        INSERT INTO mini_games (employee_id, game_type, status, awarded_date)
                        VALUES (?, ?, 'unused', datetime('now'))
                    """, (employee_id, game_type))
                    
                    game_id = conn.lastrowid
                    awarded_games.append(game_id)
                
                # Log the award action
                conn.execute("""
                    INSERT INTO system_analytics (event_type, event_data, timestamp)
                    VALUES ('admin_game_award', ?, datetime('now'))
                """, (f"Admin {session['admin_id']} awarded {quantity} {game_type} games to {employee['name']} ({employee_id}). Reason: {reason}",))
                
                return jsonify({
                    "success": True, 
                    "message": f"Successfully awarded {quantity} {game_type} game(s) to {employee['name']}",
                    "awarded_games": awarded_games
                })
                
    except Exception as e:
        logging.error(f"Error in admin_award_game_manual: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/revoke_game", methods=["POST"])
def admin_revoke_game():
    """Revoke an unused game token"""
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    
    try:
        game_id = request.form.get('game_id')
        if not game_id:
            return jsonify({"success": False, "message": "Game ID is required"}), 400
        
        with DatabaseConnection() as conn:
            # Check if game exists and is unused
            game = conn.execute("""
                SELECT mg.id, mg.status, e.name as employee_name 
                FROM mini_games mg 
                LEFT JOIN employees e ON mg.employee_id = e.employee_id
                WHERE mg.id = ?
            """, (game_id,)).fetchone()
            
            if not game:
                return jsonify({"success": False, "message": "Game not found"}), 404
            
            if game['status'] != 'unused':
                return jsonify({"success": False, "message": "Can only revoke unused games"}), 400
            
            # Delete the game record
            conn.execute("DELETE FROM mini_games WHERE id = ?", (game_id,))
            
            # Log the revoke action
            conn.execute("""
                INSERT INTO system_analytics (event_type, event_data, timestamp)
                VALUES ('admin_game_revoke', ?, datetime('now'))
            """, (f"Admin {session['admin_id']} revoked unused game {game_id} from {game['employee_name']}",))
            
            return jsonify({"success": True, "message": f"Game token revoked successfully"})
            
    except Exception as e:
        logging.error(f"Error in admin_revoke_game: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500


@app.route("/employee_portal", methods=["GET", "POST"])
def employee_portal():
    login_form = EmployeeLoginForm()
    if request.method == "POST" and login_form.validate_on_submit():
        employee_id = login_form.employee_id.data
        pin = login_form.pin.data
        with DatabaseConnection() as conn:
            if verify_pin(conn, employee_id, pin):
                session['employee_id'] = employee_id
                flash("Access granted", "success")
                return redirect(url_for('employee_portal'))
            else:
                flash("Invalid ID or PIN", "danger")
    if 'employee_id' in session:
        with DatabaseConnection() as conn:
            emp = conn.execute("SELECT employee_id, name, score FROM employees WHERE employee_id=?", (session['employee_id'],)).fetchone()
            unused = conn.execute("SELECT id, game_type, awarded_date FROM mini_games WHERE employee_id=? AND status='unused'", (session['employee_id'],)).fetchall()
            used = conn.execute("SELECT id, game_type, outcome, played_date FROM mini_games WHERE employee_id=? AND status='played'", (session['employee_id'],)).fetchall()
        change_pin_form = ChangePinForm()
        return render_template('employee_portal.html', login_form=login_form, change_pin_form=change_pin_form, employee=emp, unused_games=unused, used_games=used)
    return render_template('employee_portal.html', login_form=login_form, employee=None)


@app.route("/employee/change_pin", methods=["POST"])
def employee_change_pin():
    if 'employee_id' not in session:
        return redirect(url_for('employee_portal'))
    form = ChangePinForm()
    if form.validate_on_submit():
        with DatabaseConnection() as conn:
            if verify_pin(conn, session['employee_id'], form.current_pin.data):
                new_hash = generate_password_hash(form.new_pin.data)
                conn.execute("UPDATE employees SET pin_hash=? WHERE employee_id=?", (new_hash, session['employee_id']))
                conn.commit()
                flash("PIN updated", "success")
            else:
                flash("Current PIN incorrect", "danger")
    else:
        flash("Invalid form data", "danger")
    return redirect(url_for('employee_portal'))


@app.route("/employee/logout", methods=["POST"])
def employee_logout():
    session.pop('employee_id', None)
    flash("Logged out", "info")
    return redirect(url_for('employee_portal'))


@app.route("/play_game/<int:game_id>", methods=["POST"])
def play_game(game_id):
    """Enhanced Vegas-style mini game with proper casino mechanics"""
    if 'employee_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    
    try:
        # Validate CSRF token manually for non-form requests
        csrf.protect()
    except CSRFError as e:
        logging.error(f"CSRF error in play_game: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': 'CSRF validation failed. Please refresh and try again.'}), 400
    
    try:
        with DatabaseConnection() as conn:
            # Verify game ownership and status
            game_row = conn.execute(
                "SELECT employee_id, game_type FROM mini_games WHERE id=? AND status='unused'", 
                (game_id,)
            ).fetchone()
            
            if not game_row or game_row['employee_id'] != session['employee_id']:
                return jsonify({'success': False, 'message': 'Invalid or unavailable game'}), 403
            
            game_type = game_row['game_type']
            
            # Get game configuration
            settings = get_settings(conn)
            cfg = json.loads(settings.get('mini_game_settings', '{}'))
            
            # Play the specific game type with database-driven odds
            if game_type == 'slot':
                result = play_slot_machine_game(conn, cfg)
            elif game_type == 'scratch':
                result = play_scratch_off_game(conn, cfg)
            elif game_type == 'wheel':
                result = play_wheel_game(conn, cfg)
            elif game_type == 'roulette':
                result = play_roulette_game(conn, cfg)
            elif game_type == 'dice':
                result = play_dice_game(conn, cfg)
            else:
                result = play_generic_game(conn, cfg)
            
            # Process the game outcome
            outcome_data = {
                'game_type': game_type,
                'result': result['outcome'],
                'win': result['win'],
                'prize_type': result.get('prize_type'),
                'prize_amount': result.get('prize_amount', 0),
                'prize_description': result.get('prize_description'),
                'dollar_value': result.get('dollar_value', 0.0),
                'timestamp': datetime.now().isoformat()
            }
            
            # Award prizes if won
            if result['win']:
                prize_type = result.get('prize_type')
                prize_amount = result.get('prize_amount', 0)
                dollar_value = result.get('dollar_value', 0.0)
                
                # Handle different prize types
                if prize_type == 'points' and prize_amount > 0:
                    # Award points
                    adjust_points(
                        conn, 
                        session['employee_id'], 
                        prize_amount, 
                        "SYSTEM",
                        f"Vegas {game_type.title()} Game Win",
                        f"Automated prize from {game_type} mini-game (Game ID: {game_id})"
                    )
                elif prize_type == 'mini_game':
                    # Award another random mini game
                    award_mini_game(conn, session['employee_id'], random.choice(['slot', 'scratch', 'roulette', 'wheel', 'dice']))
                
                # Track payout regardless of prize type
                record_mini_game_payout(
                    conn, game_id, session['employee_id'], game_type,
                    prize_type, prize_amount, dollar_value
                )
            
            # Record the game play
            play_mini_game(conn, game_id, json.dumps(outcome_data))
            conn.commit()
            
            # Format response message
            if result['win']:
                prize_type = result.get('prize_type')
                if prize_type == 'points':
                    if result.get('prize_amount', 0) >= 50:
                        message = f"🎉 JACKPOT! You won {result['prize_amount']} points! 🎉"
                    else:
                        message = f"🎰 Winner! You earned {result['prize_amount']} points!"
                elif prize_type == 'mini_game':
                    message = f"🎁 BONUS! You won another mini-game! Check your unused games!"
                else:
                    message = f"🏆 You won: {result.get('prize_description', 'Special Prize')}!"
            else:
                message = "🎲 Better luck next time! Keep spinning!"
            
            return jsonify({
                'success': True,
                'message': message,
                'result': result,
                'jackpot': result.get('prize_amount', 0) >= 50
            })
            
    except Exception as e:
        logging.error(f"Error in play_game: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': 'Casino malfunction! Try again.'}), 500


def get_game_odds_and_prizes(conn, game_type):
    """Get game odds and available prizes from database"""
    # Get odds
    odds_row = conn.execute(
        "SELECT win_probability, jackpot_probability FROM game_odds WHERE game_type=?", 
        (game_type,)
    ).fetchone()
    
    if not odds_row:
        # Default fallback odds
        odds = {'win_probability': 0.3, 'jackpot_probability': 0.05}
    else:
        odds = {'win_probability': odds_row['win_probability'], 'jackpot_probability': odds_row['jackpot_probability']}
    
    # Get available prizes
    prizes = conn.execute(
        "SELECT prize_type, prize_amount, prize_description, probability, is_jackpot FROM game_prizes WHERE game_type=? ORDER BY probability DESC",
        (game_type,)
    ).fetchall()
    
    if not prizes:
        # Default fallback prizes
        prizes = [
            {'prize_type': 'points', 'prize_amount': 5, 'prize_description': '5 Points', 'probability': 0.2, 'is_jackpot': 0},
            {'prize_type': 'points', 'prize_amount': 10, 'prize_description': '10 Points', 'probability': 0.1, 'is_jackpot': 0}
        ]
    
    return odds, prizes


def select_prize_by_probability(prizes):
    """Select a prize based on probability weights"""
    total_prob = sum(p['probability'] for p in prizes)
    rand_val = random.random() * total_prob
    
    cumulative = 0
    for prize in prizes:
        cumulative += prize['probability']
        if rand_val <= cumulative:
            return prize
    
    # Fallback to first prize
    return prizes[0] if prizes else None


def record_mini_game_payout(conn, game_id, employee_id, game_type, prize_type, prize_amount, dollar_value):
    """Record payout for analytics and tracking"""
    try:
        conn.execute("""
            INSERT INTO mini_game_payouts 
            (game_id, employee_id, game_type, prize_type, prize_amount, dollar_value)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (game_id, employee_id, game_type, prize_type, prize_amount, dollar_value))
        logging.debug(f"Recorded payout: {prize_type} ${dollar_value} for employee {employee_id}")
    except Exception as e:
        logging.error(f"Failed to record payout: {e}")


def play_slot_machine_game(conn, config):
    """Professional 3-reel slot machine with database-driven odds"""
    odds, prizes = get_game_odds_and_prizes(conn, 'slot')
    
    symbols = ['🍒', '🍋', '🍊', '🍇', '⭐', '💎', '🔔', '7️⃣']
    weights = [20, 18, 15, 12, 10, 8, 5, 2]  # Weighted probability
    
    reels = []
    for _ in range(3):
        reel = random.choices(symbols, weights=weights)[0]
        reels.append(reel)
    
    # Determine if this is a win based on database odds
    win_roll = random.random()
    win = win_roll < odds['win_probability']
    
    prize_amount = 0
    prize_type = 'points'
    dollar_value = 0.0
    prize_description = None
    dollar_value = 0.0
    
    if win:
        # Select prize based on configured probabilities
        selected_prize = select_prize_by_probability(prizes)
        if selected_prize:
            prize_amount = selected_prize['prize_amount'] or 0
            prize_type = selected_prize['prize_type']
            prize_description = selected_prize['prize_description']
            dollar_value = getattr(selected_prize, 'dollar_value', 0.0) or 0.0
    
    return {
        'outcome': {'reels': reels, 'pattern': 'slots'},
        'win': win,
        'prize_type': prize_type,
        'prize_amount': prize_amount,
        'prize_description': prize_description,
        'dollar_value': dollar_value
    }


def play_scratch_off_game(conn, config):
    """Scratch-off lottery with database-driven prizes"""
    odds, prizes = get_game_odds_and_prizes(conn, 'scratch')
    
    # Generate scratch pattern
    scratch_symbols = ['💰', '⭐', '🍀', '🎁', '❌', '💎', '🍒']
    scratch_grid = []
    for _ in range(3):
        row = [random.choice(scratch_symbols) for _ in range(3)]
        scratch_grid.append(row)
    
    # Determine if this is a win based on database odds
    win_roll = random.random()
    win = win_roll < odds['win_probability']
    
    prize_amount = 0
    prize_type = 'points'
    dollar_value = 0.0
    prize_description = None
    dollar_value = 0.0
    winning_symbol = None
    
    if win:
        # Select prize based on configured probabilities
        selected_prize = select_prize_by_probability(prizes)
        if selected_prize:
            prize_amount = selected_prize['prize_amount'] or 0
            prize_type = selected_prize['prize_type']
            prize_description = selected_prize['prize_description']
            dollar_value = getattr(selected_prize, 'dollar_value', 0.0) or 0.0
            
        # Add some winning symbols to the grid for visual effect
        flat_grid = [item for row in scratch_grid for item in row]
        symbol_counts = {symbol: flat_grid.count(symbol) for symbol in set(flat_grid)}
        winning_symbol = max(symbol_counts, key=symbol_counts.get)
    
    return {
        'outcome': {
            'grid': scratch_grid, 
            'winning_symbol': winning_symbol
        },
        'win': win,
        'prize_type': prize_type,
        'prize_amount': prize_amount,
        'prize_description': prize_description,
        'dollar_value': dollar_value
    }


def play_roulette_game(conn, config):
    """Mini roulette with database-driven odds"""
    odds, prizes = get_game_odds_and_prizes(conn, 'roulette')
    
    winning_number = random.randint(0, 36)
    color = 'green' if winning_number == 0 else ('red' if winning_number % 2 == 1 else 'black')
    
    # Simple betting system - bet on color
    player_bet = random.choice(['red', 'black', 'green'])
    
    # Determine if this is a win based on database odds
    win_roll = random.random()
    win = win_roll < odds['win_probability']
    
    prize_amount = 0
    prize_type = 'points'
    dollar_value = 0.0
    prize_description = None
    
    if win:
        # Select prize based on configured probabilities
        selected_prize = select_prize_by_probability(prizes)
        if selected_prize:
            prize_amount = selected_prize['prize_amount'] or 0
            prize_type = selected_prize['prize_type']
            prize_description = selected_prize['prize_description']
            dollar_value = getattr(selected_prize, 'dollar_value', 0.0) or 0.0
    
    return {
        'outcome': {
            'number': winning_number,
            'color': color,
            'bet': player_bet
        },
        'win': win,
        'prize_type': prize_type,
        'prize_amount': prize_amount,
        'prize_description': prize_description
    }


def play_wheel_game(conn, config):
    """Wheel of Fortune style spinning wheel game with database-driven odds"""
    odds, prizes = get_game_odds_and_prizes(conn, 'wheel')
    
    # Define wheel segments for visual display
    segments = [
        {'name': '6 Points', 'color': '#4CAF50'},
        {'name': '12 Points', 'color': '#2196F3'},
        {'name': '20 Points', 'color': '#FF9800'},
        {'name': 'Early Lunch', 'color': '#9C27B0'},
        {'name': 'WHEEL WINNER!', 'color': '#FFD700'},
        {'name': '6 Points', 'color': '#607D8B'},
        {'name': '12 Points', 'color': '#E91E63'},
        {'name': 'Try Again', 'color': '#F44336'}
    ]
    
    # Determine if this is a win based on database odds
    win_roll = random.random()
    win = win_roll < odds['win_probability']
    
    # Select segment for animation (random for visual effect)
    selected_segment = random.choice(segments)
    
    # Calculate final spin position (for animation)
    segment_angle = 360 / len(segments)
    segment_index = segments.index(selected_segment)
    final_angle = segment_index * segment_angle + random.uniform(0, segment_angle)
    
    # Add multiple rotations for spinning effect
    spin_rotations = random.randint(3, 8)
    total_angle = (spin_rotations * 360) + final_angle
    
    prize_amount = 0
    prize_type = 'points'
    dollar_value = 0.0
    prize_description = None
    
    if win:
        # Select prize based on configured probabilities
        selected_prize = select_prize_by_probability(prizes)
        if selected_prize:
            prize_amount = selected_prize['prize_amount'] or 0
            prize_type = selected_prize['prize_type']
            prize_description = selected_prize['prize_description']
            dollar_value = getattr(selected_prize, 'dollar_value', 0.0) or 0.0
    
    return {
        'outcome': {
            'winning_segment': selected_segment,
            'angle': total_angle,
            'segments': segments  # Include all segments for wheel display
        },
        'win': win,
        'prize_type': prize_type,
        'prize_amount': prize_amount,
        'prize_description': prize_description
    }


def play_dice_game(conn, config):
    """Vegas-style dice game with database-driven odds"""
    odds, prizes = get_game_odds_and_prizes(conn, 'dice')
    
    # Roll two dice
    die1 = random.randint(1, 6)
    die2 = random.randint(1, 6)
    total = die1 + die2
    
    # Determine if this is a win based on database odds
    win_roll = random.random()
    win = win_roll < odds['win_probability']
    
    # Special winning conditions for visual appeal
    is_double = (die1 == die2)
    is_lucky_seven = (total == 7)
    is_snake_eyes = (die1 == 1 and die2 == 1)
    is_boxcars = (die1 == 6 and die2 == 6)
    
    prize_amount = 0
    prize_type = 'points'
    dollar_value = 0.0
    prize_description = None
    
    if win:
        # Select prize based on configured probabilities
        selected_prize = select_prize_by_probability(prizes)
        if selected_prize:
            prize_amount = selected_prize['prize_amount'] or 0
            prize_type = selected_prize['prize_type']
            prize_description = selected_prize['prize_description']
            dollar_value = getattr(selected_prize, 'dollar_value', 0.0) or 0.0
            
            # Special messaging for dice combinations
            if is_snake_eyes:
                prize_description = f"SNAKE EYES! {prize_description}"
            elif is_boxcars:
                prize_description = f"BOXCARS! {prize_description}"  
            elif is_lucky_seven:
                prize_description = f"LUCKY SEVEN! {prize_description}"
            elif is_double:
                prize_description = f"DOUBLE {die1}s! {prize_description}"
    
    return {
        'outcome': {
            'dice': [die1, die2],
            'total': total,
            'is_double': is_double,
            'is_lucky_seven': is_lucky_seven,
            'is_snake_eyes': is_snake_eyes,
            'is_boxcars': is_boxcars
        },
        'win': win,
        'prize_type': prize_type,
        'prize_amount': prize_amount,
        'prize_description': prize_description
    }


def play_generic_game(conn, config):
    """Fallback generic game with database-driven odds"""
    # Try to get odds from database, fallback to defaults
    try:
        odds, prizes = get_game_odds_and_prizes(conn, 'generic')
    except:
        odds = {'win_probability': 0.3, 'jackpot_probability': 0.05}
        prizes = [{'prize_type': 'points', 'prize_amount': 5, 'prize_description': '5 Points', 'probability': 0.2, 'is_jackpot': 0}]
    
    win_roll = random.random()
    win = win_roll < odds['win_probability']
    
    prize_amount = 0
    prize_type = 'points'
    dollar_value = 0.0
    prize_description = None
    
    if win:
        selected_prize = select_prize_by_probability(prizes)
        if selected_prize:
            prize_amount = selected_prize['prize_amount'] or 0
            prize_type = selected_prize['prize_type']
            prize_description = selected_prize['prize_description']
            dollar_value = getattr(selected_prize, 'dollar_value', 0.0) or 0.0
    
    return {
        'outcome': {'type': 'generic', 'roll': random.randint(1, 100)},
        'win': win,
        'prize_type': prize_type,
        'prize_amount': prize_amount,
        'prize_description': prize_description
    }


@app.route("/api/game-config")
def get_game_config():
    """API endpoint for game configuration"""
    try:
        with DatabaseConnection() as conn:
            settings = get_settings(conn)
            config = json.loads(settings.get('mini_game_settings', '{}'))
            return jsonify(config)
    except Exception as e:
        logging.error(f"Error getting game config: {e}")
        return jsonify({'error': 'Configuration unavailable'}), 500


# ===== ANALYTICS API ENDPOINTS =====

@app.route("/api/analytics/dashboard", methods=["GET"])
def get_dashboard_analytics():
    """Get comprehensive dashboard analytics data for trends display"""
    try:
        days = int(request.args.get('days', 30))
        
        with DatabaseConnection() as conn:
            # Employee score trends over time
            score_trends = conn.execute("""
                SELECT 
                    DATE(date) as date,
                    SUM(CASE WHEN points > 0 THEN points ELSE 0 END) as points_awarded,
                    SUM(CASE WHEN points < 0 THEN ABS(points) ELSE 0 END) as points_deducted,
                    COUNT(DISTINCT employee_id) as active_employees,
                    COUNT(*) as total_activities
                FROM score_history 
                WHERE date >= date('now', '-{} days')
                GROUP BY DATE(date)
                ORDER BY date DESC
                LIMIT 30
            """.format(days)).fetchall()
            
            # Top performers this week/month
            top_performers = conn.execute("""
                SELECT 
                    e.name,
                    e.score,
                    e.role,
                    e.employee_id,
                    SUM(CASE WHEN sh.points > 0 AND sh.date >= date('now', '-7 days') THEN sh.points ELSE 0 END) as weekly_points
                FROM employees e
                LEFT JOIN score_history sh ON e.employee_id = sh.employee_id
                WHERE e.active = 1
                GROUP BY e.employee_id, e.name, e.score, e.role
                ORDER BY e.score DESC, weekly_points DESC
                LIMIT 10
            """).fetchall()
            
            # Prize distribution statistics
            prize_distribution = conn.execute("""
                SELECT 
                    prize_type,
                    COUNT(*) as count,
                    COALESCE(SUM(dollar_value), 0) as total_value,
                    AVG(COALESCE(dollar_value, 0)) as avg_value
                FROM mini_game_payouts 
                WHERE payout_date >= date('now', '-{} days')
                GROUP BY prize_type
                ORDER BY total_value DESC
            """.format(days)).fetchall()
            
            # Voting participation trends
            voting_trends = conn.execute("""
                SELECT 
                    DATE(vs.start_time) as date,
                    COUNT(DISTINCT vr.employee_id) as participants,
                    COUNT(*) as total_votes,
                    CASE WHEN vs.end_time IS NULL THEN 'active' ELSE 'completed' END as status,
                    vs.session_id
                FROM voting_sessions vs
                LEFT JOIN voting_results vr ON vs.session_id = vr.session_id
                WHERE vs.start_time >= date('now', '-{} days')
                GROUP BY DATE(vs.start_time), vs.session_id
                ORDER BY date DESC
            """.format(days)).fetchall()
            
            # System engagement metrics
            engagement_metrics = conn.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM employees WHERE active = 1) as active_employees,
                    (SELECT COUNT(*) FROM mini_games WHERE played_date >= date('now', '-7 days')) as weekly_games,
                    (SELECT COUNT(*) FROM voting_sessions WHERE start_time >= date('now', '-7 days')) as weekly_voting_sessions,
                    (SELECT AVG(score) FROM employees WHERE active = 1) as avg_employee_score,
                    (SELECT SUM(dollar_value) FROM mini_game_payouts WHERE payout_date >= date('now', '-30 days')) as monthly_payout_value
            """).fetchone()
            
            return jsonify({
                "success": True,
                "analytics": {
                    "score_trends": [dict(row) for row in score_trends],
                    "top_performers": [dict(row) for row in top_performers],
                    "prize_distribution": [dict(row) for row in prize_distribution],
                    "voting_trends": [dict(row) for row in voting_trends],
                    "engagement_metrics": dict(engagement_metrics) if engagement_metrics else {},
                    "period_days": days
                }
            })
            
    except Exception as e:
        logging.error(f"Error getting dashboard analytics: {str(e)}")
        return jsonify({"success": False, "message": "Failed to get analytics"}), 500


@app.route("/api/analytics/minigames", methods=["GET"])
def get_minigames_analytics():
    """Get mini-games specific analytics"""
    try:
        days = int(request.args.get('days', 30))
        
        with DatabaseConnection() as conn:
            # Game play frequency over time
            game_frequency = conn.execute("""
                SELECT 
                    DATE(played_date) as date,
                    game_type,
                    COUNT(*) as games_played,
                    COUNT(DISTINCT employee_id) as unique_players
                FROM mini_games 
                WHERE played_date >= date('now', '-{} days')
                GROUP BY DATE(played_date), game_type
                ORDER BY date DESC, games_played DESC
            """.format(days)).fetchall()
            
            # Win/loss ratio trends by game type
            win_loss_ratios = conn.execute("""
                SELECT 
                    mg.game_type,
                    COUNT(*) as total_games,
                    COUNT(mp.id) as winning_games,
                    ROUND(CAST(COUNT(mp.id) AS FLOAT) / COUNT(*) * 100, 2) as win_rate_percent,
                    COUNT(*) - COUNT(mp.id) as losing_games
                FROM mini_games mg
                LEFT JOIN mini_game_payouts mp ON mg.id = mp.game_id
                WHERE mg.played_date >= date('now', '-{} days')
                GROUP BY mg.game_type
                ORDER BY win_rate_percent DESC
            """.format(days)).fetchall()
            
            # Prize payout trends
            payout_trends = conn.execute("""
                SELECT 
                    DATE(mp.payout_date) as date,
                    mp.game_type,
                    mp.prize_type,
                    COUNT(*) as payouts,
                    SUM(mp.dollar_value) as total_value,
                    AVG(mp.dollar_value) as avg_value
                FROM mini_game_payouts mp
                WHERE mp.payout_date >= date('now', '-{} days')
                GROUP BY DATE(mp.payout_date), mp.game_type, mp.prize_type
                ORDER BY date DESC, total_value DESC
            """.format(days)).fetchall()
            
            # Most popular games
            popular_games = conn.execute("""
                SELECT 
                    mg.game_type,
                    COUNT(*) as total_plays,
                    COUNT(DISTINCT mg.employee_id) as unique_players,
                    ROUND(AVG(CASE WHEN mp.id IS NOT NULL THEN 1.0 ELSE 0.0 END) * 100, 2) as win_rate,
                    COALESCE(SUM(mp.dollar_value), 0) as total_payout_value
                FROM mini_games mg
                LEFT JOIN mini_game_payouts mp ON mg.id = mp.game_id
                WHERE mg.played_date >= date('now', '-{} days')
                GROUP BY mg.game_type
                ORDER BY total_plays DESC
            """.format(days)).fetchall()
            
            return jsonify({
                "success": True,
                "analytics": {
                    "game_frequency": [dict(row) for row in game_frequency],
                    "win_loss_ratios": [dict(row) for row in win_loss_ratios],
                    "payout_trends": [dict(row) for row in payout_trends],
                    "popular_games": [dict(row) for row in popular_games],
                    "period_days": days
                }
            })
            
    except Exception as e:
        logging.error(f"Error getting minigames analytics: {str(e)}")
        return jsonify({"success": False, "message": "Failed to get analytics"}), 500


@app.route("/api/analytics/employee/<employee_id>", methods=["GET"])
def get_employee_analytics(employee_id):
    """Get individual employee performance analytics"""
    try:
        days = int(request.args.get('days', 90))
        
        with DatabaseConnection() as conn:
            # Employee basic info
            employee_info = conn.execute("""
                SELECT employee_id, name, score, role, active, created_at
                FROM employees 
                WHERE employee_id = ?
            """, (employee_id,)).fetchone()
            
            if not employee_info:
                return jsonify({"success": False, "message": "Employee not found"}), 404
            
            # Score history trends
            score_history = conn.execute("""
                SELECT 
                    DATE(date) as date,
                    points,
                    reason,
                    admin_id,
                    (SELECT SUM(points) FROM score_history sh2 WHERE sh2.employee_id = ? AND sh2.date <= sh.date) as running_total
                FROM score_history sh
                WHERE employee_id = ? AND date >= date('now', '-{} days')
                ORDER BY date DESC
            """.format(days), (employee_id, employee_id)).fetchall()
            
            # Game performance
            game_performance = conn.execute("""
                SELECT 
                    mg.game_type,
                    COUNT(*) as games_played,
                    COUNT(mp.id) as games_won,
                    COALESCE(SUM(mp.dollar_value), 0) as total_winnings,
                    ROUND(CAST(COUNT(mp.id) AS FLOAT) / COUNT(*) * 100, 2) as personal_win_rate
                FROM mini_games mg
                LEFT JOIN mini_game_payouts mp ON mg.id = mp.game_id
                WHERE mg.employee_id = ? AND mg.played_date >= date('now', '-{} days')
                GROUP BY mg.game_type
                ORDER BY games_played DESC
            """.format(days), (employee_id,)).fetchall()
            
            # Voting activity
            voting_activity = conn.execute("""
                SELECT 
                    COUNT(*) as votes_cast,
                    COUNT(DISTINCT session_id) as sessions_participated,
                    AVG(vote_value) as avg_vote_given
                FROM voting_results 
                WHERE voter_employee_id = ? AND created_at >= date('now', '-{} days')
            """.format(days), (employee_id,)).fetchone()
            
            # Recent achievements/milestones
            recent_activities = conn.execute("""
                SELECT 
                    date,
                    points,
                    reason,
                    'points' as activity_type
                FROM score_history 
                WHERE employee_id = ? AND date >= date('now', '-30 days')
                UNION ALL
                SELECT 
                    played_date as date,
                    COALESCE(mp.dollar_value, 0) as points,
                    'Won ' || mg.game_type || ' game' as reason,
                    'minigame' as activity_type
                FROM mini_games mg
                LEFT JOIN mini_game_payouts mp ON mg.id = mp.game_id
                WHERE mg.employee_id = ? AND mg.played_date >= date('now', '-30 days') AND mp.id IS NOT NULL
                ORDER BY date DESC
                LIMIT 20
            """, (employee_id, employee_id)).fetchall()
            
            return jsonify({
                "success": True,
                "employee": dict(employee_info),
                "analytics": {
                    "score_history": [dict(row) for row in score_history],
                    "game_performance": [dict(row) for row in game_performance],
                    "voting_activity": dict(voting_activity) if voting_activity else {},
                    "recent_activities": [dict(row) for row in recent_activities],
                    "period_days": days
                }
            })
            
    except Exception as e:
        logging.error(f"Error getting employee analytics: {str(e)}")
        return jsonify({"success": False, "message": "Failed to get analytics"}), 500


@app.route("/api/analytics/system-health", methods=["GET"])
def get_system_health_analytics():
    """Get system health and engagement analytics"""
    try:
        days = int(request.args.get('days', 30))
        
        with DatabaseConnection() as conn:
            # Overall engagement metrics
            engagement_stats = conn.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM employees WHERE active = 1) as total_active_employees,
                    (SELECT COUNT(*) FROM mini_games WHERE played_date >= date('now', '-7 days')) as games_this_week,
                    (SELECT COUNT(*) FROM voting_sessions WHERE created_at >= date('now', '-7 days')) as voting_sessions_this_week,
                    (SELECT COUNT(DISTINCT voter_employee_id) FROM voting_results WHERE created_at >= date('now', '-7 days')) as voting_participants_this_week,
                    (SELECT SUM(dollar_value) FROM mini_game_payouts WHERE payout_date >= date('now', '-30 days')) as monthly_payouts,
                    (SELECT AVG(score) FROM employees WHERE active = 1) as avg_employee_score,
                    (SELECT MAX(score) FROM employees WHERE active = 1) as highest_score,
                    (SELECT COUNT(*) FROM score_history WHERE date >= date('now', '-7 days') AND points > 0) as positive_adjustments_this_week,
                    (SELECT COUNT(*) FROM score_history WHERE date >= date('now', '-7 days') AND points < 0) as negative_adjustments_this_week
            """).fetchone()
            
            # Daily activity patterns
            daily_activity = conn.execute("""
                SELECT 
                    DATE(activity_date) as date,
                    SUM(games_played) as games_played,
                    SUM(votes_cast) as votes_cast,
                    SUM(points_awarded) as points_awarded,
                    SUM(active_users) as active_users
                FROM (
                    SELECT 
                        DATE(played_date) as activity_date,
                        COUNT(*) as games_played,
                        0 as votes_cast,
                        0 as points_awarded,
                        COUNT(DISTINCT employee_id) as active_users
                    FROM mini_games 
                    WHERE played_date >= date('now', '-{} days')
                    GROUP BY DATE(played_date)
                    
                    UNION ALL
                    
                    SELECT 
                        DATE(created_at) as activity_date,
                        0 as games_played,
                        COUNT(*) as votes_cast,
                        0 as points_awarded,
                        COUNT(DISTINCT voter_employee_id) as active_users
                    FROM voting_results 
                    WHERE created_at >= date('now', '-{} days')
                    GROUP BY DATE(created_at)
                    
                    UNION ALL
                    
                    SELECT 
                        DATE(date) as activity_date,
                        0 as games_played,
                        0 as votes_cast,
                        SUM(CASE WHEN points > 0 THEN points ELSE 0 END) as points_awarded,
                        COUNT(DISTINCT employee_id) as active_users
                    FROM score_history 
                    WHERE date >= date('now', '-{} days')
                    GROUP BY DATE(date)
                ) activities
                GROUP BY DATE(activity_date)
                ORDER BY date DESC
            """.format(days, days, days)).fetchall()
            
            # ROI analytics for prize programs
            roi_analytics = conn.execute("""
                SELECT 
                    prize_type,
                    COUNT(*) as total_prizes_awarded,
                    SUM(dollar_value) as total_cost,
                    AVG(dollar_value) as avg_prize_value,
                    COUNT(DISTINCT employee_id) as employees_benefited
                FROM mini_game_payouts 
                WHERE payout_date >= date('now', '-{} days')
                GROUP BY prize_type
                ORDER BY total_cost DESC
            """.format(days)).fetchall()
            
            # Usage patterns by time
            usage_patterns = conn.execute("""
                SELECT 
                    strftime('%H', played_date) as hour,
                    COUNT(*) as activity_count,
                    'minigames' as activity_type
                FROM mini_games 
                WHERE played_date >= date('now', '-30 days')
                GROUP BY strftime('%H', played_date)
                
                UNION ALL
                
                SELECT 
                    strftime('%H', created_at) as hour,
                    COUNT(*) as activity_count,
                    'voting' as activity_type
                FROM voting_results 
                WHERE created_at >= date('now', '-30 days')
                GROUP BY strftime('%H', created_at)
                
                ORDER BY hour, activity_type
            """).fetchall()
            
            return jsonify({
                "success": True,
                "analytics": {
                    "engagement_stats": dict(engagement_stats) if engagement_stats else {},
                    "daily_activity": [dict(row) for row in daily_activity],
                    "roi_analytics": [dict(row) for row in roi_analytics],
                    "usage_patterns": [dict(row) for row in usage_patterns],
                    "period_days": days
                }
            })
            
    except Exception as e:
        logging.error(f"Error getting system health analytics: {str(e)}")
        return jsonify({"success": False, "message": "Failed to get analytics"}), 500


@app.errorhandler(500)
def internal_error(e):
    logging.error(f"500 error: {e}")
    return render_template('error.html', error="🎰 JACKPOT JAM! Tech gremlins invaded the casino—retry your spin! 🎰"), 500


if __name__ == "__main__":
    logging.debug("Running Flask app in debug mode")
    app.run(host="0.0.0.0", port=6800, debug=True)
else:
    logging.debug("Running Flask app under Gunicorn")