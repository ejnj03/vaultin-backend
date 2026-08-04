"""
Uniswap V3 contract addresses per chain.

IMPORTANT: Ethereum, Arbitrum, Optimism, and Polygon use the original V1 SwapRouter + Quoter.
Base uses SwapRouter02 + QuoterV2 which have different ABIs (struct-based params for quoter).

Source: https://docs.uniswap.org/contracts/v3/reference/deployments/
"""

# ─── Chain IDs ───────────────────────────────────────────────────────────────
ETHEREUM = 1
ARBITRUM = 42161
OPTIMISM = 10
POLYGON = 137
BASE = 8453

# ─── Router addresses per chain ──────────────────────────────────────────────
UNISWAP_ROUTER = {
    ETHEREUM:  "0xE592427A0AEce92De3Edee1F18E0157C05861564",  # SwapRouter (V1)
    ARBITRUM:  "0xE592427A0AEce92De3Edee1F18E0157C05861564",  # SwapRouter (V1)
    OPTIMISM:  "0xE592427A0AEce92De3Edee1F18E0157C05861564",  # SwapRouter (V1)
    POLYGON:   "0xE592427A0AEce92De3Edee1F18E0157C05861564",  # SwapRouter (V1)
    BASE:      "0x2626664c2603336E57B271c5C0b26F421741e481",  # SwapRouter02 (V2)
}

# ─── Quoter addresses per chain ──────────────────────────────────────────────
UNISWAP_QUOTER = {
    ETHEREUM:  "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6",  # Quoter (V1)
    ARBITRUM:  "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6",  # Quoter (V1)
    OPTIMISM:  "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6",  # Quoter (V1)
    POLYGON:   "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6",  # Quoter (V1)
    BASE:      "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a",  # QuoterV2
}

# ─── Which version each chain uses ───────────────────────────────────────────
UNISWAP_VERSION = {
    ETHEREUM:  "v1",
    ARBITRUM:  "v1",
    OPTIMISM:  "v1",
    POLYGON:   "v1",
    BASE:      "v2",
}

# ─── V1 ABIs (SwapRouter + Quoter) ──────────────────────────────────────────
# Used by: Ethereum, Arbitrum, Optimism, Polygon

QUOTER_ABI_V1 = [
    {
        "inputs": [
            {"name": "tokenIn", "type": "address"},
            {"name": "tokenOut", "type": "address"},
            {"name": "fee", "type": "uint24"},
            {"name": "amountIn", "type": "uint256"},
            {"name": "sqrtPriceLimitX96", "type": "uint160"}
        ],
        "name": "quoteExactInputSingle",
        "outputs": [{"name": "amountOut", "type": "uint256"}],
        "type": "function"
    },
    {
        "inputs": [
            {"name": "tokenIn", "type": "address"},
            {"name": "tokenOut", "type": "address"},
            {"name": "fee", "type": "uint24"},
            {"name": "amountOut", "type": "uint256"},
            {"name": "sqrtPriceLimitX96", "type": "uint160"}
        ],
        "name": "quoteExactOutputSingle",
        "outputs": [{"name": "amountIn", "type": "uint256"}],
        "type": "function"
    }
]

ROUTER_ABI_V1 = [
    {
        "inputs": [
            {"components": [
                {"name": "tokenIn", "type": "address"},
                {"name": "tokenOut", "type": "address"},
                {"name": "fee", "type": "uint24"},
                {"name": "recipient", "type": "address"},
                {"name": "deadline", "type": "uint256"},
                {"name": "amountIn", "type": "uint256"},
                {"name": "amountOutMinimum", "type": "uint256"},
                {"name": "sqrtPriceLimitX96", "type": "uint160"}
            ], "name": "params", "type": "tuple"}
        ],
        "name": "exactInputSingle",
        "outputs": [{"name": "amountOut", "type": "uint256"}],
        "type": "function"
    },
    {
        "inputs": [
            {"components": [
                {"name": "tokenIn", "type": "address"},
                {"name": "tokenOut", "type": "address"},
                {"name": "fee", "type": "uint24"},
                {"name": "recipient", "type": "address"},
                {"name": "deadline", "type": "uint256"},
                {"name": "amountOut", "type": "uint256"},
                {"name": "amountInMaximum", "type": "uint256"},
                {"name": "sqrtPriceLimitX96", "type": "uint160"}
            ], "name": "params", "type": "tuple"}
        ],
        "name": "exactOutputSingle",
        "outputs": [{"name": "amountIn", "type": "uint256"}],
        "type": "function"
    }
]

