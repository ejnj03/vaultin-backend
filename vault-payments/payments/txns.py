import boto3
import uuid 
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
txns_table = dynamodb.Table("vaultin-transactions")

def create_txnEntry(transferReason, fromUser, toUser, fromAccount, toAccount, toAmount, fromNetwork, fromToken, toNetwork, toToken, txnHash):

    txns_table.put_item(Item={
        "txnHash": txnHash,
        "title": transferReason,
        "fromUser": fromUser,
        "toUser": toUser,
        "fromAccount": fromAccount,
        "toAccount": toAccount,
        "toAmount": toAmount,
        "fromNetwork": fromNetwork,
        "fromToken": fromToken,
        "toNetwork": toNetwork,
        "toToken": toToken,
        "status": "submitted",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })

def find_txns_from(user_addr):
    res = txns_table.query(
        IndexName="fromAccount-index",
        KeyConditionExpression=Key("fromAccount").eq(user_addr) & Key("status").eq("confirmed")
    )
    if "Items" in res:
        return res["Items"]
    else:
        return []

def find_txns_to(user_addr):
    res = txns_table.query(
        IndexName="toAccount-Index",
        KeyConditionExpression=Key("toAccount").eq(user_addr) & Key("status").eq("confirmed")
    )
    if "Items" in res:
        return res["Items"]
    else:
        return []

def get_completed(user_addr):
    """
    Per-transaction metadata recorded when a transfer was sent, keyed by hash.

    Returns the counterparty as well as the title, because it cannot be
    recovered from chain data. Same-chain cross-token transfers route through
    Uniswap: the sender sends token A to the router and the router sends token B
    to the recipient, so an on-chain view shows the router as the counterparty
    for both parties and neither ever sees the other. What was recorded here at
    send time is the only record of who was actually paid.

    Previously returned {hash: title} as a bare string. The frontend accepts
    both shapes (see sidecarFields in txn_history.js), so this change does not
    have to be deployed in lockstep -- but the frontend must ship first, or a
    client still expecting a string will render the object as its title.
    """
    txns = find_txns_from(user_addr)
    txns.extend(find_txns_to(user_addr))
    return {
        item["txnHash"]: {
            "title": item.get("title"),
            "fromUser": item.get("fromUser"),
            "toUser": item.get("toUser"),
        }
        for item in txns
    }

#TODO: Add finalized/completed at column and add ts
def update_txn_status(txnHash, status):
    #modify the entry
    txns_table.update_item(
        Key={"txnHash": txnHash},
        UpdateExpression="SET #s = :status",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": status
        }
    )
    return {"statusId":200}