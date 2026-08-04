from web3 import Web3

"""
Uniswap V4 contract addresses per chain (Universal Router + PoolManager + V4Quoter + Permit2).

V4 uses IDENTICAL contracts and ABIs across ALL chains. The only difference is deployed addresses.
The Universal Router replaces SwapRouter entirely — swaps use command-based encoding.

Flow: Token.approve(Permit2) → Permit2.approve(UniversalRouter) → UniversalRouter.execute()

Source: https://docs.uniswap.org/contracts/v4/deployments
"""

# ─── Chain IDs ───────────────────────────────────────────────────────────────
ETHEREUM = 1
ARBITRUM = 42161
OPTIMISM = 10
POLYGON = 137
BASE = 8453

# ─── Universal Router addresses per chain ────────────────────────────────────
UNIVERSAL_ROUTER = {
    ETHEREUM:  "0x66a9893cc07d91d95644aedd05d03f95e1dba8af",
    ARBITRUM:  "0xa51afafe0263b40edaef0df8781ea9aa03e381a3",
    OPTIMISM:  "0x851116d9223fabed8e56c0e6b8ad0c31d98b3507",
    POLYGON:   "0x1095692a6237d83c6a72f3f5efedb9a670c49223",
    BASE:      "0x6ff5693b99212da76ad316178a184ab56d299b43",
}

# ─── PoolManager addresses per chain ─────────────────────────────────────────
POOL_MANAGER = {
    ETHEREUM:  "0x000000000004444c5dc75cB358380D2e3dE08A90",
    ARBITRUM:  "0x360e68faccca8ca495c1b759fd9eee466db9fb32",
    OPTIMISM:  "0x9a13f98cb987694c9f086b1f5eb990eea8264ec3",
    POLYGON:   "0x67366782805870060151383f4bbff9dab53e5cd6",
    BASE:      "0x498581ff718922c3f8e6a244956af099b2652b2b",
}

# ─── V4 Quoter addresses per chain ──────────────────────────────────────────
V4_QUOTER = {
    ETHEREUM:  "0x52f0e24d1c21c8a0cb1e5a5dd6198556bd9e1203",
    ARBITRUM:  "0x3972c00f7ed4885e145823eb7c655375d275a1c5",
    OPTIMISM:  "0x1f3131a13296fb91c90870043742c3cdbff1a8d7",
    POLYGON:   "0xb3d5c3dfc3a7aebff71895a7191796bffc2c81b9",
    BASE:      "0x0d5e0f971ed27fbff6c2837bf31316121532048d",
}

# ─── StateView addresses per chain ───────────────────────────────────────────
STATE_VIEW = {
    ETHEREUM:  "0x7ffe42c4a5deea5b0fec41c94c136cf115597227",
    ARBITRUM:  "0x76fd297e2d437cd7f76d50f01afe6160f86e9990",
    OPTIMISM:  "0xc18a3169788f4f75a170290584eca6395c75ecdb",
    POLYGON:   "0x5ea1bd7974c8a611cbab0bdcafcb1d9cc9b3ba5a",
    BASE:      "0xa3c0c9b65bad0b08107aa264b0f3db444b867a71",
}

# ─── Permit2 address (SAME on all chains via CREATE2) ───────────────────────
PERMIT2 = "0x000000000022D473030F116dDEE9F6B43aC78BA3"

# ─── Zero address for hooks (no hooks = standard pool) ──────────────────────
NO_HOOKS = "0x0000000000000000000000000000000000000000"

# ─── Fee tiers → tick spacings ───────────────────────────────────────────────
FEE_TIERS = {
    100:   1,    # 0.01% fee, tickSpacing 1   (stablecoin pairs)
    500:   10,   # 0.05% fee, tickSpacing 10  (stable/major pairs)
    3000:  60,   # 0.30% fee, tickSpacing 60  (most pairs)
    10000: 200,  # 1.00% fee, tickSpacing 200 (exotic pairs)
}

# ─── Command constants ───────────────────────────────────────────────────────
class Commands:
    V4_SWAP              = 0x10
    WRAP_ETH             = 0x0B
    UNWRAP_WETH          = 0x0C
    PERMIT2_PERMIT       = 0x0A

