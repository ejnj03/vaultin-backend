#fetch keys from secret manager
import boto3
import json

def get_secrets():
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId="vault-auth-secrets")
    return json.loads(response["SecretString"])

secrets = get_secrets()

#TODO: implement rotating access-refresh
#just using access as default for now (expires every 24 hrs)
ACCESS_SECRET = secrets["ACCESS_SECRET"]
REFRESH_SECRET = secrets["REFRESH_SECRET"]

def get_coinbase_secrets():
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId="vault-coinbase-auth-secrets")
    return json.loads(response["SecretString"])

coinbase_secrets = get_coinbase_secrets()


CDP_API_KEY=coinbase_secrets["CDP_API_KEY"]
CDP_API_SECRET=coinbase_secrets["CDP_API_SECRET"]