# ─── V2 ABIs (SwapRouter02 + QuoterV2) ──────────────────────────────────────
# Used by: Base
# Key differences from V1:
# - QuoterV2.quoteExactInputSingle takes a struct param instead of positional args
# - QuoterV2 returns additional data (sqrtPriceX96After, initializedTicksCrossed, gasEstimate)
# - SwapRouter02 does NOT include deadline in the struct (uses separate multicall with deadline)

QUOTER_ABI_V2 = [
    {
        "inputs": [
            {"components": [
                {"name": "tokenIn", "type": "address"},
                {"name": "tokenOut", "type": "address"},
                {"name": "amountIn", "type": "uint256"},
                {"name": "fee", "type": "uint24"},
                {"name": "sqrtPriceLimitX96", "type": "uint160"}
            ], "name": "params", "type": "tuple"}
        ],
        "name": "quoteExactInputSingle",
        "outputs": [
            {"name": "amountOut", "type": "uint256"},
            {"name": "sqrtPriceX96After", "type": "uint160"},
            {"name": "initializedTicksCrossed", "type": "uint32"},
            {"name": "gasEstimate", "type": "uint256"}
        ],
        "type": "function"
    },
    {
        "inputs": [
            {"components": [
                {"name": "tokenIn", "type": "address"},
                {"name": "tokenOut", "type": "address"},
                {"name": "amount", "type": "uint256"},
                {"name": "fee", "type": "uint24"},
                {"name": "sqrtPriceLimitX96", "type": "uint160"}
            ], "name": "params", "type": "tuple"}
        ],
        "name": "quoteExactOutputSingle",
        "outputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "sqrtPriceX96After", "type": "uint160"},
            {"name": "initializedTicksCrossed", "type": "uint32"},
            {"name": "gasEstimate", "type": "uint256"}
        ],
        "type": "function"
    }
]

ROUTER_ABI_V2 = [
    {
        "inputs": [
            {"components": [
                {"name": "tokenIn", "type": "address"},
                {"name": "tokenOut", "type": "address"},
                {"name": "fee", "type": "uint24"},
                {"name": "recipient", "type": "address"},
                {"name": "amountIn", "type": "uint256"},
                {"name": "amountOutMinimum", "type": "uint256"},
                {"name": "sqrtPriceLimitX96", "type": "uint160"}
            ], "name": "params", "type": "tuple"}
        ],
        "name": "exactInputSingle",
        "outputs": [{"name": "amountOut", "type": "uint256"}],
        "type": "function"
    },
    {
        "inputs": [
            {"components": [
                {"name": "tokenIn", "type": "address"},
                {"name": "tokenOut", "type": "address"},
                {"name": "fee", "type": "uint24"},
                {"name": "recipient", "type": "address"},
                {"name": "amountOut", "type": "uint256"},
                {"name": "amountInMaximum", "type": "uint256"},
                {"name": "sqrtPriceLimitX96", "type": "uint160"}
            ], "name": "params", "type": "tuple"}
        ],
        "name": "exactOutputSingle",
        "outputs": [{"name": "amountIn", "type": "uint256"}],
        "type": "function"
    }
]

# ─── ERC20 ABI (same across all chains) ─────────────────────────────────────

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
    },
    {
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]


# ─── Helper to get the right addresses and ABIs for a chain ──────────────────

def get_uniswap_config(chain_id):
    """
    Returns (router_address, quoter_address, router_abi, quoter_abi, version)
    for the given chain_id.
    """
    version = UNISWAP_VERSION.get(chain_id)
    if not version:
        raise ValueError(f"Uniswap V3 not configured for chain {chain_id}")

    router_addr = UNISWAP_ROUTER[chain_id]
    quoter_addr = UNISWAP_QUOTER[chain_id]

    if version == "v2":
        return router_addr, quoter_addr, ROUTER_ABI_V2, QUOTER_ABI_V2, version
    else:
        return router_addr, quoter_addr, ROUTER_ABI_V1, QUOTER_ABI_V1, version
