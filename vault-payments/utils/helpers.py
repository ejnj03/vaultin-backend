import json

def build_response(status_code, body={}, extra_headers=None, error=None):
    headers = {
        "Access-Control-Allow-Origin": "http://localhost:5173",
        "Access-Control-Allow-Credentials": "true",
    }
    if extra_headers:
        headers.update(extra_headers)
    if error:
        body["error"] = error
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body, default=str)
    }

def get_body(event, key=None):
    body = json.loads(event.get("body", "{}"))
    if key:
        return body.get(key, None)
    return body
            
def get_token_from_header(event):
    print(event.get("headers", {}))
    headers = event.get("headers", {})
    auth_string = headers.get("authorization", "") or headers.get("Authorization", "")
    splits = auth_string.split()
    if len(splits) != 2:
        return None
    return splits[1]

def get_params(event, key):
    return event.get("pathParameters", {}).get(key, "")
