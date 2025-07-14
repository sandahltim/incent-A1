from flask import Blueprint, render_template
from collections import defaultdict
from db_connection import DatabaseConnection
import re

tab3_bp = Blueprint("tab3_bp", __name__, url_prefix="/tab3")

def tokenize_name(name):
    return re.split(r'\W+', name.lower())

def categorize_item(item):
    tokens = tokenize_name(item.get("common_name", ""))
    if any(word in tokens for word in ['tent', 'canopy', 'pole', 'hp', 'mid', 'end', 'navi']):
        return 'Tent Tops'
    elif any(word in tokens for word in ['table', 'chair', 'plywood', 'prong']):
        return 'Tables and Chairs'
    elif any(word in tokens for word in ['132', '120', '90', '108']):
        return 'Round Linen'
    elif any(word in tokens for word in ['90x90', '90x132', '60x120', '90x156', '54']):
        return 'Rectangle Linen'
    elif any(word in tokens for word in ['otc', 'machine', 'hotdog', 'nacho']):
        return 'Concession'
    else:
        return 'Other'

def subcategorize_item(category, item):
    tokens = tokenize_name(item.get("common_name", ""))
    if category == 'Tent Tops':
        if any(word in tokens for word in ['hp']):
            return 'HP Tents'
        elif any(word in tokens for word in ['ncp', 'nc', 'end', 'pole']):
            return 'Pole Tents'
        elif any(word in tokens for word in ['navi']):
            return 'Navi Tents'
        elif any(word in tokens for word in ['canopy']):
            return 'AP Tents'
        else:
            return 'Other Tents'
    elif category == 'Tables and Chairs':
        if 'table' in tokens:
            return 'Tables'
        elif 'chair' in tokens:
            return 'Chairs'
        else:
            return 'Other T&C'
    elif category == 'Round Linen':
        if '90' in tokens:
            return '90-inch Round'
        elif '108' in tokens:
            return '108-inch Round'
        elif '120' in tokens:
            return '120-inch Round'
        elif '132' in tokens:
            return '132-inch Round'
        else:
            return 'Other Round Linen'
    elif category == 'Rectangle Linen':
        if '90x90' in tokens:
            return '90 Square'
        elif '54' in tokens:
            return '54 Square'
        elif '90x132' in tokens:
            return '90x132'
        elif '90x156' in tokens:
            return '90x156'
        elif '60x120' in tokens:
            return '60x120'
        else:
            return 'Other Rectangle Linen'
    elif category == 'Concession':
        if 'frozen' in tokens:
            return 'Frozen Drink Machines'
        elif 'cotton' in tokens:
            return 'Cotton Candy Machines'
        elif 'sno' in tokens:
            return 'SnoKone Machines'
        elif 'hotdog' in tokens:
            return 'Hotdog Machines'
        elif 'cheese' in tokens:
            return 'Warmers'
        elif 'popcorn' in tokens:
            return 'Popcorn Machines'
        else:
            return 'Other Concessions'
    else:
        return 'Unspecified Subcategory'

def needs_service(item):
    """Filter items to only those relevant to the service department."""
    service_statuses = {"repair", "wash", "wet", "needs to be inspected"}
    status = item.get("status") or ""  # Handle None with empty string
    return status.lower() in service_statuses

def assign_crew(item):
    """Assign items to crews based on category."""
    category = categorize_item(item)
    if category == 'Tent Tops':
        return 'Tent Crew'
    elif category in ('Round Linen', 'Rectangle Linen'):
        return 'Linen Crew'
    else:
        return 'Fabrication/Maintenance'

@tab3_bp.route("/")
def show_tab3():
    with DatabaseConnection() as conn:
        rows = conn.execute("SELECT * FROM id_item_master").fetchall()
    items = [dict(row) for row in rows if needs_service(dict(row))]
    print(f"Service items found: {len(items)}")  # Debug log

    # Build crew_map: crew -> status -> category -> subcategory -> items
    crew_map = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    for item in items:
        crew = assign_crew(item)
        status = item.get("status", "")
        category = categorize_item(item)
        subcategory = subcategorize_item(category, item)
        
        if 'item_list' not in crew_map[crew][status][category]:
            crew_map[crew][status][category]['item_list'] = []
            crew_map[crew][status][category]['subcategories'] = defaultdict(list)
        crew_map[crew][status][category]['item_list'].append(item)
        crew_map[crew][status][category]['subcategories'][subcategory].append(item)

    # Build crew_data with totals
    crew_data = []
    for crew, status_dict in crew_map.items():
        crew_total = 0
        status_counts = defaultdict(int)
        for status, cat_dict in status_dict.items():
            status_total = 0
            for cat, sub_dict in cat_dict.items():
                item_count = len(sub_dict['item_list'])
                status_total += item_count
                sub_dict['total'] = item_count
                sub_dict['service'] = item_count
            status_counts[status] = status_total
            crew_total += status_total
        crew_data.append({
            "crew": crew,
            "total": crew_total,
            "status_counts": status_counts
        })

    crew_data.sort(key=lambda x: x["crew"])
    items_found = len(items) > 0

    # Debug crew_map structure
    for crew, status_dict in crew_map.items():
        print(f"Crew: {crew}")
        for status, cat_dict in status_dict.items():
            print(f"  Status: {status}")
            for cat, sub_dict in cat_dict.items():
                print(f"    Category: {cat}, Items: {len(sub_dict['item_list'])}, Subcategories: {len(sub_dict['subcategories'])}")
                for subcat, sub_items in sub_dict['subcategories'].items():
                    print(f"      Subcategory: {subcat}, Items: {len(sub_items)}")
                    for item in sub_items:
                        print(f"        Item: {item['tag_id']}")

    return render_template("tab3.html", crew_data=crew_data, crew_map=crew_map, items_found=items_found)