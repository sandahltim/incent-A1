# routes/main.py
# Main application routes - home page, data endpoints

import time
import logging
import traceback
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, send_file
from incentive_service import (
    DatabaseConnection, get_scoreboard, is_voting_active, get_rules, get_pot_info,
    get_roles, get_voting_results, get_unread_feedback_count, get_settings,
    get_recent_admin_adjustments
)
from config import Config
from forms import VoteForm, FeedbackForm, QuickAdjustForm, LogoutForm
from utils.helpers import get_score_class, get_role_key_map
from services.cache import data_cache

try:
    from caching_service import get_cache_manager, get_cache_warmer
    CACHING_AVAILABLE = True
except ImportError:
    CACHING_AVAILABLE = False
    logging.warning("Advanced caching service not available")

main_bp = Blueprint('main', __name__)


@main_bp.route("/", methods=["GET"])
def show_incentive():
    """Main incentive scoreboard page."""
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


@main_bp.route("/data", methods=["GET"])
def incentive_data():
    """API endpoint for scoreboard data."""
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
        
        # Check simple cache
        cached_data = data_cache.get()
        if cached_data is not None:
            request_time = time.time() - start_time
            logging.debug(f"Returning cached data in {request_time:.3f} seconds")
            return jsonify(cached_data)
        
        # Generate fresh data
        with DatabaseConnection() as conn:
            scoreboard = get_scoreboard(conn)
            voting_active = is_voting_active(conn)
            settings = get_settings(conn)
            
            data = {
                "scoreboard": [dict(row) for row in scoreboard],
                "voting_active": voting_active,
                "timestamp": time.time(),
                "settings": {
                    "scoreboard_refresh_interval": int(settings.get('scoreboard_refresh_interval', 60)),
                    "sound_on": settings.get('sound_on', '1'),
                    "strobe_mode": settings.get('strobe_mode', 'on'),
                    "scoreboard_spin_duration": int(settings.get('scoreboard_spin_duration', 10)),
                    "scoreboard_spin_iterations": int(settings.get('scoreboard_spin_iterations', 0)),
                    "scoreboard_spin_pause": int(settings.get('scoreboard_spin_pause', 0)),
                    "scoreboard_spin_delay": int(settings.get('scoreboard_spin_delay', 0)),
                    "banner_text": settings.get('banner_text', "JACKPOT TIME! GIVE 'EM THE MONEY! SLOTS SPINNING - WINNERS GRINNING!")
                }
            }
        
        # Cache the data
        data_cache.set(data)
        
        if CACHING_AVAILABLE and Config.CACHE_ENABLED:
            try:
                cache = get_cache_manager()
                cache.set('api_data', data, ttl=60)
            except Exception as e:
                logging.warning(f"Failed to cache API data: {e}")
        
        request_time = time.time() - start_time
        logging.debug(f"Generated fresh data in {request_time:.3f} seconds")
        return jsonify(data)
        
    except Exception as e:
        logging.error(f"Error in incentive_data: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": "Internal server error"}), 500


@main_bp.route("/favicon.ico")
def favicon():
    """Serve favicon."""
    try:
        return send_file("static/favicon.ico", mimetype="image/vnd.microsoft.icon")
    except FileNotFoundError:
        return "", 404