# ─── Action constants ────────────────────────────────────────────────────────
class Actions:
    SWAP_EXACT_IN_SINGLE  = 0x06
    SWAP_EXACT_OUT_SINGLE = 0x08
    SETTLE_ALL            = 0x0C
    TAKE                  = 0x0E
    TAKE_ALL              = 0x0F

# ─── Universal Router ABI ────────────────────────────────────────────────────
UNIVERSAL_ROUTER_ABI = [
    {
        "inputs": [
            {"name": "commands", "type": "bytes"},
            {"name": "inputs", "type": "bytes[]"},
            {"name": "deadline", "type": "uint256"}
        ],
        "name": "execute",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "commands", "type": "bytes"},
            {"name": "inputs", "type": "bytes[]"}
        ],
        "name": "execute",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]

# ─── V4 Quoter ABI ──────────────────────────────────────────────────────────
V4_QUOTER_ABI = [
    {
        "inputs": [
            {"components": [
                {"components": [
                    {"name": "currency0", "type": "address"},
                    {"name": "currency1", "type": "address"},
                    {"name": "fee", "type": "uint24"},
                    {"name": "tickSpacing", "type": "int24"},
                    {"name": "hooks", "type": "address"}
                ], "name": "poolKey", "type": "tuple"},
                {"name": "zeroForOne", "type": "bool"},
                {"name": "exactAmount", "type": "uint128"},
                {"name": "hookData", "type": "bytes"}
            ], "name": "params", "type": "tuple"}
        ],
        "name": "quoteExactInputSingle",
        "outputs": [
            {"name": "amountOut", "type": "uint256"},
            {"name": "gasEstimate", "type": "uint256"}
        ],
        "type": "function"
    },
    {
        "inputs": [
            {"components": [
                {"components": [
                    {"name": "currency0", "type": "address"},
                    {"name": "currency1", "type": "address"},
                    {"name": "fee", "type": "uint24"},
                    {"name": "tickSpacing", "type": "int24"},
                    {"name": "hooks", "type": "address"}
                ], "name": "poolKey", "type": "tuple"},
                {"name": "zeroForOne", "type": "bool"},
                {"name": "exactAmount", "type": "uint128"},
                {"name": "hookData", "type": "bytes"}
            ], "name": "params", "type": "tuple"}
        ],
        "name": "quoteExactOutputSingle",
        "outputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "gasEstimate", "type": "uint256"}
        ],
        "type": "function"
    }
]

# ─── Permit2 ABI ────────────────────────────────────────────────────────────
PERMIT2_ABI = [
    {
        "inputs": [
            {"name": "token", "type": "address"},
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint160"},
            {"name": "expiration", "type": "uint48"}
        ],
        "name": "approve",
        "outputs": [],
        "type": "function"
    },
    {
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "token", "type": "address"},
            {"name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [
            {"name": "amount", "type": "uint160"},
            {"name": "expiration", "type": "uint48"},
            {"name": "nonce", "type": "uint48"}
        ],
        "type": "function"
    }
]

# ─── ERC20 ABI ───────────────────────────────────────────────────────────────
ERC20_ABI = [
    {
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    },
    {
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _cs(addr):
    """Checksum an address."""
    return Web3.to_checksum_address(addr)


def get_uniswap_v4_config(chain_id):
    """Returns (universal_router, pool_manager, quoter, permit2) for the given chain."""
    if chain_id not in UNIVERSAL_ROUTER:
        raise ValueError(f"Uniswap V4 not configured for chain {chain_id}")
    return (
        _cs(UNIVERSAL_ROUTER[chain_id]),
        _cs(POOL_MANAGER[chain_id]),
        _cs(V4_QUOTER[chain_id]),
        _cs(PERMIT2),
    )


def build_pool_key(token_a, token_b, fee=3000, hooks=NO_HOOKS):
    """
    Build a PoolKey tuple for V4. Currencies are sorted (lower address first).
    Returns (currency0, currency1, fee, tickSpacing, hooks) and zeroForOne direction.
    """
    token_a = _cs(token_a)
    token_b = _cs(token_b)
    hooks = _cs(hooks)
    tick_spacing = FEE_TIERS[fee]
    a_int = int(token_a, 16)
    b_int = int(token_b, 16)
    if a_int < b_int:
        return (token_a, token_b, fee, tick_spacing, hooks), True
    else:
        return (token_b, token_a, fee, tick_spacing, hooks), False
