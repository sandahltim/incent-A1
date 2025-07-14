from flask import Blueprint, render_template, request, jsonify
from collections import defaultdict
from db_connection import DatabaseConnection

tab6_bp = Blueprint("tab6_bp", __name__, url_prefix="/tab6")

def get_resale_items(conn):
    query = """
       SELECT * FROM id_item_master
       WHERE LOWER(bin_location) = 'resale'
       ORDER BY last_contract_num, tag_id
    """
    return conn.execute(query).fetchall()

def categorize_item(item):
    common_name = item.get("common_name", "").upper()
    if "FOG"  in common_name or "JUICE"  in common_name:
        return "A/V Resale"
    elif "CHOCOLATE" in common_name:
        return "Chocolate Resale"
    elif "COTTON CANDY" in common_name or "COTTON CANDY BAGS" in common_name:
        return "Cotton Candy Resale"
    elif "FUEL STERNO" in common_name or "BUTANE CARTRIDGE 8 OUNCE" in common_name or "AISLE CLOTH" in common_name or "GARBAGE CAN" in common_name:
        return "Disposable Resale"
    elif "POPCORN" in common_name or "NACHO CHEESE" in common_name or "DONUT" in common_name or "MINI DONUT" in common_name:
        return "Popcorn-Cheese-Donut Resale"
    elif "FRUSHEEZE" in common_name:
        return "Slushie Resale"
    elif "SNOKONE" in common_name:
        return "SnoKone Resale"
    elif "8 X 30" in common_name:
        return "8ft Banq KwikCovers"
    elif "6 X 30" in common_name:
        return "6ft Banq KwikCovers"
    elif "ROUND 60" in common_name:
        return "60\" Rd KwikCovers"
    elif "ROUND 48" in common_name:
        return "48\" Rd KwikCovers"
    elif "ROUND 30" in common_name or "ROUND 36" in common_name:
        return "30\"/36\" Rd KwikCovers"
    return "Other"

@tab6_bp.route("/")
def show_tab6():
    print("Loading /tab6/ endpoint")
    with DatabaseConnection() as conn:
        rows = get_resale_items(conn)
    items = [dict(row) for row in rows]

    # Get filter parameters (exact match)
    filter_common_name = request.args.get("common_name", "").strip()
    filter_tag_id = request.args.get("tag_id", "").strip()
    filter_last_contract = request.args.get("last_contract_num", "").strip()
    filter_status = request.args.get("status", "").strip()
    filter_rental_class_num = request.args.get("rental_class_num", "").strip()

    # Filter items (exact match)
    filtered_items = items
    if filter_common_name:
        filtered_items = [item for item in filtered_items if item.get("common_name") == filter_common_name]
    if filter_tag_id:
        filtered_items = [item for item in filtered_items if item.get("tag_id") == filter_tag_id]
    if filter_last_contract:
        filtered_items = [item for item in filtered_items if item.get("last_contract_num") == filter_last_contract]
    if filter_status:
        filtered_items = [item for item in filtered_items if item.get("status") == filter_status]
    if filter_rental_class_num:
        rental_class_nums = [num.strip() for num in filter_rental_class_num.split(',') if num.strip()]
        if not rental_class_nums:  # Full list from your data
            rental_class_nums = [
                "64815", "64816", "64817", "3168", "3169", "64840", "64841", "64842", "64843", "64847", "64848", "64849",
                "64819", "64824", "64836", "64837", "64876", "3903", "64852", "64853", "64854", "66742", "66743", "66747",
                "64864", "64865", "64866", "64867", "64868", "64869", "64874", "64855", "64856", "64857", "64858", "64860",
                "64861", "65808", "63442", "64921", "64922", "64923", "64924", "64925", "64926", "64927", "64928", "64929",
                "64930", "64932", "64933", "64934", "65493", "65496", "64935", "64936", "64937", "64938", "64939", "64940",
                "64941", "64942", "64943", "64944", "64945", "64946", "64947", "64948", "64949", "65494", "65497", "64888",
                "64889", "64890", "64891", "64892", "64893", "65604", "65605", "65606", "65607", "65608", "65609", "63440",
                "64894", "64895", "64896", "64897", "64898", "64899", "64900", "64901", "64902", "64904", "64905", "65611",
                "64906", "64907", "64908", "64909", "64910", "64911", "64912", "64913", "64914", "64915", "64916", "64917",
                "64918", "64919", "64920", "65495", "65498"
            ]
        filtered_items = [item for item in filtered_items if item.get("rental_class_num") in rental_class_nums]

    # Group by category
    category_map = defaultdict(list)
    for item in filtered_items:
        cat = categorize_item(item)
        category_map[cat].append(item)

    # Parent data (categories)
    parent_data = []
    middle_map = {}
    for category, item_list in category_map.items():
        total_amount = len(item_list)
        on_contract = sum(1 for item in item_list if item["status"] in ["Delivered", "On Rent"])

        # Middle child: Common names
        common_name_map = defaultdict(list)
        for item in item_list:
            common_name = item.get("common_name", "Unknown")
            common_name_map[common_name].append(item)
        middle_map[category] = [
            {"common_name": name, "total": len(items)}
            for name, items in common_name_map.items()
        ]

        parent_data.append({
            "category": category,
            "total_amount": total_amount,
            "on_contract": on_contract
        })

    parent_data.sort(key=lambda x: x["category"])

    return render_template(
        "tab6.html",
        parent_data=parent_data,
        middle_map=middle_map,
        filter_common_name=filter_common_name,
        filter_tag_id=filter_tag_id,
        filter_last_contract=filter_last_contract,
        filter_status=filter_status,
        filter_rental_class_num=filter_rental_class_num
    )

