from config import CDP_API_KEY, CDP_API_SECRET
import time
import jwt
import requests
from cryptography.hazmat.primitives import serialization
import base64

def generate_session_token(address, network, asset):
    try:
        now = int(time.time())
        payload = {
            "sub": CDP_API_KEY,
            "iss": "cdp",
            "aud": ["cdp_service"],
            "nbf": now,
            "iat": now,
            "exp": now + 300,
            "uris": ["POST api.developer.coinbase.com/onramp/v1/token"]
        }

        padded = CDP_API_SECRET + "=" * (-len(CDP_API_SECRET) % 4)
        key_bytes = base64.b64decode(padded)
        pem_key = b"-----BEGIN PRIVATE KEY-----\n"
        pem_key += base64.b64encode(b"\x30\x2e\x02\x01\x00\x30\x05\x06\x03\x2b\x65\x70\x04\x22\x04\x20" + key_bytes[:32])
        pem_key += b"\n-----END PRIVATE KEY-----\n"
        private_key = serialization.load_pem_private_key(pem_key, password=None)
        token = jwt.encode(payload, private_key, algorithm="EdDSA", headers={"kid": CDP_API_KEY, "typ": "JWT"})
        #print("CDP: ", CDP_API_SECRET)
        response = requests.post(
            "https://api.developer.coinbase.com/onramp/v1/token",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "addresses": [
                    {"address": address, "blockchains": [network]}
                ],
                "assets": [asset]
            }
        )

        if response.status_code != 200:
            return {"error": f"CDP API returned {response.status_code}: {response.text}"}

        data = response.json()
        if "token" not in data:
            return {"error": f"No token in CDP response: {data}"}

        return {"session_token": data["token"]}

    except Exception as e:
        return {"error": f"generate_session_token failed: {str(e)}"}