from flask import Flask, request, url_for, jsonify
from refresh_logic import IS_RELOADING, LAST_REFRESH
from db_connection import DatabaseConnection

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    from app.routes.root import root_bp
    from app.routes.tab1 import tab1_bp
    from app.routes.tab2 import tab2_bp
    from app.routes.tab3 import tab3_bp
    from app.routes.tab4 import tab4_bp
    from app.routes.tab5 import tab5_bp
    from app.routes.tab6 import tab6_bp

    app.register_blueprint(root_bp)
    app.register_blueprint(tab1_bp, url_prefix="/tab1")
    app.register_blueprint(tab2_bp, url_prefix="/tab2")
    app.register_blueprint(tab3_bp, url_prefix="/tab3")
    app.register_blueprint(tab4_bp, url_prefix="/tab4")
    app.register_blueprint(tab5_bp, url_prefix="/tab5")
    app.register_blueprint(tab6_bp, url_prefix="/tab6")

    @app.route('/status', methods=['GET'])
    def status():
        return jsonify({"is_reloading": IS_RELOADING}), 200

    @app.route('/new_items', methods=['GET'])
    def new_items():
        if not LAST_REFRESH:
            return jsonify({"items": [], "transactions": []}), 200

        since_date = LAST_REFRESH.strftime("%Y-%m-%d %H:%M:%S")
        with DatabaseConnection() as conn:
            # New items from id_item_master
            items_query = """
                SELECT * FROM id_item_master 
                WHERE date_updated >= ? OR date_last_scanned >= ?
            """
            new_items = conn.execute(items_query, (since_date, since_date)).fetchall()
            new_items = [dict(row) for row in new_items]

            # New transactions from id_transactions
            trans_query = """
                SELECT * FROM id_transactions 
                WHERE date_updated >= ? OR scan_date >= ?
            """
            new_trans = conn.execute(trans_query, (since_date, since_date)).fetchall()
            new_trans = [dict(row) for row in new_trans]

        return jsonify({
            "items": new_items,
            "transactions": new_trans,
            "since": since_date
        }), 200

    @app.context_processor
    def utility_processor():
        def update_url_param(key, value):
            args = request.args.copy()
            args[key] = value
            return url_for(request.endpoint, **args)
        return dict(update_url_param=update_url_param)

    return app