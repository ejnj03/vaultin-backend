import boto3
import uuid 
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Attr
import time

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
fr_table = dynamodb.Table("vault-friend-requests")
contacts_table = dynamodb.Table("vault-contacts")

#----------- REQUESTS -------------#
def create_request(from_user, to_user):
    status = find_request(from_user, to_user)
    opp_status = find_request(to_user, from_user)

    if status == "pending" or status == "accepted" or opp_status == "pending" or opp_status == "accepted": 
        if status == "pending":
            error = "request was already sent"
        elif opp_status == "pending":
            error = "this user has already sent you a request"
        elif status == "accepted" or opp_status == "accepted":
            error = "user is already a friend"
        #duplicate requests after a denied request is valid
        return {"error_code": 409, "error": error}
    
    fr_table.put_item(Item={
        "requesterUsername": from_user,
        "recieverUsername": to_user,
        "createdAt": int(time.time()),
        "status": "pending"
    })

    return {}
        
def get_request(from_user, to_user):
    resp = fr_table.get_item(
        Key={
            "requesterUsername": from_user,
            "recieverUsername": to_user
        }
    )
    if "Item" not in resp:
        return None
    item = resp["Item"]
    return item

def find_request(from_user, to_user):
    resp = fr_table.get_item(
        Key={
            "requesterUsername": from_user,
            "recieverUsername": to_user
        }
    )
    if "Item" not in resp:
        return None
    item = resp["Item"]
    return item["status"]

def get_sent(user):
    """
    get all reqs sent by the user
    """
    response = fr_table.query(
        KeyConditionExpression="requesterUsername = :user",
        FilterExpression="#s = :status",
        ExpressionAttributeValues={
            ":user": user,
            ":status": "pending"
        },
        ExpressionAttributeNames={
            "#s": "status"
        }
    )
    return response["Items"]

def get_recieved(user):
    """
    get all reqs recieved by the user
    """
    response = fr_table.query(
        IndexName="recieverUsername-index",
        KeyConditionExpression="recieverUsername = :user",
        FilterExpression="#s = :status",
        ExpressionAttributeValues={
            ":user": user,
            ":status": "pending"
        },
        ExpressionAttributeNames={
            "#s": "status"
        }
    )
    return response["Items"]

def update_status(reciever, sender, status="accepted"):
    fr_table.update_item(
        Key={
            "requesterUsername": sender,
            "recieverUsername": reciever
        },
        UpdateExpression="SET #s = :status, updatedAt = :t",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":status": status, ":t": int(time.time())},
    )
#----------- CONTACTS AND ACTIONS -------------#

def get_contacts(user):
    resp = contacts_table.query(
        KeyConditionExpression="username = :user",
        ExpressionAttributeValues={":user": user}
    )
    return resp.get("Items", [])

def is_contact(user1, user2, get_state=False):
    resp = contacts_table.get_item(
        Key={
            "username": user1,
            "friendUsername": user2
        }
    )
    if "Item" not in resp:
        return None if get_state else False
    item = resp["Item"]
    return item if get_state else True

def create_contact(user1, user2):
    accepted_t = int(time.time())
    contacts_table.put_item(Item={
        "username": user1,
        "friendUsername": user2,
        "createdAt": accepted_t
    })
    contacts_table.put_item(Item={
        "username": user2,
        "friendUsername": user1,
        "createdAt": accepted_t
    })

def accept_request(user, friend_user):
    #find request from friend to the person taking the action
    status = find_request(friend_user, user)
    if status != "pending": 
        if is_contact(user, friend_user):
            error = "user is already a friend"
        else:
            error = "already responded to this request"
        #duplicate requests after a denied request is valid
        return {"error_code": 409, "error": error}
    
    #update fr table
    update_status(user, friend_user, status="accepted")
    #update contact table
    create_contact(user, friend_user)

    return {}

def reject_request(user, friend_user):
    #find request from friend to the person taking the action
    status = find_request(friend_user, user)
    if status != "pending": 
        if is_contact(user, friend_user):
            error = "user is already a friend"
        else:
            error = "already responded to this request"
        #duplicate requests after a denied request is valid
        return {"error_code": 409, "error": error}
    
    #update fr table
    update_status(user, friend_user, status="rejected")

    return {}


def cancel_request(user, friend_user):
    #find request from friend to the person taking the action
    status = find_request(user, friend_user)
    if status != "pending": 
        if is_contact(user, friend_user):
            error = "user is already a friend"
        elif status == "canceled":
            error = "request was already canceled"
        else:
            error = "already responded to this request"
        #duplicate requests after a denied request is valid
        return {"error_code": 409, "error": error}
    
    #update fr table
    update_status(friend_user, user, status="canceled")

    return {}