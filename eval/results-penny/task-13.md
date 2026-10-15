## Rate limits

Requests are limited to 1000 per hour per API key. If you exceed this limit, you
will receive a 429 response. The limit resets on a rolling window basis, so
implement exponential backoff in your client. Bulk endpoints have a separate
limit of 50 requests per hour. Enterprise customers can request a higher limit
by contacting support.