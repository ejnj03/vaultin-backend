from db import users_table

def lookup_userData(username):
    entry = users_table.get_item(Key={"username": username})
    if "Item" in entry:
        return entry["Item"]
    return None