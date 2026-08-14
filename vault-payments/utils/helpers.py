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


def build_response(status_code, body={}, extra_headers=None, error=None):
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
