from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from collections import defaultdict
from db_connection import DatabaseConnection
from data_service import get_active_rental_contracts, get_active_rental_items
import sqlite3
import os
import logging

tab5_bp = Blueprint("tab5_bp", __name__, url_prefix="/tab5")
HAND_COUNTED_DB = "/home/tim/test_rfidpi/tab5_hand_counted.db"
logging.basicConfig(level=logging.DEBUG)

def init_hand_counted_db():
    try:
        if not os.path.exists(HAND_COUNTED_DB):
            conn = sqlite3.connect(HAND_COUNTED_DB, timeout=10)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hand_counted_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    last_contract_num TEXT,
                    common_name TEXT,
                    total_items INTEGER,
                    tag_id TEXT DEFAULT NULL,
                    date_last_scanned TEXT,
                    last_scanned_by TEXT
                )
            """)
            conn.commit()
            conn.close()
            logging.debug("Initialized tab5_hand_counted.db")
        os.chmod(HAND_COUNTED_DB, 0o666)
    except Exception as e:
        logging.error(f"Error initializing tab5_hand_counted.db: {e}")

@tab5_bp.route("/")
def show_tab5():
    logging.debug("Loading /tab5/ endpoint")
    init_hand_counted_db()

    try:
        with DatabaseConnection() as conn:
            logging.debug("Fetching RFID data")
            contracts = get_active_rental_contracts(conn)
            all_items = conn.execute("SELECT * FROM id_item_master").fetchall()
            active_items = get_active_rental_items(conn)

        with sqlite3.connect(HAND_COUNTED_DB, timeout=10) as conn:
            logging.debug("Fetching hand-counted data")
            conn.row_factory = sqlite3.Row
            hand_counted_items = conn.execute("SELECT * FROM hand_counted_items WHERE last_contract_num LIKE 'L%'").fetchall()

        all_items = [dict(row) for row in all_items]
        laundry_items = [
            item for item in [dict(row) for row in active_items]
            if item.get("last_contract_num", "").lower().startswith("l")
        ]
        hand_counted = [dict(row) for row in hand_counted_items] if hand_counted_items else []

        filter_contract = request.args.get("last_contract_num", "").lower().strip()
        filter_common_name = request.args.get("common_name", "").lower().strip()

        filtered_items = laundry_items
        if filter_contract:
            filtered_items = [item for item in filtered_items if filter_contract in item["last_contract_num"].lower()]
        if filter_common_name:
            filtered_items = [item for item in filtered_items if filter_common_name in item.get("common_name", "").lower()]

        logging.debug("Merging data")
        contract_map = defaultdict(list)
        for item in filtered_items:
            contract = item.get("last_contract_num", "Unknown")
            contract_map[contract].append(item)
        for item in hand_counted:
            contract = item.get("last_contract_num", "Unknown")
            contract_map[contract].append(item)

        parent_data = []
        child_map = {}
        for contract, item_list in contract_map.items():
            logging.debug(f"Processing contract: {contract}")
            rental_class_map = defaultdict(list)
            for item in item_list:
                rental_class_id = item.get("rental_class_id", "unknown")
                rental_class_map[rental_class_id].append(item)

            child_data = {}
            for rental_class_id, items in rental_class_map.items():
                common_name = items[0]["common_name"]
                rfid_items = [i for i in items if i.get("tag_id") is not None]
                hand_items = [i for i in items if i.get("tag_id") is None]
                total_rfid = len(rfid_items)
                total_hand = sum(int(i.get("total_items", 0)) for i in hand_items)
                total_items = total_rfid + total_hand
                total_available = sum(1 for item in all_items if item["common_name"] == common_name and item["status"] == "Ready to Rent")
                on_rent = sum(1 for item in all_items if item["common_name"] == common_name and 
                              item["status"] in ["On Rent", "Delivered"] and 
                              (item.get("last_contract_num", "") and not item["last_contract_num"].lower().startswith("l")))
                service = total_rfid - sum(1 for item in rfid_items if item.get("status") == "Ready to Rent") - \
                          sum(1 for item in rfid_items if item.get("status", "") in ["On Rent", "Delivered"]) if rfid_items else 0
                child_data[rental_class_id] = {
                    "common_name": common_name,
                    "total": total_items,
                    "available": total_available,
                    "on_rent": on_rent,
                    "service": service,
                    "items": rfid_items + hand_items
                }

            rfid_total = len([i for i in item_list if i.get("tag_id") is not None])
            hand_total = sum(int(i.get("total_items", 0)) for i in item_list if i.get("tag_id") is None)
            # Get client_name and scan_date from contracts or first RFID item
            contract_info = next((c for c in contracts if c["last_contract_num"] == contract), None)
            client_name = contract_info["client_name"] if contract_info else "N/A"
            scan_date = contract_info["scan_date"] if contract_info else (item_list[0]["date_last_scanned"] if item_list and item_list[0].get("date_last_scanned") else "N/A")
            parent_data.append({
                "contract": contract,
                "total": rfid_total + hand_total,
                "client_name": client_name,
                "scan_date": scan_date
            })
            child_map[contract] = child_data

        logging.debug("Sorting parent data")
        parent_data.sort(key=lambda x: x["contract"].lower())

        logging.debug("Rendering Tab 5")
        return render_template(
            "tab5.html",
            parent_data=parent_data,
            child_map=child_map,
            filter_contract=filter_contract,
            filter_common_name=filter_common_name
        )
    except Exception as e:
        logging.error(f"Error in show_tab5: {e}")
        return "Internal Server Error", 500

@tab5_bp.route("/save_hand_counted", methods=["POST"])
def save_hand_counted():
    logging.debug("Saving hand-counted entry")
    try:
        common_name = request.form.get("common_name")
        last_contract_num = request.form.get("last_contract_num")
        total_items = int(request.form.get("total_items", 0))
        last_scanned_by = request.form.get("last_scanned_by")
        date_last_scanned = request.form.get("date_last_scanned")

        with sqlite3.connect(HAND_COUNTED_DB, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO hand_counted_items (last_contract_num, common_name, total_items, tag_id, date_last_scanned, last_scanned_by)
                VALUES (?, ?, ?, NULL, ?, ?)
            """, (last_contract_num, common_name, total_items, date_last_scanned, last_scanned_by))
            conn.commit()

        return redirect(url_for("tab5_bp.show_tab5", last_contract_num=request.args.get("last_contract_num", ""), common_name=request.args.get("common_name", "")))
    except Exception as e:
        logging.error(f"Error saving hand-counted entry: {e}")
        return "Internal Server Error", 500

