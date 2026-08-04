#fetch keys from secret manager
import boto3
import json

def get_secrets():
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId="vault-auth-secrets")
    return json.loads(response["SecretString"])

secrets = get_secrets()

#TODO: implement rotating access-refresh

ACCESS_SECRET = secrets["ACCESS_SECRET"]

def get_payments_secrets():
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId="vault-payments-secrets")
    return json.loads(response["SecretString"])

payments_secrets = get_payments_secrets()
ALCHEMY_API_KEY = payments_secrets["ALCHEMY_API_KEY"]
  