@tab6_bp.route("/subcat_data", methods=["GET"])
def subcat_data():
    print("Hit /tab6/subcat_data endpoint")
    category = request.args.get('category')
    common_name = request.args.get('common_name')
    page = int(request.args.get('page', 1))
    per_page = 20

    with DatabaseConnection() as conn:
        rows = get_resale_items(conn)
    items = [dict(row) for row in rows]

    # Apply filters from query params (exact match)
    filter_common_name = request.args.get("common_name_filter", "").strip()
    filter_tag_id = request.args.get("tag_id", "").strip()
    filter_last_contract = request.args.get("last_contract_num", "").strip()
    filter_status = request.args.get("status", "").strip()
    filter_rental_class_num = request.args.get("rental_class_num", "").strip()

    filtered_items = items
    if filter_common_name:
        filtered_items = [item for item in filtered_items if item.get("common_name") == filter_common_name]
    if filter_tag_id:
        filtered_items = [item for item in filtered_items if item.get("tag_id") == filter_tag_id]
    if filter_last_contract:
        filtered_items = [item for item in filtered_items if item.get("last_contract_num") == filter_last_contract]
    if filter_status:
        filtered_items = [item for item in filtered_items if item.get("status") == filter_status]
    if filter_rental_class_num:
        rental_class_nums = [num.strip() for num in filter_rental_class_num.split(',') if num.strip()]
        if not rental_class_nums:  # Full list from your data
            rental_class_nums = [
                "64815", "64816", "64817", "3168", "3169", "64840", "64841", "64842", "64843", "64847", "64848", "64849",
                "64819", "64824", "64836", "64837", "64876", "3903", "64852", "64853", "64854", "66742", "66743", "66747",
                "64864", "64865", "64866", "64867", "64868", "64869", "64874", "64855", "64856", "64857", "64858", "64860",
                "64861", "65808", "63442", "64921", "64922", "64923", "64924", "64925", "64926", "64927", "64928", "64929",
                "64930", "64932", "64933", "64934", "65493", "65496", "64935", "64936", "64937", "64938", "64939", "64940",
                "64941", "64942", "64943", "64944", "64945", "64946", "64947", "64948", "64949", "65494", "65497", "64888",
                "64889", "64890", "64891", "64892", "64893", "65604", "65605", "65606", "65607", "65608", "65609", "63440",
                "64894", "64895", "64896", "64897", "64898", "64899", "64900", "64901", "64902", "64904", "64905", "65611",
                "64906", "64907", "64908", "64909", "64910", "64911", "64912", "64913", "64914", "64915", "64916", "64917",
                "64918", "64919", "64920", "65495", "65498"
            ]
        filtered_items = [item for item in filtered_items if item.get("rental_class_num") in rental_class_nums]

    category_items = [item for item in filtered_items if categorize_item(item) == category]
    subcat_items = [item for item in category_items if item.get("common_name") == common_name] if common_name else category_items

    total_items = len(subcat_items)
    total_pages = (total_items + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    paginated_items = subcat_items[start:end]

    print(f"AJAX: Category: {category}, Common Name: {common_name}, Total Items: {total_items}, Page: {page}")

    return jsonify({
        "items": [{
            "tag_id": item["tag_id"],
            "common_name": item["common_name"],
            "date_last_scanned": item.get("date_last_scanned", "N/A"),
            "last_scanned_by": item.get("last_scanned_by", "Unknown"),
            "last_contract_num": item.get("last_contract_num", "N/A")
        } for item in paginated_items],
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page
    })