@tab5_bp.route("/update_hand_counted", methods=["POST"])
def update_hand_counted():
    logging.debug("Updating hand-counted entry")
    try:
        common_name = request.form.get("common_name")
        last_contract_num = request.form.get("last_contract_num")
        returned_qty = int(request.form.get("total_items", 0))
        last_scanned_by = request.form.get("last_scanned_by")
        date_last_scanned = request.form.get("date_last_scanned")

        if not last_contract_num.startswith("L"):
            logging.error(f"Invalid contract: {last_contract_num} must start with 'L'")
            return "Contract must start with 'L'", 400

        with sqlite3.connect(HAND_COUNTED_DB, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, total_items FROM hand_counted_items 
                WHERE last_contract_num = ? AND common_name = ?
            """, (last_contract_num, common_name))
            row = cursor.fetchone()

            if not row:
                logging.error(f"No matching L contract found: {last_contract_num}, {common_name}")
                return "No matching L contract found", 404

            orig_id, orig_total = row["id"], int(row["total_items"])
            new_total = orig_total - returned_qty

            if new_total < 0:
                logging.error(f"Returned quantity {returned_qty} exceeds original {orig_total}")
                return "Returned quantity exceeds original total", 400

            if new_total == 0:
                cursor.execute("DELETE FROM hand_counted_items WHERE id = ?", (orig_id,))
            else:
                cursor.execute("""
                    UPDATE hand_counted_items SET total_items = ? 
                    WHERE id = ?
                """, (new_total, orig_id))

            closed_contract = "C" + last_contract_num[1:]
            cursor.execute("""
                INSERT INTO hand_counted_items (last_contract_num, common_name, total_items, tag_id, date_last_scanned, last_scanned_by)
                VALUES (?, ?, ?, NULL, ?, ?)
            """, (closed_contract, common_name, returned_qty, date_last_scanned, last_scanned_by))

            conn.commit()

        return redirect(url_for("tab5_bp.show_tab5", last_contract_num=request.args.get("last_contract_num", ""), common_name=request.args.get("common_name", "")))
    except Exception as e:
        logging.error(f"Error updating hand-counted entry: {e}")
        return "Internal Server Error", 500

@tab5_bp.route("/subcat_data", methods=["GET"])
def subcat_data():
    logging.debug("Hit /tab5/subcat_data endpoint")
    try:
        contract = request.args.get('contract')
        common_name = request.args.get('common_name')
        page = int(request.args.get('page', 1))
        per_page = 20
    except ValueError:
        page = 1
        per_page = 20

    with DatabaseConnection() as conn:
        items = get_active_rental_items(conn)

    with sqlite3.connect(HAND_COUNTED_DB, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        hand_items = conn.execute("SELECT * FROM hand_counted_items WHERE last_contract_num LIKE 'L%' AND last_contract_num = ? AND common_name = ?", 
                                  (contract, common_name)).fetchall()

    laundry_items = [
        item for item in [dict(row) for row in items]
        if item.get("last_contract_num", "").lower().startswith("l")
    ]
    hand_counted = [dict(row) for row in hand_items]

    filter_contract = request.args.get("last_contract_num", "").lower().strip()
    filter_common_name = request.args.get("common_name_filter", "").lower().strip()

    filtered_items = laundry_items + hand_counted
    if filter_contract:
        filtered_items = [item for item in filtered_items if filter_contract in item["last_contract_num"].lower()]
    if filter_common_name:
        filtered_items = [item for item in filtered_items if filter_common_name in item.get("common_name", "").lower()]

    subcat_items = [
        item for item in filtered_items
        if item.get("last_contract_num") == contract and item.get("common_name") == common_name
    ]

    total_items = len(subcat_items)
    total_pages = (total_items + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    paginated_items = subcat_items[start:end]

    logging.debug(f"AJAX: Contract: {contract}, Common Name: {common_name}, Total Items: {total_items}, Page: {page}")

    return jsonify({
        "items": [{
            "tag_id": item.get("tag_id", "N/A"),
            "common_name": item["common_name"],
            "status": item.get("status", "Hand Counted"),
            "bin_location": item.get("bin_location", "N/A"),
            "quality": item.get("quality", "N/A"),
            "last_contract_num": item["last_contract_num"],
            "date_last_scanned": item.get("date_last_scanned", "N/A"),
            "last_scanned_by": item.get("last_scanned_by", "Unknown"),
            "notes": item.get("notes", "N/A"),
            "client_name": item.get("client_name", "N/A")
        } for item in paginated_items],
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page
    })
