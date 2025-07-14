from flask import Blueprint, render_template, request, jsonify
from collections import defaultdict
from db_connection import DatabaseConnection
from data_service import get_active_rental_contracts, get_active_rental_items
import logging

tab1_bp = Blueprint("tab1", __name__, url_prefix="/tab1")
logging.basicConfig(level=logging.DEBUG)

@tab1_bp.route("/")
def show_tab1():
    page = request.args.get("page", 1, type=int)
    per_page = 10
    filter_contract = request.args.get("last_contract_num", "").lower().strip()
    filter_common = request.args.get("common_name", "").lower().strip()
    sort = request.args.get("sort", "last_contract_num:asc")

    try:
        with DatabaseConnection() as conn:
            contracts = get_active_rental_contracts(conn, filter_contract, filter_common, sort)
            items = get_active_rental_items(conn, filter_contract, filter_common, sort)
        
        parent_data = [
            {"contract": c["last_contract_num"], "client_name": c["client_name"], 
             "total": 0, "scan_date": c["scan_date"], "transaction_notes": c["transaction_notes"]}
            for c in contracts
        ]

        total_items = len(parent_data)
        total_pages = (total_items + per_page - 1) // per_page
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        end = start + per_page
        parent_data = parent_data[start:end]

        child_map = defaultdict(dict)
        for item in items:
            contract = item["last_contract_num"]
            rental_class_id = item["rental_class_id"] or "unknown"
            common_name = item["common_name"]
            if contract in [p["contract"] for p in parent_data]:
                if rental_class_id not in child_map[contract]:
                    child_map[contract][rental_class_id] = {
                        "common_name": common_name,
                        "total": 0,
                        "available": 0,
                        "on_rent": 0,
                        "service": 0
                    }
                totals = child_map[contract][rental_class_id]
                totals["total"] += 1
                if item["status"] == "Ready to Rent":
                    totals["available"] += 1
                elif item["status"] in ["On Rent", "Delivered"]:
                    totals["on_rent"] += 1
                else:
                    totals["service"] += 1
                parent_idx = [p["contract"] for p in parent_data].index(contract)
                parent_data[parent_idx]["total"] += 1

        logging.debug(f"Tab 1 rendered: {len(parent_data)} parents, child_map keys: {list(child_map.keys())}")
        return render_template(
            "tab1.html",
            parent_data=parent_data,
            child_map=child_map,
            filter_contract=filter_contract,
            filter_common=filter_common,
            current_page=page,
            total_pages=total_pages,
            sort=sort
        )
    except Exception as e:
        logging.error(f"Error in show_tab1: {e}")
        return "Internal Server Error", 500

@tab1_bp.route("/data")
def subcat_data():
    contract = request.args.get("contract")
    common_name = request.args.get("common_name")
    page = request.args.get("page", 1, type=int)
    per_page = 20

    try:
        logging.debug(f"Fetching subcat data: contract={contract}, common_name={common_name}, page={page}")
        with DatabaseConnection() as conn:
            items = get_active_rental_items(conn)
        
        # Ensure items is a list of dicts
        items = [dict(item) for item in items]
        logging.debug(f"Total items fetched: {len(items)}")
        
        filtered_items = [
            item for item in items
            if item["last_contract_num"] == contract and item["common_name"] == common_name
        ]
        logging.debug(f"Filtered items: {len(filtered_items)}")

        total_items = len(filtered_items)
        total_pages = (total_items + per_page - 1) // per_page
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        end = start + per_page
        paginated_items = filtered_items[start:end]

        response = {
            "items": [{
                "tag_id": item["tag_id"],
                "common_name": item["common_name"],
                "status": item["status"],
                "bin_location": item.get("bin_location", "N/A"),
                "quality": item.get("quality", "N/A"),
                "last_contract_num": item["last_contract_num"],
                "date_last_scanned": item.get("date_last_scanned", "N/A"),
                "last_scanned_by": item.get("last_scanned_by", "N/A"),
                "notes": item.get("notes", "N/A")
            } for item in paginated_items],
            "total_items": total_items,
            "total_pages": total_pages,
            "current_page": page
        }
        logging.debug(f"Subcat data response: {response}")
        return jsonify(response)
    except Exception as e:
        logging.error(f"Error in subcat_data: {e}")
        return "Internal Server Error", 500