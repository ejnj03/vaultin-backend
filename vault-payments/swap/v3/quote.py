from web3 import Web3
from concurrent.futures import ThreadPoolExecutor
from constants import RPC_URLS, WETH_ADDRESSES
from swap.v3.uniswap_constants import get_uniswap_config, ERC20_ABI
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
        self.native_input = is_native(from_tok_addr)

        if self.native_input:
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
        router_addr, quoter_addr, router_abi, quoter_abi, self.version = get_uniswap_config(chain_id)
        self.router_addr = router_addr
        self.quoter_contract = self.w3.eth.contract(address=quoter_addr, abi=quoter_abi)
        self.router_contract = self.w3.eth.contract(address=router_addr, abi=router_abi)

    def _quote_from_input(self, fee_tier, price_limit=0):
        try:
            fee = FEE_TIERS[fee_tier]
            if self.version == "v2":
                result = self.quoter_contract.functions.quoteExactInputSingle(
                    (self.from_tok_addr, self.to_tok_addr, self.raw_amount, fee, price_limit)
                ).call()
                return fee_tier, result[0]
            else:
                output = self.quoter_contract.functions.quoteExactInputSingle(
                    self.from_tok_addr, self.to_tok_addr, fee, self.raw_amount, price_limit
                ).call()
                return fee_tier, output
        except Exception:
            return fee_tier, None

    def _quote_from_output(self, fee_tier, price_limit=0):
        try:
            fee = FEE_TIERS[fee_tier]
            if self.version == "v2":
                result = self.quoter_contract.functions.quoteExactOutputSingle(
                    (self.from_tok_addr, self.to_tok_addr, self.raw_amount, fee, price_limit)
                ).call()
                return fee_tier, result[0]
            else:
                output = self.quoter_contract.functions.quoteExactOutputSingle(
                    self.from_tok_addr, self.to_tok_addr, fee, self.raw_amount, price_limit
                ).call()
                return fee_tier, output
        except Exception:
            return fee_tier, None

    def get_best_tier(self):
        print(f"get_best_tier called: q_type={self.q_type}, from={self.from_tok_addr}, to={self.to_tok_addr}, amount={self.raw_amount}, chain_connected={self.w3.is_connected()}")
        with ThreadPoolExecutor(max_workers=4) as executor:
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

    def get_gas_cost(self, fee_tier, estimate, time_limit=300, price_limit=0, slippage_bps=50, max_approval=2**256 - 1, gas_estimate=200000):
        """
        defaults:
        - time window for txn is 5 min (300 seconds)
        - price limit is None accept the price the pool gives
        - slippage_bps: slippage in basis points (50 = 0.5%)
        - if allowance is insufficient set it to max_approval amount so user approves once, never again
        - estimate: quoted token amount from the quoter (output for EXACT_INPUT, input for EXACT_OUTPUT)
        """
        if self.q_type == "EXACT_INPUT":
            input_amount = self.raw_amount
        else:
            input_amount = estimate

        if not self.native_input:
            token_contract = self.w3.eth.contract(address=self.from_tok_addr, abi=ERC20_ABI)
            allowance = token_contract.functions.allowance(self.user_address, self.router_addr).call()
            print(f"allowance={allowance}, input_amount={input_amount}, q_type={self.q_type}")
            if allowance < input_amount:
                    print(f"Estimating approval gas for {self.from_tok_addr}...")
                    approval_cost = token_contract.functions.approve(self.router_addr, max_approval).estimate_gas({'from': self.user_address})
                    print(f"Approval gas estimate: {approval_cost}")
                    return {"is_approved": False, "approval_gas": approval_cost, "gas_estimate": gas_estimate}

        deadline = int(time.time()) + time_limit
        if self.q_type == "EXACT_INPUT":
            amount_out_min = estimate * (10000 - slippage_bps) // 10000
            eth_value = self.raw_amount if self.native_input else 0
            print(f"Estimating exactInputSingle gas: amount={self.raw_amount}, amount_out_min={amount_out_min}, fee_tier={fee_tier}")
            if self.version == "v2":
                params = (self.from_tok_addr, self.to_tok_addr, fee_tier, self.recipient, self.raw_amount, amount_out_min, price_limit)
            else:
                params = (self.from_tok_addr, self.to_tok_addr, fee_tier, self.recipient, deadline, self.raw_amount, amount_out_min, price_limit)
            txn_cost = self.router_contract.functions.exactInputSingle(params).estimate_gas({'from': self.user_address, 'value': eth_value})
            print(f"exactInputSingle gas estimate: {txn_cost}")
        else:
            amount_in_max = estimate * (10000 + slippage_bps) // 10000
            eth_value = amount_in_max if self.native_input else 0
            print(f"Estimating exactOutputSingle gas: amount={self.raw_amount}, amount_in_max={amount_in_max}, fee_tier={fee_tier}")
            if self.version == "v2":
                params = (self.from_tok_addr, self.to_tok_addr, fee_tier, self.recipient, self.raw_amount, amount_in_max, price_limit)
            else:
                params = (self.from_tok_addr, self.to_tok_addr, fee_tier, self.recipient, deadline, self.raw_amount, amount_in_max, price_limit)
            txn_cost = self.router_contract.functions.exactOutputSingle(params).estimate_gas({'from': self.user_address, 'value': eth_value})
            print(f"exactOutputSingle gas estimate: {txn_cost}")

        return {"is_approved": True, "transaction_gas": txn_cost}
    
    def format_contracts(self, fee_tier, gas, estimate, gas_factor=1.2, time_limit=300, price_limit=0, slippage_bps=50, max_approval=2**256 - 1):
        contracts = []
        is_approved = gas["is_approved"]
        if not is_approved:
            contracts.append({
                "address": self.from_tok_addr,
                "abi": ERC20_ABI,
                "functionName": "approve",
                "args": [self.router_addr, hex(max_approval)],
                "gas": int(gas_factor * gas["approval_gas"])
            })
            transfer_gas = int(gas_factor * gas["gas_estimate"])
        else:
            transfer_gas = int(gas_factor * gas["transaction_gas"])

        deadline = int(time.time()) + time_limit

        if self.q_type == "EXACT_INPUT":
            amount_out_min = estimate * (10000 - slippage_bps) // 10000
            if self.version == "v2":
                args = [(self.from_tok_addr, self.to_tok_addr, fee_tier, self.recipient,
                         hex(self.raw_amount), hex(amount_out_min), price_limit)]
            else:
                args = [(self.from_tok_addr, self.to_tok_addr, fee_tier, self.recipient,
                         deadline, hex(self.raw_amount), hex(amount_out_min), price_limit)]
            swap_contract = {
                "address": self.router_addr,
                "abi": self.router_contract.abi,
                "functionName": "exactInputSingle",
                "args": args,
                "gas": transfer_gas
            }
            if self.native_input:
                swap_contract["value"] = hex(self.raw_amount)
            contracts.append(swap_contract)
        else:
            amount_in_max = estimate * (10000 + slippage_bps) // 10000
            if self.version == "v2":
                args = [(self.from_tok_addr, self.to_tok_addr, fee_tier, self.recipient,
                         hex(self.raw_amount), hex(amount_in_max), price_limit)]
            else:
                args = [(self.from_tok_addr, self.to_tok_addr, fee_tier, self.recipient,
                         deadline, hex(self.raw_amount), hex(amount_in_max), price_limit)]
            swap_contract = {
                "address": self.router_addr,
                "abi": self.router_contract.abi,
                "functionName": "exactOutputSingle",
                "args": args,
                "gas": transfer_gas
            }
            if self.native_input:
                swap_contract["value"] = hex(amount_in_max)
            contracts.append(swap_contract)
        return contracts
    
    def get_quote(self):
        #get the best fee tier
        tier, estimate = self.get_best_tier()
        #uniswap uses millionth (*10^6)
        fee_tier = FEE_TIERS[tier]

        #gas cost with the tier from above
        gas_costs = self.get_gas_cost(fee_tier, estimate)

        formatted_contracts = self.format_contracts(fee_tier, gas_costs, estimate)
        
        #calculate how much of your input is eaten up by fees and how much is actually swapped
        if self.q_type == "EXACT_INPUT":
            #the estimate is for the output
            fee = (self.raw_amount * fee_tier) // 10 ** 6
            res = {"swapped": self.raw_amount - fee, "swap_fee": fee, "output": estimate}
        else:
            fee = (estimate * fee_tier) // 10 ** 6
            res = {"swapped": estimate - fee, "swap_fee": fee, "output": self.raw_amount}
        res.update(gas_costs)

        return {"metadata": res, "contracts": formatted_contracts}