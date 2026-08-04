from web3 import Web3
from concurrent.futures import ThreadPoolExecutor
from constants import RPC_URLS, WETH_ADDRESSES
from swap.uniswap_constants import UNISWAP_ROUTER, UNISWAP_QUOTER, ROUTER_ABI, QUOTER_ABI, ERC20_ABI
from auth.secrets import ALCHEMY_API_KEY
import time

"""
Alchemy's node is connected to the blockchain and can read data from it
-> gives a URL that we can use to send requests to
connection to the blockchain
"""

FEE_TIERS = {"0.01%": 100, "0.05%": 500, "0.3%": 3000, "1%": 10000}


def is_native(addr):
    return addr == "0x0000000000000000000000000000000000000000"


class SwapQuote:
    def __init__(self, q_type, raw_amount, chain_id, from_tok_addr, to_tok_addr, user_address, recipient, preference, urgency):
        self.q_type = q_type
        self.raw_amount = raw_amount

        self.from_tok_addr = from_tok_addr
        if is_native(from_tok_addr):
            self.from_tok_addr = WETH_ADDRESSES[chain_id]
        else: 
            self.from_tok_addr = from_tok_addr

        if is_native(to_tok_addr):
            self.to_tok_addr = WETH_ADDRESSES[chain_id]
        else:
            self.to_tok_addr = to_tok_addr
        
        self.user_address = user_address
        self.recipient = recipient
        self.preference = preference
        self.urgency = urgency
        self.w3 = Web3(Web3.HTTPProvider(f"{RPC_URLS[chain_id]}{ALCHEMY_API_KEY}"))
        self.quoter_contract = self.w3.eth.contract(address=UNISWAP_QUOTER, abi=QUOTER_ABI)
        self.router_contract = self.w3.eth.contract(address=UNISWAP_ROUTER, abi=ROUTER_ABI)

    def _quote_from_input(self, fee_tier, price_limit=0):
        try:
            output = self.quoter_contract.functions.quoteExactInputSingle(
                self.from_tok_addr, self.to_tok_addr, FEE_TIERS[fee_tier], self.raw_amount, price_limit
            ).call()
            return fee_tier, output
        except Exception:
            return fee_tier, None

    def _quote_from_output(self, fee_tier, price_limit=0):
        try:
            output = self.quoter_contract.functions.quoteExactOutputSingle(
                self.from_tok_addr, self.to_tok_addr, FEE_TIERS[fee_tier], self.raw_amount, price_limit
            ).call()
            return fee_tier, output
        except Exception:
            return fee_tier, None

    def get_best_tier(self):
        print(f"get_best_tier called: q_type={self.q_type}, from={self.from_tok_addr}, to={self.to_tok_addr}, amount={self.raw_amount}, chain_connected={self.w3.is_connected()}")
        executor = ThreadPoolExecutor(max_workers=4)
        futures = []
        for fee_tier in FEE_TIERS:
            if self.q_type == "EXACT_INPUT":
                futures.append(executor.submit(self._quote_from_input, fee_tier))
            else:
                futures.append(executor.submit(self._quote_from_output, fee_tier))

        all_results = [f.result() for f in futures]
        print(f"Quote results per fee tier: {all_results}")
        results = [r for r in all_results if r[1] is not None]
        if not results:
            raise ValueError("No valid quotes found for this token pair. The pair may lack liquidity or the token addresses may be invalid.")
        if self.q_type == "EXACT_INPUT":
            return max(results, key=lambda x: x[1])
        return min(results, key=lambda x: x[1])

    def get_gas_cost(self, fee_tier, time_limit=300, price_limit=0, slippage_bps=50, max_approval=2**256 - 1):
        """
        defaults:
        - time window for txn is 5 min (300 seconds)
        - price limit is None accept the price the pool gives
        - slippage_bps: slippage in basis points (50 = 0.5%)
        - if allowance is insufficient set it to max_approval amount so user approves once, never again
        estimate is in gas units
        """
        native = is_native(self.from_tok_addr)

        gas_price = self.w3.eth.gas_price

        approval_cost = 0
        if not native:
            token_contract = self.w3.eth.contract(address=self.from_tok_addr, abi=ERC20_ABI)
            allowance = token_contract.functions.allowance(self.user_address, UNISWAP_ROUTER).call()
            if allowance < self.raw_amount:
                approval_cost = token_contract.functions.approve(UNISWAP_ROUTER, max_approval).estimate_gas({'from': self.user_address})
                return {"is_approved": False, "approval_cost": approval_cost * gas_price}
            
        deadline = int(time.time()) + time_limit
        if self.q_type == "EXACT_INPUT":
            amount_out_min = self.raw_amount * (10000 - slippage_bps) // 10000
            txn_cost = self.router_contract.functions.exactInputSingle((self.from_tok_addr, self.to_tok_addr, fee_tier, self.recipient, deadline, self.raw_amount, amount_out_min, price_limit)).estimate_gas({'from': self.user_address})
        else:
            amount_in_max = self.raw_amount * (10000 + slippage_bps) // 10000
            txn_cost = self.router_contract.functions.exactOutputSingle((self.from_tok_addr, self.to_tok_addr, fee_tier, self.recipient, deadline, self.raw_amount, amount_in_max, price_limit)).estimate_gas({'from': self.user_address})
        
        return {"is_approved": True, "transaction_cost": txn_cost * gas_price}
    
    def get_quote(self):
        #get the best fee tier
        tier, estimate = self.get_best_tier()
        #uniswap uses millionth (*10^6)
        fee_tier = FEE_TIERS[tier]

        #gas cost with the tier from above
        gas_costs = self.get_gas_cost(fee_tier)

        #calculate how much of your input is eaten up by fees and how much is actually swapped
        if self.q_type == "EXACT_INPUT":
            #the estimate is for the output
            fee = (self.raw_amount * fee_tier) // 10 ** 6
            res = {"swapped": self.raw_amount - fee, "swap_fee": fee, "output": estimate}
        else:
            fee = (estimate * fee_tier) // 10 ** 6
            res = {"swapped": estimate - fee, "swap_fee": fee, "output": self.raw_amount}
        res.update(gas_costs)
        return res