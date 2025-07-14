from flask import Blueprint, render_template, request
from collections import defaultdict
from db_connection import DatabaseConnection

tab4_bp = Blueprint("tab4_bp", __name__, url_prefix="/tab4")

@tab4_bp.route("/")
def show_tab4():
    with DatabaseConnection() as conn:
        rows = conn.execute("SELECT * FROM id_item_master ORDER BY common_name").fetchall()
    items = [dict(row) for row in rows]

    # Get filter parameters from URL
    filter_common_name = request.args.get("common_name", "").lower().strip()
    filter_tag_id = request.args.get("tag_id", "").lower().strip()
    filter_bin_location = request.args.get("bin_location", "").lower().strip()
    filter_last_contract = request.args.get("last_contract_num", "").lower().strip()
    filter_status = request.args.get("status", "").lower().strip()

    # Filter items based on all parameters
    filtered_items = items
    if filter_common_name:
        filtered_items = [item for item in filtered_items if filter_common_name in (item.get("common_name") or "").lower()]
    if filter_tag_id:
        filtered_items = [item for item in filtered_items if filter_tag_id in (item.get("tag_id") or "").lower()]
    if filter_bin_location:
        filtered_items = [item for item in filtered_items if filter_bin_location in (item.get("bin_location") or "").lower()]
    if filter_last_contract:
        filtered_items = [item for item in filtered_items if filter_last_contract in (item.get("last_contract_num") or "").lower()]
    if filter_status:
        filtered_items = [item for item in filtered_items if filter_status in (item.get("status") or "").lower()]

    # Group by common_name
    item_map = defaultdict(list)
    for item in filtered_items:
        common_name = item.get("common_name", "Unknown")
        item_map[common_name].append(item)

    # Build parent_data
    parent_data = [
        {"common_name": name, "total": len(items)}
        for name, items in item_map.items()
    ]
    parent_data.sort(key=lambda x: x["common_name"])

    # Pagination
    per_page = 20
    total_items = len(parent_data)
    total_pages = (total_items + per_page - 1) // per_page
    page = request.args.get("page", 1, type=int)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    paginated_data = parent_data[start:end]

    return render_template(
        "tab4.html",
        parent_data=paginated_data,
        item_map=item_map,
        current_page=page,
        total_pages=total_pages,
        filter_common_name=filter_common_name,
        filter_tag_id=filter_tag_id,
        filter_bin_location=filter_bin_location,
        filter_last_contract=filter_last_contract,
        filter_status=filter_status
    )
