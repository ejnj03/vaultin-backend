import boto3
import uuid 
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
requests_table = dynamodb.Table("vault-payment-requests")

def create_request(requester_address, requester_username, title, recipient_username, amount, network, token):
    #generate random id
    req_id = str(uuid.uuid4())

    requestRow = {
        "requestId": req_id,
        "requesterAddress": requester_address,
        "requesterUsername": requester_username,
        "title": title,
        "recipientUsername": recipient_username,
        "amount": amount,
        "network": network,
        "token": token,
        "status": "pending",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    #register the request
    requests_table.put_item(Item=requestRow)

    return requestRow

#TODO: add pagination (returns 1MB max per call, data might be larger)
#TODO: create GSI to use it in place of scanning over all entries
def find_requests_from(user_addr):
    #find the requests made by the user
    res = requests_table.scan(
        FilterExpression=Attr("requesterAddress").eq(user_addr)
    )
    if "Items" in res:
        return res["Items"]
    else:
        return None
    
def find_requests_to(user_username):
    #find the requests made to the user
    res= requests_table.scan(
        FilterExpression=Attr("recipientUsername").eq(user_username)
    )
    if "Items" in res:
        return res["Items"]
    else:
        return None

def respond_request(req_id, action, active_user):
    res = requests_table.get_item(Key={"requestId": req_id})

    if not "Item" in res:
        #client input issue/not found issue
        return {"error": "No request with the provided request id.", "statusId":404}
    #you should only be able to respond to requests for which you are the reciever
    req = res["Item"]
    if req["recipientAddress"] != active_user:
        #authenticated but lacking permission
        return {"error": "The active user is not the reciever of this request; unauthorized to respond to the request", "statusId":403}
    #you should not be able to approve or reject a request that is not in the pending status
    curr_status = req["status"]
    if curr_status != "pending":
        return {"error": f"The status of this request is {curr_status}", "statusId":403}

    if action == "approve":
        status = "approved"
    elif action == "reject":
        status = "rejected"
    else:
        #client input issue
        return {"error": "invalid action provided", "statusId":400}
    
    #modify the entry
    requests_table.update_item(
        Key={"requestId": req_id},
        UpdateExpression="SET #s = :status",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": status
        }
    )
    return {"statusId":200}

def cancel_request(req_id, active_user):
    res = requests_table.get_item(Key={"requestId": req_id})

    if not "Item" in res:
        #client input issue/not found issue
        return {"error": "No request with the provided request id.", "statusId":404}
    #you should only be able to respond to requests for which you are the reciever
    req = res["Item"]
    if req["requesterAddress"] != active_user:
        #authenticated but lacking permission
        return {"error": "The active user is not the initiator of this request; unauthorized to respond to the request", "statusId":403}
    
    #if the request is not in pending status it cannot be canceled
    curr_status = req["status"]
    if curr_status != "pending":
        return {"error": f"The status of this request is {curr_status}- cannot be canceled", "statusId":403}
    
    #modify the entry
    requests_table.update_item(
        Key={"requestId": req_id},
        UpdateExpression="SET #s = :status",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": "canceled"
        }
    )
    return {"statusId":200}

#TODO: accept txnHash field and add it to the db upon request completion
def completed_request(req_id, active_user):
    res = requests_table.get_item(Key={"requestId": req_id})

    if not "Item" in res:
        #client input issue/not found issue
        return {"error": "No request with the provided request id.", "statusId":404}
    #you should only be able to respond to requests for which you are the reciever
    req = res["Item"]
    if req["recipientAddress"] != active_user:
        #authenticated but lacking permission
        return {"error": "The active user is not the reciever of this request; unauthorized to respond to the request", "statusId":403}
    #you should not be able to approve or reject a request that is not in the pending status
    curr_status = req["status"]
    if curr_status != "approved":
        return {"error": f"The status of this request is {curr_status}", "statusId":403}

    #modify the entry
    requests_table.update_item(
        Key={"requestId": req_id},
        UpdateExpression="SET #s = :status",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": "completed"
        }
    )
    return {"statusId":200}