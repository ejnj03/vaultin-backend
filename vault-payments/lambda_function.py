from decimal import Decimal
from auth import validate_jwt_access
from utils import get_token_from_header, get_body, build_response, get_params, find_address, find_username, find_by_address, find_by_username
from payments import create_request as create_payment_request, find_requests_from, find_requests_to, respond_request, cancel_request as cancel_payment_request, completed_request
from payments import create_txnEntry, get_completed, update_txn_status
from swap import find_transferMethod
from social import create_request, get_recieved, get_sent, accept_request, reject_request, get_contacts, cancel_request

def validate_event(event):
    access_token = get_token_from_header(event)
    if not access_token:
        return build_response(401, error="No access token in auth header")
    return validate_jwt_access(access_token)
#this

def lambda_handler(event, context):
    route = event.get("routeKey", "")

    val_res = validate_event(event)
    if "address" not in val_res:
        return val_res #built error response
    user_address = val_res["address"]
    
    user_username = find_username(user_address)

    #----------------FRIEND ROUTES------------------#
    if route == 'GET /users/by-username/{username}':
        try:
            username = get_params(event, "username")
            res = find_by_username(username)
            if not res:
                return build_response(404, error="profile not found")
            return build_response(200, res)
        except Exception as e:
            return build_response(500, error=str(e))
    if route == 'GET /users/by-address/{address}':
        address = get_params(event, "address")
        res = find_by_address(address)
        if not res:
            return build_response(404, error="profile not found")
        return build_response(200, res)
    
    if route == 'POST /friends/send-friend-request':
        reciever_username = get_body(event, "username")
        res = create_request(user_username, reciever_username)
        if "error_code" in res:
            return build_response(res["error_code"], error=res["error"])
        return build_response(200)
    
    if route == 'GET /friends/get-recieved':
        return build_response(200, get_recieved(user_username))
    if route == 'GET /friends/get-sent':
        return build_response(200, get_sent(user_username))

    if route == 'POST /friends/accept-friend-request':
        friend_username = get_body(event, "friend_username")
        res = accept_request(user_username, friend_username)
        if "error_code" in res:
            return build_response(res["error_code"], error=res["error"])
        return build_response(200)
    if route == 'POST /friends/reject-friend-request':
        friend_username = get_body(event, "friend_username")
        res = reject_request(user_username, friend_username)
        if "error_code" in res:
            return build_response(res["error_code"], error=res["error"])
        return build_response(200)
    if route == 'POST /friends/friend-request/cancel':
        friend_username = get_body(event, "friend_username")
        res = cancel_request(user_username, friend_username)
        if "error_code" in res:
            return build_response(res["error_code"], error=res["error"])
        return build_response(200)
    
    if route == 'GET /friends/user-friends':
        return build_response(200, get_contacts(user_username))
    #----------------TRANSFER ROUTES----------------#
    #get-quote: get the quote for the txn
    if route == 'POST /txns/get-quote':
        try:
            body = get_body(event)
            #if getting the quote with the purpose of the actual transaction 

            recipient = body.get("recipient")
            from_network = body.get("fromNetwork")
            from_token = body.get("fromToken")
            to_network = body.get("toNetwork")
            to_token = body.get("toToken")
            from_amount = body.get("fromAmount", None)
            to_amount = body.get("toAmount", None)
            urgency= body.get("urgency", None)
            preference = body.get("preference", None)
            atomic = body.get("atomic", False)

            if not recipient:
                return build_response(400, error="recipient is required")

            # Resolve recipient
            if not recipient.startswith("0x"):
                recipient_address = find_address(recipient)
            else:
                recipient_address = recipient

            result = find_transferMethod(user_address, from_network, from_token, to_network, to_token, from_amount, to_amount, recipient_address, urgency, preference, atomic)
            return build_response(200, result)
        except Exception as e:
            return build_response(500, {"error": str(e)})

    #log-txn: logs the txn in the db
    if route == 'POST /txns/log-txn':
        try:
            body = get_body(event)
            transferReason = body.get("transferReason")
            toAccount = body.get("toAccount")
            toAmount = Decimal(str(body.get("toAmount")))
            fromNetwork = body.get("fromNetwork")
            fromToken = body.get("fromToken")
            toNetwork = body.get("toNetwork")
            toToken = body.get("toToken")
            txnHash = body.get("txnHash")

            create_txnEntry(transferReason, user_username, find_username(toAccount), user_address, toAccount, toAmount, fromNetwork, fromToken, toNetwork, toToken, txnHash)
            return build_response(200, {"status": "Transaction logged"})
        except Exception as e:
            return build_response(500, error=str(e))
    
    #return transactions by hash : txn title 
    if route == 'GET /txns/get-completed':
        return build_response(200, get_completed(user_address))
    
    if route == 'POST /txns/update-state':
        body = get_body(event)
        txnHash = body.get("txnHash")
        status = body.get("status")
        update_txn_status(txnHash, status)
        return build_response(200)
    #----------------REQUEST ROUTES----------------#

    if route == 'POST /payment-requests/create-request':
        try:
            body = get_body(event)
            title = body.get("title")
            recipientUsername = body.get("recipientUsername")
            amount = body.get("amount")
            network = body.get("network")
            token = body.get("token")
            request_row = create_payment_request(user_address, user_username, title, recipientUsername, amount, network, token)
            return build_response(200, {"requestRow": request_row})
        except Exception as e:
            return build_response(500, {"error": str(e)})
    
    if route == 'GET /payment-requests/sent':
        res = find_requests_from(user_address)
        if res is None:
            return build_response(500, {"error": "Could not retrieve requests made from user"})
        return build_response(200, {"requests": res})

    if route == 'GET /payment-requests/received':
        res = find_requests_to(user_username)
        if res is None:
            return build_response(500, {"error": "Could not retrieve requests made to user"})
        return build_response(200, {"requests": res})
    
    if route == 'POST /respond-request':
        ret=None
        try:
            body = get_body(event)
            req_id = body.get("requestId", None)
            action = body.get("action", None)
            if req_id is None or action is None:
                return build_response(400, error="request parameters not fully supplied")
            ret = respond_request(req_id, action, user_address)
        except Exception as e:
            return build_response(500, {"error": str(e)})
        if "error" in ret:
            return build_response(ret["statusId"], error=ret["error"])
        return build_response(200)
    
    if route == 'POST /cancel-request':
        ret=None
        try:
            body = get_body(event)
            req_id = body.get("requestId", None)
            if req_id is None:
                return build_response(400, error="requestId not supplied")
            ret = cancel_payment_request(req_id, user_address)
        except Exception as e:
            return build_response(500, {"error": str(e)})
        if "error" in ret:
            return build_response(ret["statusId"], error=ret["error"])
        return build_response(200)

    if route == 'POST /completed-request':
        ret=None
        try:
            body = get_body(event)
            req_id = body.get("requestId", None)
            if req_id is None:
                return build_response(400, error="requestId not supplied")
            ret = completed_request(req_id, user_address)
        except Exception as e:
            return build_response(500, {"error": str(e)})
        if "error" in ret:
            return build_response(ret["statusId"], error=ret["error"])
        return build_response(200)
        
    return build_response(404, {"error": "not found"})