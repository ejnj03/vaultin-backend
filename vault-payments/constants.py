SUPPORTED_TOKENS = {
    "arbitrum": {
        "chainId": 42161,
        "tokens": {
            "ETH":  {"address": "0x0000000000000000000000000000000000000000", "decimals": 18},
            "USDC": {"address": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", "decimals": 6},
            "USDT": {"address": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9", "decimals": 6},
        },
    },
    "polygon": {
        "chainId": 137,
        "tokens": {
            "POL":  {"address": "0x0000000000000000000000000000000000000000", "decimals": 18},
            "USDC": {"address": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", "decimals": 6},
            "USDT": {"address": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F", "decimals": 6},
        },
    },
    "optimism": {
        "chainId": 10,
        "tokens": {
            "ETH":  {"address": "0x0000000000000000000000000000000000000000", "decimals": 18},
            "USDC": {"address": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", "decimals": 6},
            "USDT": {"address": "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58", "decimals": 6},
        },
    },
    "base": {
        "chainId": 8453,
        "tokens": {
            "ETH":  {"address": "0x0000000000000000000000000000000000000000", "decimals": 18},
            "USDC": {"address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "decimals": 6},
        },
    },
    "ethereum": {
        "chainId": 1,
        "tokens": {
            "ETH":  {"address": "0x0000000000000000000000000000000000000000", "decimals": 18},
            "USDC": {"address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "decimals": 6},
            "USDT": {"address": "0xdAC17F958D2ee523a2206206994597C13D831ec7", "decimals": 6},
        },
    },
}

RPC_URLS = {
    1: "https://eth-mainnet.g.alchemy.com/v2/",
    42161: "https://arb-mainnet.g.alchemy.com/v2/",
    8453: "https://base-mainnet.g.alchemy.com/v2/",
    10: "https://opt-mainnet.g.alchemy.com/v2/",
    137: "https://polygon-mainnet.g.alchemy.com/v2/",
}

WETH_ADDRESSES = {
    1: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",      # Ethereum
    42161: "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",    # Arbitrum
    10: "0x4200000000000000000000000000000000000006",        # Optimism
    8453: "0x4200000000000000000000000000000000000006",       # Base
    137: "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",      # Polygon (WMATIC)
}

