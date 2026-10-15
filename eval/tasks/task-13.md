# Task 13 — operation: light edit

## Request
Light edit this doc section. Don't restructure it.

## Material
```
DRAFT:
## Rate limits

The API enforces rate limits. Requests are limited to 1000 per hour per API
key. If you exceed this limit you will receive a 429 response. The limit
resets on a rolling window basis. It is important to note that you should
implement exponential backoff in your client. Additionally, bulk endpoints
have a separate limit of 50 requests per hour. Enterprise customers can
request a higher limit by contacting support.
```
