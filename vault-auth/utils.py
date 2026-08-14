import json

# AllowCredentials forbids the "*" wildcard, so every origin is listed explicitly
# and echoed back per-request. Keep in sync with CorsConfiguration in template.yaml.
ALLOWED_ORIGINS = {
    "http://localhost:5180",
    "https://vaultin.app",
    "https://www.vaultin.app",
}
DEFAULT_ORIGIN = "https://vaultin.app"

# Set once per invocation. Safe as module state: a Lambda container handles one
# request at a time, so there is no cross-request bleed.
_request_origin = DEFAULT_ORIGIN


def set_request_origin(event):
    """Record the caller's Origin if allowlisted. Call at the top of lambda_handler."""
    global _request_origin
    headers = event.get("headers", {}) or {}
    origin = headers.get("origin") or headers.get("Origin")
    _request_origin = origin if origin in ALLOWED_ORIGINS else DEFAULT_ORIGIN


def build_response(status_code, body={}, error=None, extra_headers=None):
    headers = {
        "Access-Control-Allow-Origin": _request_origin,
        "Access-Control-Allow-Credentials": "true",
        # Responses differ by Origin, so caches must key on it
        "Vary": "Origin",
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