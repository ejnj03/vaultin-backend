import jwt
from auth.secrets import ACCESS_SECRET
from utils.helpers import build_response

#TODO: update to validate auth header
def validate_jwt_access(access_token):

    #print(jwt_token)
    try:
        payload = jwt.decode(access_token, ACCESS_SECRET, algorithms=["HS256"])
        address = payload["sub"]
        
    except jwt.InvalidSignatureError:
        return build_response(401, {"error_code": "InvalidSignatureError"})
    except jwt.ExpiredSignatureError:
        expired_payload = jwt.decode(access_token, ACCESS_SECRET, algorithms=["HS256"], options={"verify_exp": False})
        print("Expired token payload:", expired_payload)
        return build_response(401, {"error_code": "ExpiredSignatureError"})
    except Exception as e:
        print(e)
        return build_response(401, {"error_code": f"jwt token invalid"})
    
    return {"address" : address}