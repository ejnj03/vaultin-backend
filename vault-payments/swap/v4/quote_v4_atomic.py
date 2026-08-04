from web3 import Web3
from concurrent.futures import ThreadPoolExecutor
from constants import RPC_URLS
from swap.v4.uniswap_v4_constants import get_uniswap_v4_config, build_pool_key, UNIVERSAL_ROUTER_ABI, V4_QUOTER_ABI, ERC20_ABI
from swap.v4.permit2atomic import Permit2AtomicManager
from swap.v4.encoder import encode_exact_in, encode_exact_out, build_execute_inputs
from auth.secrets import ALCHEMY_API_KEY
import time
from swap.v4.utils import utc_interval

PERMIT_EXPIRATION = utc_interval(minutes=10)

NATIVE_ZERO = "0x0000000000000000000000000000000000000000"
FEE_TIERS = {"0.01%": 100, "0.05%": 500, "0.3%": 3000, "1%": 10000}

SLIPPAGE_BPS = 50
GAS_FACTOR = 1.2
TIME_LIMIT = 300


def is_native(addr):
    return addr == NATIVE_ZERO


class SwapQuoteV4Atomic:
    def __init__(self, q_type, raw_amount, chain_id, from_tok_addr, to_tok_addr,
                 user_address, recipient, preference, urgency):
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

        self.slippage_bps = SLIPPAGE_BPS
        self.gas_factor = GAS_FACTOR
        self.time_limit = PERMIT_EXPIRATION

        self.w3 = Web3(Web3.HTTPProvider(f"{RPC_URLS[chain_id]}{ALCHEMY_API_KEY}"))
        router_addr, _, quoter_addr, permit2_addr = get_uniswap_v4_config(chain_id)
        self.router_addr = router_addr
        self.quoter = self.w3.eth.contract(address=quoter_addr, abi=V4_QUOTER_ABI)
        self.router = self.w3.eth.contract(address=router_addr, abi=UNIVERSAL_ROUTER_ABI)
        self.tokenin = self.w3.eth.contract(address=from_tok_addr, abi=ERC20_ABI)
        self.permit2 = Permit2AtomicManager(
            self.w3,
            self.user_address,
            permit2_addr,
            router_addr,
            self.from_tok_addr,
            self.router,
            self.tokenin,
            chain_id,
            slippage_bps=self.slippage_bps,
            gas_factor=self.gas_factor,
            time_limit=self.time_limit,
        )

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

    def _encode_swap(self, fee, estimate):
        """
        Returns (encoded_swap: bytes, eth_value: int).
        value parameter is in value for eth swaps
        """
        pool_key, zero_for_one = build_pool_key(self.from_tok_addr, self.to_tok_addr, fee)

        if self.q_type == "EXACT_INPUT":
            amount_out_min = estimate * (10000 - self.slippage_bps) // 10000
            encoded = encode_exact_in(pool_key, zero_for_one, self.from_tok_addr, self.to_tok_addr, self.raw_amount, amount_out_min, self.recipient)
            amount_in_max = self.raw_amount
        else:
            amount_in_max = estimate * (10000 + self.slippage_bps) // 10000
            encoded = encode_exact_out(pool_key, zero_for_one, self.from_tok_addr, self.to_tok_addr, self.raw_amount, amount_in_max, self.recipient)

        return encoded, amount_in_max

    def _build_execute_args(self, fee, estimate):
        encoded_swap, amount_in_max = self._encode_swap(fee, estimate)
        command, inputs = build_execute_inputs(encoded_swap) 
        return command, inputs, amount_in_max

    # ── Gas + contract formatting ────────────────────────────────────────────

    def _estimate_gas(self, fee, estimate, fallback=200000):
        commands, inputs, eth_value = self._build_execute_args(fee, estimate)
        deadline = int(time.time()) + self.time_limit
        try:
            return self.router.functions.execute(commands, inputs, deadline).estimate_gas(
                {'from': self.user_address, 'value': eth_value}
            )
        except Exception as e:
            print(f"[V4] execute estimate_gas FAILED: {e}")
            return fallback

    def _build_swap_contract(self, commands, inputs, eth_value, gas):
        data = self.router.encode_abi(
            "execute",
            args=["0x" + commands.hex(), ["0x" + i.hex() for i in inputs], int(time.time()) + self.time_limit],
        )

        txn = {
            "to": self.router_addr,
            "data": data,
            "gas": int(self.gas_factor * gas),
        }

        if eth_value > 0: #if input token is eth (native)
            txn["value"] = eth_value
        return txn

    # ── Main entry point ─────────────────────────────────────────────────────

    def get_quote(self):
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
        erc20_txn = self.permit2.check_erc20_approval(input_amount) if not self.native_input else None
        txns = [erc20_txn] if erc20_txn else []
        

        #Router for executing swap -> my Wallet (amount out)
        gas = self._estimate_gas(fee, estimate)
        command, inputs, in_max_amount = self._build_execute_args(fee, estimate)

        # Check if permit2 signing is needed (Permit2 -> Router on-chain approval)
        permit2_txn = self.permit2.check_permit(in_max_amount)
        if permit2_txn:
            txns.append(permit2_txn)

        if self.native_input:
            eth_value = in_max_amount
        else:
            eth_value = 0

        #compute net gas from the approve txns (erc20->permit2,)
        approval_gas = 0
        for txn in txns:
            approval_gas += txn["gas"] 
        
        if approval_gas > 0:
            metadata["approval_gas"] = approval_gas

        swap_txn = self._build_swap_contract(command, inputs, eth_value, gas)
        txns.append(swap_txn)
        
        #approved if X need addtl erc20 txn

        metadata.update({"is_approved": not erc20_txn, "transaction_gas": txns[-1]["gas"]})
        return {"metadata": metadata, "contracts": txns}
