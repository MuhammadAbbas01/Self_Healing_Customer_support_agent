# Golden set for the Self-Healing Customer Support RAG.
# Each item: (customer question, [phrases; a retrieved chunk containing ANY of them counts as a hit])

GOLDEN = [
 ("api keeps giving me 401, im sending my key in X-API-Key header", ["people keep using", "old authentication format"]),
 ("works fine in sandbox but dead in production??", ["DO NOT WORK on production", "keys don't work in production"]),
 ("is my api key supposed to be a certain length? i think it got cut when i copied", ["exactly 48 characters"]),
 ("got 403 forbidden but my key is valid", ["authenticated but not authorized"]),
 ("403 errors but only sometimes, my app runs on aws lambda", ["Lambda functions get different IPs", "Dynamic IPs are annoying"]),
 ("401 started after my free trial ended, key looks fine", ["suspended due to a failed payment"]),
 ("i accidentally pushed my live key to a public github repo, what now", ["we scan for this and auto-revoke", "GitHub Key Leak"]),
 ("how many requests per minute can i do on the free plan", ["60 requests per minute", "60 requests/minute"]),
 ("my script gets 429 too many requests, how should i retry", ["Handling 429 Too Many Requests", "DO implement exponential backoff"]),
 ("i check payment status every second and hit the limit, need higher limit", ["polling your API every second", "Customer polling instead of using webhooks"]),
 ("payments timing out during our flash sale, 504 gateway timeout", ["NOT a rate limit issue", "Payments timing out during our flash sale"]),
 ("customers got charged twice when they retried a failed payment", ["Use idempotency keys", "Duplicate transactions being created"]),
 ("why would a card get declined, what do the reason codes mean", ["AVS mismatch", "decline_code"]),
 ("after bank 3ds verification customers land on blank page", ["redirect URL in production", "3D Secure redirect not working"]),
 ("whats the biggest amount i can charge in one transaction", ["$100,000 per transaction"]),
 ("not receiving any webhook events on my endpoint", ["200 status within 10 seconds"]),
 ("if my webhook server is down how many times do you retry", ["After 5 failed attempts"]),
 ("how can i make sure a webhook really came from you", ["Security: Verify Signature", "Customer should verify"]),
 ("same webhook event delivered two times, is that a bug", ["ignore duplicates"]),
 ("subscription renewals not coming through but created and canceled events work", ["Subscription renewals failing silently"]),
 ("database says too many connections at peak hours", ["Connection Pool Exhaustion", "too many clients already"]),
 ("app freezes when it queries the db, connections never get released", ["Connection leak", "Use Connection Context Manager"]),
 ("got deadlock detected error in postgres", ["SKIP LOCKED"]),
 ("daily revenue query takes 5 seconds even with an index on created_at", ["prevents index usage"]),
 ("ssl certificate verify failed certificate has expired but your cert is valid", ["Check your system clock", "system clock was 2 years behind"]),
 ("ssl hostname mismatch error calling www.api.acme.com", ["Don't add www"]),
 ("page and per_page parameters stopped working on list endpoints", ["cursor-based pagination"]),
 ("my old v1 integration suddenly stopped working", ["shut down in December 2023"]),
 ("curl /v2/users returns 404 but docs say it exists", ["/v2/user (singular)"]),
 ("kubernetes pod keeps restarting with OOMKilled", ["OOMKilled"]),
]

UNANSWERABLE = [
 "do you support paypal payments",
 "how do i export all transactions to csv from the dashboard",
 "can you send me your soc2 compliance report",
 "is there a shopify plugin for your api",
 "do you have a mobile sdk for android",
]

TEST = [g for i, g in enumerate(GOLDEN) if i % 3 == 0]   # 10 held-out questions (final exam)
DEV  = [g for i, g in enumerate(GOLDEN) if i % 3 != 0]   # 20 questions for tuning (practice)