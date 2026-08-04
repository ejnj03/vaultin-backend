from swap.v4.uniswap_v4_constants import PERMIT2_ABI, ERC20_ABI
from swap.v4.encoder import encode_permit2_permit
from time import time 

class Permit2AtomicManager:
    """Handles the two-layer Permit2 approval flow for Uniswap V4.

    Layer 1: ERC20.approve(Permit2, max)      — one-time, on-chain
    
    """

    def __init__(self, w3, user_address, permit2_addr, router_addr, tokenin_addr, router, tokenin, chain_id,
                 slippage_bps=50, gas_factor=1.2, time_limit=300):
        self.w3 = w3
        self.user_address = user_address
        self.permit2_addr = permit2_addr
        self.router_addr = router_addr
        self.tokenin_addr = tokenin_addr

        #contract objects
        self.router = router
        self.tokenin = tokenin

        self.chain_id = chain_id
        self.slippage_bps = slippage_bps
        self.gas_factor = gas_factor
        self.time_limit = time_limit
        #permit2 contract
        self.contract = w3.eth.contract(address=permit2_addr, abi=PERMIT2_ABI)

    def check_erc20_approval(self, input_amount, max_approval=2**256 - 1):
        """
        check ERC20 contract approval of permit2 to spend with max allowance
        """
        allowance = self.tokenin.functions.allowance(self.user_address, self.permit2_addr).call()
        if allowance > input_amount:
            return None

        gas = self.tokenin.functions.approve(self.permit2_addr, max_approval).estimate_gas({'from': self.user_address})
        #format for sendCalls

        #encode the function + param data
        data = self.tokenin.encode_abi("approve", args=[self.permit2_addr, max_approval])
        return {
            "to": self.tokenin_addr,
            "data": data,
            "gas": int(self.gas_factor * gas),
        }
    
    def check_permit(self, input_amount):
        """Returns EIP-712 permit_data if Permit2 → Router allowance needs renewal, else None."""
        result = self.contract.functions.allowance(self.user_address, self.tokenin_addr, self.router_addr).call()
        allowance, expiration, _ = result[0], result[1], result[2]

        if allowance >= input_amount and expiration >= int(time()):
            return None

        # on chain signature flow
        expire_time = int(time())+self.time_limit

        data = self.contract.encode_abi("approve", args=[self.tokenin_addr, self.router_addr, input_amount, expire_time])

        gas = self.contract.functions.approve(self.tokenin_addr, self.router_addr, input_amount, expire_time).estimate_gas({'from': self.user_address})
        
        return {
            "to": self.permit2_addr,
            "data": data,
            "gas": int(self.gas_factor * gas)
        }

