from swap.v4.uniswap_v4_constants import PERMIT2_ABI, ERC20_ABI
from swap.v4.encoder import encode_permit2_permit
import time

PERMIT_EXPIRATION = 30 * 24 * 60 * 60  # 30 days
SIG_DEADLINE = 30 * 60               # 30 minutes


class Permit2Manager:
    """Handles the two-layer Permit2 approval flow for Uniswap V4.

    Layer 1: ERC20.approve(Permit2, max)      — one-time, on-chain
    Layer 2: EIP-712 PermitSingle signature   — per-swap, off-chain
    """

    def __init__(self, w3, permit2_addr, router_addr, chain_id):
        self.w3 = w3
        self.permit2_addr = permit2_addr
        self.router_addr = router_addr
        self.chain_id = chain_id
        self.contract = w3.eth.contract(address=permit2_addr, abi=PERMIT2_ABI)

    def check_erc20_approval(self, token_addr, user_addr, input_amount, max_approval=2**256 - 1):
        """Returns an ERC20.approve contract call if Permit2 allowance is insufficient."""
        token = self.w3.eth.contract(address=token_addr, abi=ERC20_ABI)
        allowance = token.functions.allowance(user_addr, self.permit2_addr).call()
        if allowance >= input_amount:
            return None

        gas = token.functions.approve(self.permit2_addr, max_approval).estimate_gas({'from': user_addr})
        return {
            "address": token_addr,
            "abi": ERC20_ABI,
            "functionName": "approve",
            "args": [self.permit2_addr, hex(max_approval)],
            "gas": int(1.2 * gas),
        }

    def check_permit(self, token_addr, user_addr, input_amount):
        """Returns EIP-712 permit_data if Permit2 → Router allowance needs renewal, else None."""
        result = self.contract.functions.allowance(user_addr, token_addr, self.router_addr).call()
        allowance, expiration, nonce = result[0], result[1], result[2]

        if allowance >= input_amount and expiration >= int(time.time()):
            return None

        return self.build_permit_sign(token_addr, input_amount, nonce)
    
    def build_permit_sign(self, token_addr, amount, nonce):
        # off chain signature flow 
        """Build EIP-712 typed data for the frontend to sign via signTypedData."""
        return {
            "domain": {
                "name": "Permit2",
                "chainId": self.chain_id,
                "verifyingContract": self.permit2_addr,
            },
            "types": {
                "PermitSingle": [
                    {"name": "details", "type": "PermitDetails"},
                    {"name": "spender", "type": "address"},
                    {"name": "sigDeadline", "type": "uint256"},
                ],
                "PermitDetails": [
                    {"name": "token", "type": "address"},
                    {"name": "amount", "type": "uint160"},
                    {"name": "expiration", "type": "uint48"},
                    {"name": "nonce", "type": "uint48"},
                ],
            },
            "primaryType": "PermitSingle",
            "message": {
                "details": {
                    "token": token_addr,
                    "amount": str(amount),
                    "expiration": int(time.time()) + PERMIT_EXPIRATION,
                    "nonce": nonce,
                },
                "spender": self.router_addr,
                "sigDeadline": int(time.time()) + SIG_DEADLINE,
            },
        }

    def encode_permit(self, permit_data, signature):
        """ABI-encode a signed PermitSingle for use as PERMIT2_PERMIT command input."""
        return encode_permit2_permit(permit_data, signature)
