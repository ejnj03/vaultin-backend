from db import users_table
from utils import build_response

"""
DynamoDB responses:
get_item always returns a dict with some metadata, but only includes the key
'Item" if the record was found 

400: bad request (request itself is malformed or invalid)
409: conflict (request is valid but conflicts with the current state of the server)
     (issue is timing or uniqueness)
"""
def find_username(address):
    res = users_table.query(
        IndexName="address-index",
        KeyConditionExpression="address = :addr",
        ExpressionAttributeValues={":addr": address}
    )

    if res["Items"]:
        return res["Items"][0]["username"]

    return None

def find_address(username):
    print("Username: ", username)
    #username is the partition key
    res = users_table.get_item(Key={"username":username})

    if "Item" in res:
        return res["Item"]["address"]
    
    return None

def is_validUsername(username):
    error = None
    if not username or len(username) < 3 or len(username) > 20:
        error = "Username must be between 3-20 characters."
        resp_id = 400
    elif not username.isalnum():
        error = "Username must be alphanumeric."
        resp_id = 400
    else:
        #check if username is taken
        existing = users_table.get_item(Key={"username": username})

        if "Item" in existing:
            error = "Username is already taken."
            resp_id = 409

    if error:
        return resp_id, error
    else: 
        return 200, None

def register_user(details, address):
    username = details["username"]
    name = details["name"]
    config = details["configs"]

    resp_id, error = is_validUsername(username)
    if error:
        return build_response(resp_id, {"error": error})

    #register the user
    users_table.put_item(Item={
        "username": username,
        "address": address,
        "name": name,
        "config": config
    })

    return build_response(200, {"username": username, "address": address})