import boto3

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
users_table = dynamodb.Table("vault-users")

PHOTO_URL = "https://vault-profile-images.s3.us-east-1.amazonaws.com/profile-photos"
#DEFAULT_URL = f"{PHOTO_URL}/default-profile.jpg"

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

def find_by_username(username):
    res = users_table.get_item(Key={"username":username})
    if "Item" not in res:
        return None
    item = res["Item"]
    if not "profile_photo" in item:
        photo_url = ""
    else: 
        photo_url = item["profile_photo"]
    return {"username": username, "name": item["name"], "address": item["address"], "profile_photo": photo_url}

def find_by_address(address):
    res = users_table.query(
        IndexName="address-index",
        KeyConditionExpression="address = :addr",
        ExpressionAttributeValues={":addr": address}
    )

    if not res["Items"]:
        return None
    item = res["Items"][0]
    if not "profile_photo" in item:
        photo_url = ""
    else: 
        photo_url = item["profile_photo"]

    return {"address": address, "username": item["username"], "profile_photo": photo_url}
