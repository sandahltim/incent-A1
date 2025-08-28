# app_modular.py
# Modular Flask application structure
# Version: 2.0.0 - Refactored modular architecture

from flask import Flask, render_template, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from flask_wtf.csrf import CSRFProtect, CSRFError
from incentive_service import DatabaseConnection, get_settings
from config import Config
from forms import LogoutForm
import logging
from logging_config import setup_logging
import time
import traceback
from datetime import datetime, timedelta
import threading
import os
import json

# Import utilities and services
from utils.helpers import from_json, get_score_class, get_role_key_map, make_session_permanent
from services.cache import data_cache
from services.auth import check_admin_session, clear_admin_session

# Import route blueprints
from routes.main import main_bp
from routes.voting import voting_bp

# Setup logging
setup_logging()
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
logging.debug("Modular application starting, initializing Flask app")

# Initialize Flask app
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object('config.Config')
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Add Jinja filters
app.jinja_env.filters['zip'] = zip
app.jinja_env.filters['from_json'] = from_json

# Validate database file existence
if not os.path.exists(Config.INCENTIVE_DB_FILE):
    logging.error(f"Database file not found: {Config.INCENTIVE_DB_FILE}")
    raise FileNotFoundError(f"Database file not found: {Config.INCENTIVE_DB_FILE}")

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(voting_bp)


# Context processor to inject settings and global forms
@app.context_processor
def inject_globals():
    """Inject global template variables."""
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
    """Background thread to handle daily point decay."""
    logging.debug("Starting point_decay_thread")
    last_checked = None
    while True:
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        if last_checked != current_date:
            try:
                with DatabaseConnection() as conn:
                    from incentive_service import get_point_decay, deduct_points_daily
                    decay_settings = get_point_decay(conn)
                    if decay_settings['enabled']:
                        logging.debug(f"Running daily point decay: {decay_settings}")
                        deduct_points_daily(conn, decay_settings['percentage'])
                        data_cache.clear()  # Clear cache after point changes
                last_checked = current_date
            except Exception as e:
                logging.error(f"Error in point decay thread: {e}")
        time.sleep(3600)  # Check every hour


# Start background thread
decay_thread = threading.Thread(target=point_decay_thread, daemon=True)
decay_thread.start()


# Session cleanup
@app.before_request
def before_request():
    """Handle session management and cleanup."""
    make_session_permanent()
    
    # Check admin session timeout
    if 'admin_id' in session and 'last_activity' in session:
        try:
            last_activity = datetime.fromisoformat(session['last_activity'])
            if (datetime.now() - last_activity).total_seconds() > 7200:
                clear_admin_session()
                session.pop('last_activity', None)
                flash("Session expired. Please log in again.", "danger")
                return redirect(url_for('admin'))
            session['last_activity'] = datetime.now().isoformat()
        except Exception as e:
            logging.error(f"Error in session check: {str(e)}\n{traceback.format_exc()}")
            clear_admin_session()
            session.pop('last_activity', None)
            flash("Session error. Please log in again.", "danger")


# Error handlers
@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors."""
    logging.error(f"500 error: {e}")
    return render_template('error.html', error="🎰 JACKPOT JAM! Tech gremlins invaded the casino—retry your spin! 🎰"), 500


@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    """Handle CSRF errors."""
    logging.warning(f"CSRF error: {e}")
    flash("Security token expired. Please try again.", "warning")
    return render_template('error.html', error="Security token expired. Please refresh the page and try again."), 400


if __name__ == "__main__":
    logging.debug("Running modular Flask app in debug mode")
    app.run(host="0.0.0.0", port=6800, debug=True)