import urllib.request 
import json 
import boto3
import time
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('vault-token-prices')

def get_prices_secrets():
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId="vault-prices-secrets")
    return json.loads(response["SecretString"])

#the deployed version hardcoded this key in source; it must be rotated and
#stored in Secrets Manager before this is redeployed
COINGECKO_API_KEY = get_prices_secrets()["COINGECKO_API_KEY"]
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

#serve cached prices until this many seconds past CoinGecko's own
#last_updated_at, then refetch. Note this is measured against CoinGecko's
#timestamp, not our write time, so real staleness is their lag plus this.
STALE_WINDOW = 60

def fetch_prices_api(ids):
    ids = ",".join(ids)
    url = f"{COINGECKO_URL}?vs_currencies=usd&symbols={ids}&include_24hr_change=true&include_last_updated_at=true"

    req = urllib.request.Request(url)
    req.add_header("x-cg-demo-api-key", COINGECKO_API_KEY)

    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
    print("api returned: ", data)
    return data

def update_db(data, ret):

    for id in data.keys():
        dt = data[id]
        usd = dt['usd']
        usd_24h_change = dt['usd_24h_change']
        last_updated_at = dt['last_updated_at']

        ret[id] = {'usd': usd, 'usd_24h_change': usd_24h_change, 'last_updated_at': last_updated_at}
        
        table.put_item(Item={
            'cacheKey': id.lower(),
            'usd': Decimal(str(round(usd, 8))),
            'last_updated_at': last_updated_at,
            'usd_24h_change': Decimal(str(round(usd_24h_change, 8))),
        })


def fetch_prices(ids):
    now = time.time() #current unix ts in seconds
    stale = []
    result = {}
    for id in ids:
        resp = table.get_item(Key={
            'cacheKey': id
        })
        if 'Item' in resp:
            item = resp['Item']
            last_updated_at = item['last_updated_at']
            #if more than 5 min has passed
            if now - float(last_updated_at) > STALE_WINDOW:
                stale.append(id)
            else:
                usd = float(item['usd'])
                usd_24h_change = float(item['usd_24h_change'])
                result[id] = {'usd': usd, 'usd_24h_change': usd_24h_change, 'last_updated_at': int(last_updated_at)}
        else:
            stale.append(id)

    if stale:
        new_data = fetch_prices_api(stale)
        update_db(new_data, result)
    print("returning: ", result)
    return result

