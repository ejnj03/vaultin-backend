import json

def build_response(status_code, body={}, error=None, extra_headers=None):
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
        "body": json.dumps(body)
    }

def parse_cookies(cookie_list):
    cookies = {}
    for item in cookie_list:
        parts = item.strip().split("=", 1)
        if len(parts) == 2:
            cookies[parts[0]] = parts[1]
    return cookies

# Result:
# {"vault_access": "eyJhbG...", "vault_refresh": "eyJxyz..."}

def get_cookies(event):
    """
    parses the event
    """
    # HTTP API v2 payload: cookies are a top-level list
    cookie_list = event.get("cookies", [])
    if cookie_list:
        return parse_cookies(cookie_list)

    # REST API / v1 payload: cookies are in headers
    headers = event.get("headers", {})
    raw = headers.get("cookie") or headers.get("Cookie") or headers.get("cookies") or ""
    if raw:
        return parse_cookies(raw.split(";"))

    return {}

def get_body(event, key=None):
    return json.loads(event.get("body", "{}"))    

def get_params(event, key=None):
    params = event.get("pathParameters", {})
    if key is not None:
        return params.get(key, "")
    return params

def utc_interval(weeks=0, days=0, hours=0, minutes=0, seconds=0):
    utc_sec = 1
    utc_min = utc_sec * 60 
    utc_hour = utc_min * 60 
    utc_day = utc_hour * 24
    utc_week = utc_day * 7

    ret = 0
    if weeks:
        ret += utc_week * weeks
    if days:
        ret += utc_day * days
    if hours:
        ret += utc_hour * hours
    if minutes:
        ret += utc_min * minutes
    if seconds:
        ret += utc_sec * seconds

    return ret