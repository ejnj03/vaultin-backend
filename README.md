# Vaultin — backend

Serverless backend for [Vaultin](https://github.com/einjun03/vaultin_frontend), a
non-custodial payments app on Ethereum. Send money to a username instead of an
address, request payments from friends, and swap tokens — without the app ever
holding a key.

Two AWS Lambda services behind API Gateway, deployed with AWS SAM. Python 3.11.

| Service | Responsibility |
| --- | --- |
| [`vault-auth/`](vault-auth) | Sign-In With Ethereum, sessions, profiles, fiat onramp tokens |
| [`vault-payments/`](vault-payments) | Social graph, payment requests, transaction ledger, swap quoting and calldata |

---

## The swap engine

The part worth reading first: [`vault-payments/swap/v4/`](vault-payments/swap/v4).

Vaultin builds **Uniswap V4 Universal Router calldata directly**, rather than
going through an aggregator API. V4 replaced per-pair pool contracts with a
singleton `PoolManager` and a flash-accounting model, so a swap is no longer one
call — it's a sequence of actions the router settles atomically.

[`encoder.py`](vault-payments/swap/v4/encoder.py) is a pure function library
— *"no web3, no I/O — just bytes in, bytes out"* — which keeps the encoding
independently testable, separate from anything that touches the network.

An exact-input single-hop swap encodes as three actions:

```
SWAP_EXACT_IN_SINGLE   (poolKey, zeroForOne, amountIn, amountOutMin, hookData)
SETTLE_ALL             (fromToken, amountIn)
TAKE                   (toToken, recipient, amountOutMin)
```

wrapped as `(bytes actions, bytes[] params)` and handed to
`UniversalRouter.execute()`.

**Permit2 in the same transaction.** Approvals are the standard second
transaction in any swap flow. [`permit2atomic.py`](vault-payments/swap/v4/permit2atomic.py)
prepends a `PERMIT2_PERMIT` command carrying a signed EIP-712 `PermitSingle`, so
approval and swap land in one user signature and one transaction
— see [`quote_v4_atomic.py`](vault-payments/swap/v4/quote_v4_atomic.py).

**V3 is still supported** ([`swap/v3/`](vault-payments/swap/v3)) since V4
liquidity is thin on many pairs. The quoter picks a route across both.

Nothing here signs. The backend returns unsigned calldata; the user's wallet
signs it. The service cannot move funds.

---

## Auth

Wallet-native sessions, no passwords, in [`vault-auth/`](vault-auth):

```
GET  /auth/nonce     → server nonce
                       client builds an EIP-4361 SiweMessage and signs it
POST /auth/verify    → signature checked, httpOnly session cookie issued
POST /auth/update_access
POST /auth/logout
```

The address recovered from the signature *is* the identity — there is no
account to create and no credential to steal. Usernames are a lookup layer on
top (`/auth/utils/find-addr/{username}`), which is what lets the app send to
`@alice` while the transaction still resolves to an address.

Also here: username validation and registration, profile photos via presigned S3
uploads, and Coinbase CDP session tokens for the fiat onramp.

## Payments and social

[`vault-payments/`](vault-payments) — a full friend graph, because paying people
by name only works if you know who they are:

```
POST /friends/send-friend-request     GET  /friends/get-received
POST /friends/accept-friend-request   GET  /friends/get-sent
POST /friends/reject-friend-request   GET  /friends/user-friends
POST /friends/friend-request/cancel
```

Payment requests carry their own state machine — created, responded to,
cancelled, or completed — with the transaction ledger recorded separately
(`/txns/log-txn`, `/txns/update-state`) so a request and its on-chain
settlement can be reconciled.

```
POST /payment-requests/create-request  POST /respond-request
GET  /payment-requests/sent            POST /cancel-request
GET  /payment-requests/received        POST /completed-request
POST /txns/get-quote
```

---

## Running it

**Prerequisites** — Python 3.11, [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html),
Docker (for `sam build --use-container`), and AWS credentials.

```bash
cd vault-payments
sam build
sam local start-api        # http://127.0.0.1:3000
```

Deploy:

```bash
sam build && sam deploy --guided     # first time; writes samconfig.toml
sam build && sam deploy              # subsequently
```

Repeat for `vault-auth`. Each service has its own `template.yaml` and deploys
independently.

### Secrets

Nothing is committed. Both services read from **AWS Secrets Manager** at cold
start ([`auth/secrets.py`](vault-payments/auth/secrets.py)), so the Lambda
execution role needs `secretsmanager:GetSecretValue` on:

| Secret | Keys |
| --- | --- |
| `vault-auth-secrets` | `ACCESS_SECRET` |
| `vault-payments-secrets` | `ALCHEMY_API_KEY` |

### Frontend

[`vaultin_frontend`](https://github.com/einjun03/vaultin_frontend) — Vite +
React, wagmi/viem, ConnectKit. Point its `VITE_AUTH_LAMBDA` at the deployed API
Gateway URL.

---

## Layout

```
vault-auth/
  lambda_function.py      route table
  cdp_auth.py             Coinbase CDP session tokens (fiat onramp)
  auth_utils.py           SIWE verification, session cookies
  user_register.py        registration + username validation
  profile.py              presigned S3 profile photo uploads
  db.py  config.py  utils.py

vault-payments/
  lambda_function.py      route table
  swap/
    quote.py              route selection across V3 and V4
    transfer.py           direct ERC-20 transfer calldata
    v3/                   V3 quoter + constants
    v4/
      encoder.py          Universal Router calldata — pure, no I/O
      permit2.py          EIP-712 PermitSingle construction
      permit2atomic.py    permit + swap in one transaction
      quote_v4.py         quoting against the V4 singleton
      quote_v4_atomic.py  quote + permit + encode, end to end
  payments/               transaction ledger, payment requests
  social/friends.py       friend request graph
  auth/                   shared session verification, Secrets Manager
  utils/                  responses, address/username lookup
```

`.aws-sam/` is build output and is gitignored — `sam build` regenerates it.
