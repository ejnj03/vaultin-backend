# vault-prices

**Archived. Not deployed by SAM, and not currently used by the frontend.**

CoinGecko-backed USD price endpoint, recovered from the deployed `vault-prices`
Lambda on 2026-08-14. This source previously existed **only** as a deployed
artifact in AWS — it was never committed. It is preserved here so the function
can be deleted from AWS without losing the implementation (see PLT-8).

## What it did

`GET /prices?ids=eth,usdc,...` returns `{id: {usd, usd_24h_change, last_updated_at}}`.
Defaults to `pol, usdc, usdt, eth` when `ids` is absent.

Read-through cache: each id is looked up in the DynamoDB table
`vault-token-prices` (key `cacheKey`). Anything older than `STALE_WINDOW`
(60s, measured against CoinGecko's own `last_updated_at`) is refetched in a
single batched CoinGecko call and written back. Refresh is lazy — there is no
scheduled warmer, so the first request after an idle period pays full API
latency.

It was served by API Gateway `9djqt1k5r5` ("vault-api"), the pre-SAM deployment.
The frontend now gets prices from a Coinbase `ticker` WebSocket in
`src/contexts/CryptoDataContext.jsx` instead.

## Before redeploying

The recovered source had a **hardcoded CoinGecko API key** in `price_utils.py`.
It has been replaced with a Secrets Manager read from `vault-prices-secrets`
(key `COINGECKO_API_KEY`), matching the pattern in `vault-payments/auth/secrets.py`.
**The original key was exposed in a deployed artifact and should be rotated.**

Other known issues, unfixed here to keep this a faithful archive:

- A CoinGecko failure returns 502 for the whole request, discarding cached
  entries that were still fresh.
- The deployed function had a 3s timeout while making an external HTTP call
  with no timeout on `urlopen`.
- Ids that CoinGecko does not return are silently omitted from the response.
- There is no SAM template; the function, its IAM role, and the DynamoDB table
  were all created by hand.
