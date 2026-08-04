"""
Pure ABI encoding functions for Uniswap V4 Universal Router calldata.

No web3, no I/O — just bytes in, bytes out.
"""
from eth_abi import encode
from swap.v4.uniswap_v4_constants import Commands, Actions

POOL_KEY_TYPE = '(address,address,uint24,int24,address)'
SWAP_PARAMS_TYPE = f'({POOL_KEY_TYPE},bool,uint128,uint128,bytes)'


def encode_exact_in(pool_key, zero_for_one, from_addr, to_addr, amount_in, amount_out_min, recipient):
    """Encode V4_SWAP input bytes for an exact-input single-hop swap."""
    actions = bytes([Actions.SWAP_EXACT_IN_SINGLE, Actions.SETTLE_ALL, Actions.TAKE])
    swap_params   = encode([SWAP_PARAMS_TYPE], [(pool_key, zero_for_one, amount_in, amount_out_min, b"")])
    settle_params = encode(['address', 'uint256'], [from_addr, amount_in])
    take_params   = encode(['address', 'address', 'uint256'], [to_addr, recipient, amount_out_min])
    return encode(['bytes', 'bytes[]'], [actions, [swap_params, settle_params, take_params]])


def encode_exact_out(pool_key, zero_for_one, from_addr, to_addr, amount_out, amount_in_max, recipient):
    """Encode V4_SWAP input bytes for an exact-output single-hop swap."""
    actions = bytes([Actions.SWAP_EXACT_OUT_SINGLE, Actions.SETTLE_ALL, Actions.TAKE])
    swap_params   = encode([SWAP_PARAMS_TYPE], [(pool_key, zero_for_one, amount_out, amount_in_max, b"")])
    settle_params = encode(['address', 'uint256'], [from_addr, amount_in_max])
    take_params   = encode(['address', 'address', 'uint256'], [to_addr, recipient, amount_out])
    return encode(['bytes', 'bytes[]'], [actions, [swap_params, settle_params, take_params]])


def encode_permit2_permit(permit_data, signature):
    """Encode PERMIT2_PERMIT command input from a signed EIP-712 PermitSingle."""
    msg = permit_data["message"]
    details = msg["details"]
    permit_single = (
        (details["token"], int(details["amount"]), details["expiration"], details["nonce"]),
        msg["spender"],
        msg["sigDeadline"],
    )
    return encode(
        ['((address,uint160,uint48,uint48),address,uint256)', 'bytes'],
        [permit_single, bytes.fromhex(signature.replace("0x", ""))]
    )


def build_execute_inputs(encoded_swap, encoded_permit=None):
    """Assemble commands + inputs list for UniversalRouter.execute().

    Returns (commands: bytes, inputs: list[bytes]).
    Prepends PERMIT2_PERMIT if encoded_permit is provided.
    """
    if encoded_permit is not None:
        return bytes([Commands.PERMIT2_PERMIT, Commands.V4_SWAP]), [encoded_permit, encoded_swap]
    return bytes([Commands.V4_SWAP]), [encoded_swap]
