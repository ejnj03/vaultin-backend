import json
from price_utils import fetch_prices


def build_response(status_code, body, extra_headers=None):
    #CORS headers are defined by the API Gateway
    headers = {}
    if extra_headers:
        headers.update(extra_headers)
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body)
    }

def lambda_handler(event, context):
    route = event.get("routeKey", "")

    if route == "GET /prices":
        params = event.get("queryStringParameters", {}) or {}
        ids = [id for id in params.get("ids", "").split(",") if id]

        if not ids:
            ids = ["pol", "usdc", "usdt", "eth"]
        try:
            price_data = fetch_prices(ids)
        except Exception as e:
            return build_response(502, {"error": f"failed to fetch prices: {e}"})

        return build_response(200, price_data)
        

    return build_response(404, {"error": "not found"})
