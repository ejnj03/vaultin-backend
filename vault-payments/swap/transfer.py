from constants import SUPPORTED_TOKENS
from swap.v3.quote import SwapQuote
from swap.v4.quote_v4 import SwapQuoteV4
from swap.v4.quote_v4_atomic import SwapQuoteV4Atomic

def find_transferMethod(user_address, fromNetwork, fromToken, toNetwork, toToken, fromAmount, toAmount, recipientAddress, urgency=None, preference=None, userConfig=None, permit2_signature=None, permit_data=None):
    if fromNetwork == toNetwork and fromToken == toToken:
        return sameChain_sameToken(fromNetwork, fromToken, fromAmount, recipientAddress)
    if fromNetwork == toNetwork and fromToken != toToken:
         return sameChain_differentToken(user_address, fromNetwork, fromToken, toToken, fromAmount, toAmount, recipientAddress, urgency, preference, userConfig, permit2_signature=permit2_signature, permit_data=permit_data)
         
def sameChain_sameToken(network, token, transferAmount, recipientAddress):
    network_info = SUPPORTED_TOKENS[network]
    chain_id = network_info["chainId"]
    token_info = network_info["tokens"][token]
    token_address = token_info["address"]
    token_decimals = token_info["decimals"]
    return {
        "type": "sameChain_sameToken", 
        "metadata": {
            "tokenAddress": token_address, 
            "tokenDecimals": token_decimals, 
            "chainId": chain_id
        }, 
        "toAmount": transferAmount, 
        "recipientAddress": recipientAddress
    }


def sameChain_differentToken(
        user_address, 
        network, 
        fromToken, toToken, fromAmount, toAmount, 
        recipientAddress, 
        urgency, preference, 
        use_v4=True, 
        atomic=True,
        permit2_signature=None, 
        permit_data=None
    ):

    network_info = SUPPORTED_TOKENS[network]
    chain_id = network_info["chainId"]
    tokens = network_info["tokens"]
    from_token = tokens[fromToken]
    to_token = tokens[toToken]


    if fromAmount is not None:
        q_type = "EXACT_INPUT"
        amount = fromAmount
    else:
        q_type = "EXACT_OUTPUT"
        amount = toAmount

    raw_amount = int(amount)
    from_tok_addr = from_token["address"]
    to_tok_addr = to_token["address"]

    if use_v4:
        if atomic:
            quote = SwapQuoteV4Atomic(q_type, raw_amount, chain_id, from_tok_addr, to_tok_addr, user_address, recipientAddress, preference, urgency)
            return quote.get_quote()
        
        quote = SwapQuoteV4(q_type, raw_amount, chain_id, from_tok_addr, to_tok_addr, user_address, recipientAddress, preference, urgency)
        return quote.get_quote(permit2_signature, permit_data)
    else:
        quote = SwapQuote(q_type, raw_amount, chain_id, from_tok_addr, to_tok_addr, user_address, recipientAddress, preference, urgency)
        return quote.get_quote()