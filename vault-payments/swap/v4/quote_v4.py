from web3 import Web3
from concurrent.futures import ThreadPoolExecutor
from constants import RPC_URLS
from swap.v4.uniswap_v4_constants import get_uniswap_v4_config, build_pool_key, UNIVERSAL_ROUTER_ABI, V4_QUOTER_ABI
from swap.v4.permit2 import Permit2Manager
from swap.v4.encoder import encode_exact_in, encode_exact_out, build_execute_inputs
from auth.secrets import ALCHEMY_API_KEY
import time

NATIVE_ZERO = "0x0000000000000000000000000000000000000000"
FEE_TIERS = {"0.01%": 100, "0.05%": 500, "0.3%": 3000, "1%": 10000}


def is_native(addr):
    return addr == NATIVE_ZERO


class SwapQuoteV4:
    def __init__(self, q_type, raw_amount, chain_id, from_tok_addr, to_tok_addr,
                 user_address, recipient, preference, urgency, userConfig=None):
        self.q_type = q_type
        self.raw_amount = raw_amount
        self.native_input = is_native(from_tok_addr)
        self.from_tok_addr = from_tok_addr
        self.to_tok_addr = to_tok_addr
        self.user_address = user_address
        self.recipient = recipient
        self.preference = preference
        self.urgency = urgency
        self.chain_id = chain_id
        self.userConfig = userConfig

        self.w3 = Web3(Web3.HTTPProvider(f"{RPC_URLS[chain_id]}{ALCHEMY_API_KEY}"))
        router_addr, _, quoter_addr, permit2_addr = get_uniswap_v4_config(chain_id)
        self.router_addr = router_addr
        self.quoter = self.w3.eth.contract(address=quoter_addr, abi=V4_QUOTER_ABI)
        self.router = self.w3.eth.contract(address=router_addr, abi=UNIVERSAL_ROUTER_ABI)
        self.permit2 = Permit2Manager(self.w3, permit2_addr, router_addr, chain_id)

    # ── Quoting ─────────────────────────────────────────────────────────────

    def _quote_tier(self, fee_label):
        fee = FEE_TIERS[fee_label]
        pool_key, zero_for_one = build_pool_key(self.from_tok_addr, self.to_tok_addr, fee)
        try:
            if self.q_type == "EXACT_INPUT":
                result = self.quoter.functions.quoteExactInputSingle(
                    (pool_key, zero_for_one, self.raw_amount, b"")
                ).call()
            else:
                result = self.quoter.functions.quoteExactOutputSingle(
                    (pool_key, zero_for_one, self.raw_amount, b"")
                ).call()
            return fee_label, result[0]
        except Exception as e:
            print(f"[V4] quote failed for {fee_label}: {e}")
            return fee_label, None

    def get_best_tier(self):
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(self._quote_tier, FEE_TIERS.keys()))
        valid = [r for r in results if r[1] is not None and r[1] > 0]
        if not valid:
            raise ValueError("No valid V4 quotes found for this token pair.")
        return max(valid, key=lambda x: x[1]) if self.q_type == "EXACT_INPUT" else min(valid, key=lambda x: x[1])

    # ── Encoding ─────────────────────────────────────────────────────────────

    def _encode_swap(self, fee, estimate, slippage_bps=50):
        """Returns (encoded_swap: bytes, eth_value: int)."""
        pool_key, zero_for_one = build_pool_key(self.from_tok_addr, self.to_tok_addr, fee)

        if self.q_type == "EXACT_INPUT":
            amount_out_min = estimate * (10000 - slippage_bps) // 10000
            encoded = encode_exact_in(pool_key, zero_for_one, self.from_tok_addr, self.to_tok_addr, self.raw_amount, amount_out_min)
            eth_value = self.raw_amount if self.native_input else 0
        else:
            amount_in_max = estimate * (10000 + slippage_bps) // 10000
            encoded = encode_exact_out(pool_key, zero_for_one, self.from_tok_addr, self.to_tok_addr, self.raw_amount, amount_in_max)
            eth_value = amount_in_max if self.native_input else 0

        return encoded, eth_value

    def _build_execute_args(self, fee, estimate, slippage_bps=50, permit_data=None, permit2_signature=None):
        encoded_swap, eth_value = self._encode_swap(fee, estimate, slippage_bps)
        encoded_permit = self.permit2.encode_permit(permit_data, permit2_signature) if (permit_data and permit2_signature) else None
        commands, inputs = build_execute_inputs(encoded_swap, encoded_permit)
        return commands, inputs, eth_value

    # ── Gas + contract formatting ────────────────────────────────────────────

    def _estimate_gas(self, fee, estimate, slippage_bps=50, permit_data=None,
                      permit2_signature=None, time_limit=300, fallback=200000):
        commands, inputs, eth_value = self._build_execute_args(fee, estimate, slippage_bps, permit_data, permit2_signature)
        deadline = int(time.time()) + time_limit
        try:
            return self.router.functions.execute(commands, inputs, deadline).estimate_gas(
                {'from': self.user_address, 'value': eth_value}
            )
        except Exception as e:
            print(f"[V4] execute estimate_gas FAILED: {e}")
            return fallback

    def _build_swap_contract(self, fee, estimate, gas, slippage_bps=50, permit_data=None,
                             permit2_signature=None, gas_factor=1.2, time_limit=300):
        commands, inputs, eth_value = self._build_execute_args(fee, estimate, slippage_bps, permit_data, permit2_signature)
        contract = {
            "address": self.router_addr,
            "abi": UNIVERSAL_ROUTER_ABI,
            "functionName": "execute",
            "args": ["0x" + commands.hex(), ["0x" + i.hex() for i in inputs], int(time.time()) + time_limit],
            "gas": int(gas_factor * gas),
        }
        if eth_value > 0:
            contract["value"] = hex(eth_value)
        return contract

    # ── Main entry point ─────────────────────────────────────────────────────

    def get_quote(self, permit2_signature=None, permit_data=None):
        tier, estimate = self.get_best_tier()
        fee = FEE_TIERS[tier]
        input_amount = self.raw_amount if self.q_type == "EXACT_INPUT" else estimate

        swap_fee = (input_amount * fee) // 10 ** 6
        metadata = {
            "swap_fee": swap_fee,
            "swapped": input_amount - swap_fee,
            "output": estimate if self.q_type == "EXACT_INPUT" else self.raw_amount,
        }

        # ERC20 → Permit2 (one-time on-chain approval)
        erc20_contract = self.permit2.check_erc20_approval(self.from_tok_addr, self.user_address, input_amount) if not self.native_input else None
        erc20_contracts = [erc20_contract] if erc20_contract else []

        # If signed permit provided, build execute with PERMIT2_PERMIT + V4_SWAP
        if permit2_signature and permit_data:
            gas = self._estimate_gas(fee, estimate, permit_data=permit_data, permit2_signature=permit2_signature)
            swap = self._build_swap_contract(fee, estimate, gas, permit_data=permit_data, permit2_signature=permit2_signature)
            metadata.update({"is_approved": not erc20_contracts, "transaction_gas": gas})
            return {"metadata": metadata, "contracts": erc20_contracts + [swap]}

        # Check if permit2 signing is needed
        permit_data_for_signing = self.permit2.check_permit(self.from_tok_addr, self.user_address, input_amount)
        if permit_data_for_signing:
            metadata["is_approved"] = False
            return {"metadata": metadata, "contracts": erc20_contracts, "permit_data": permit_data_for_signing}

        # Already approved — just the swap
        gas = self._estimate_gas(fee, estimate)
        swap = self._build_swap_contract(fee, estimate, gas)
        metadata.update({"is_approved": not erc20_contracts, "transaction_gas": gas})
        return {"metadata": metadata, "contracts": erc20_contracts + [swap]}
