import json
from auth_utils import generate_nonce, verify_msg, generate_jwt_refresh, generate_jwt_access, validate_jwt_refresh
import base64
from user_register import find_username, find_address, register_user, is_validUsername

from user_data import lookup_userData
from utils import build_response, get_cookies, get_body, get_params, set_request_origin

from profile import get_upload_url, update_db, get_photo

from cdp_auth import generate_session_token

def lambda_handler(event, context=None):
    #echo back the caller's origin on every response built below
    set_request_origin(event)

    #get the route of the request
    route = event.get("routeKey", "")

    if route == "GET /auth/nonce":
        nonce = generate_nonce()
        nonce_formatted = base64.urlsafe_b64encode(nonce.encode()).decode()
        return build_response(200, {"nonce": nonce_formatted})

    
    if route == "POST /auth/verify":
        try:
            body = json.loads(event.get("body", {}))
            message = body.get("message", "")
            signature = body.get("signature", "")

            #verify (throws errors if not valid)
            wallet_address = verify_msg(message, signature)
            #generate jwt from the address
            refresh_token = generate_jwt_refresh(wallet_address)
            access_token = generate_jwt_access(wallet_address)
            #all checks passed- return the JWT
            cookie_header = f"refresh_token={refresh_token}; HttpOnly; Secure; SameSite=None; Path=/; Max-Age=86400"
            return build_response(
                200,
                {
                    "address": wallet_address,
                    "authenticated": True,
                    #TODO: implement access token creation flow
                    "access_token": access_token
                },
                extra_headers={"Set-Cookie": cookie_header}
            )

        except Exception as e:
            return build_response(401, {"error": str(e) or type(e).__name__})
    
    #handle CORS preflight
    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return build_response(200, {}, extra_headers={
            "Access-Control-Allow-Methods": "GET, POST, PUT, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Allow-Credentials": "true"
        })

    #-------all methods hereafter require refresh token (valid)-------#
    #print(event)
    cookies = get_cookies(event)
    #print(cookies)
    res = validate_jwt_refresh(cookies.get("refresh_token"))
    #print(res)
    if "address" not in res:
        return res #built error response
    user_addr = res["address"]
    user_username = find_username(user_addr)

    if route == "POST /auth/update_access":
        access_token = generate_jwt_access(user_addr)
        return build_response(200, {"access_token": access_token})
    
    if route == "GET /auth/validate-username/{username}":
        username = get_params(event, "username")
        resp_id, error = is_validUsername(username)
        return build_response(resp_id, body={"resp_id": resp_id}, error=error)
    
    #revoke access to token on user logout
    #clear the cookie (=;) and delete it immediately (Max=0)
    if route == "POST /auth/logout":
        cookie_header = "refresh_token=; HttpOnly; Secure; SameSite=None; Path=/; Max-Age=0"
        return build_response(200, {}, extra_headers={"Set-Cookie": cookie_header})

    if route == "POST /auth/register/register-user":
        details = get_body(event)
        return register_user(details, user_addr)
    
    if route == "GET /auth/utils/find-addr/{username}":
        username = get_params(event, "username").lower()
        addr = find_address(username)
        if not addr:
            return build_response(404, {"error": f"no address found for {username}"})
        return build_response(200, {"address": addr, "username": username})
    
    if route == "GET /auth/utils/find-username":
        user = find_username(user_addr)
        if not user:
            return build_response(404, {"error": f"no username found for {user_addr}"})
        return build_response(200, {"address": user_addr, "username": user})
    
    if route == "GET /auth/utils/lookup-userData":
        data = lookup_userData(user_username)
        if data:
            return build_response(200, {"data": data})
        return (404, {"error": "user is not registered in the database."})
    
    #------------COINBASE AUTH---------------#

    if route == 'POST /trade/coinbase/session-token':
        body = get_body(event)
        res = generate_session_token(body.get("address", ""), body.get("network", ""), body.get("asset", ""))
        if "error" in res:
            return build_response(400, res)
        return build_response(200, res)
    #------------USER PROFILE PIC API----------#
    if route == 'GET /profile/upload-url/{filetype}':
        try:
            file_type = get_params(event, "filetype").lower()
            #print(f"[upload-url] user_addr={user_addr}, file_type={file_type}")
            url = get_upload_url(user_addr, file_type)
            #print(f"[upload-url] presigned URL generated successfully")
            return build_response(200, {"link": url})
        except Exception as e:
            #print(f"[upload-url] ERROR: {e}")
            return build_response(500, {"error": f"failed to generate upload url: {str(e)}"})
    
    if route == 'POST /profile/update-photo':
        fileType = get_body(event).get("type", "")
        url = update_db(user_username, user_addr, fileType)
        return build_response(200, {"url": url})
    
    if route == 'GET /profile/my-profile-photo':
        return build_response(200, {"url": get_photo(user_username)})
    
    return build_response(404, {"error": "not found"})