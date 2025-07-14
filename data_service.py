def get_active_rental_contracts(conn, filter_contract="", filter_common="", sort="last_contract_num:asc", since_date=None):
    """
    Returns a list of active rental contracts with latest client_name and transaction notes from id_transactions.
    """
    sort_field, sort_order = sort.split(":") if ":" in sort else ("last_contract_num", "asc")
    query = """
       SELECT DISTINCT im.last_contract_num,
           it.client_name AS client_name,
           MAX(im.date_last_scanned) AS scan_date,
           it.notes AS transaction_notes
       FROM id_item_master im
       LEFT JOIN id_transactions it ON im.last_contract_num = it.contract_number AND im.tag_id = it.tag_id
       WHERE im.status IN ('On Rent', 'Delivered')
         AND it.scan_date = (
             SELECT MAX(it2.scan_date)
             FROM id_transactions it2
             WHERE it2.contract_number = im.last_contract_num
               AND it2.tag_id = im.tag_id
         )
    """
    params = []
    if filter_contract:
        query += " AND im.last_contract_num LIKE ?"
        params.append(f"%{filter_contract}%")
    if filter_common:
        query += " AND im.common_name LIKE ?"
        params.append(f"%{filter_common}%")
    if since_date:
        query += " AND im.date_last_scanned >= ?"
        params.append(since_date)
    query += f" GROUP BY im.last_contract_num, it.client_name, it.notes ORDER BY {sort_field} {sort_order.upper()}"
    return conn.execute(query, params).fetchall()

def get_active_rental_items(conn, filter_contract="", filter_common="", sort="last_contract_num:asc", since_date=None):
    """
    Returns all active rental items with rental_class_id from seed_rental_classes and notes from id_transactions.
    """
    sort_field, sort_order = sort.split(":") if ":" in sort else ("last_contract_num", "asc")
    query_items = """
       SELECT im.tag_id, im.common_name, src.rental_class_id, im.status, im.bin_location, 
              im.quality, im.last_contract_num, im.date_last_scanned, im.last_scanned_by,
              it.notes AS notes
       FROM id_item_master im
       LEFT JOIN seed_rental_classes src ON im.common_name = src.common_name
       LEFT JOIN id_transactions it ON im.last_contract_num = it.contract_number AND im.tag_id = it.tag_id
       WHERE im.status IN ('On Rent', 'Delivered')
         AND (it.scan_date IS NULL OR it.scan_date = (
             SELECT MAX(it2.scan_date)
             FROM id_transactions it2
             WHERE it2.contract_number = im.last_contract_num
               AND it2.tag_id = im.tag_id
         ))
    """
    params = []
    if filter_contract:
        query_items += " AND im.last_contract_num LIKE ?"
        params.append(f"%{filter_contract}%")
    if filter_common:
        query_items += " AND im.common_name LIKE ?"
        params.append(f"%{filter_common}%")
    if since_date:
        query_items += " AND im.date_last_scanned >= ?"
        params.append(since_date)
    query_items += f" ORDER BY {sort_field} {sort_order.upper()}"
    return conn.execute(query_items, params).fetchall()