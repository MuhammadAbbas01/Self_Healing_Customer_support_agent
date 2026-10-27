import os

# Create documents directory
os.makedirs('/home/claude/documents', exist_ok=True)

# DOCUMENT 1: Company Technical Handbook (8000+ words, messy, mixed content)
doc1 = """
# ACME TECH COMPANY - TECHNICAL KNOWLEDGE BASE
Last Updated: Multiple dates (see sections)
Contributors: Various team members

## SECTION 1: COMPANY OVERVIEW & HISTORY
Founded in 2019, ACME Tech provides cloud-based payment processing and API services to over 5000 businesses worldwide. This document contains technical information, troubleshooting guides, internal notes, and historical context. Some sections may be outdated - always check the date stamps.

Our mission: To make payments simple. Our reality: Lots of bugs we're working on fixing.

## SECTION 2: GETTING STARTED (Written by Sarah, Jan 2022 - PARTIALLY OUTDATED)
When you first sign up, you'll receive an API key. In the old days (pre-2023), we used simple API keys like this:
X-API-Key: acme_1234567890

But we changed to OAuth2 in March 2023 (see Security Update section below). Don't use the old format anymore unless you're on our legacy plan.

To make your first API call:
1. Register at dashboard.acme.com
2. Generate credentials (see Authentication section)
3. Read the docs (ha ha, nobody does this)
4. Start coding
5. Hit errors
6. Read this document
7. Fix errors
8. Repeat steps 5-7 until it works

## SECTION 3: AUTHENTICATION & SECURITY
### Historical Context
We've had 3 different auth systems:

**Version 1 (2019-2022): Simple API Keys**
Format: acme_[random string]
Header: X-API-Key: acme_xxxxx
Status: DEPRECATED - Only works for legacy customers on old plans
Security: Terrible, we know. That's why we changed it.

**Version 2 (2022-2023): JWT Tokens**  
Format: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Header: Authorization: JWT [token]
Status: DEPRECATED as of March 2023
Why we killed it: Token expiry issues caused too many support tickets

**Version 3 (2023-present): Bearer Tokens**
Format: sk-live-[48 random characters] for production
Format: sk-test-[48 random characters] for testing
Header: Authorization: Bearer sk-live-xxxxx
Status: CURRENT - Use this!

### Common Authentication Errors

**ERROR: 401 Unauthorized**
This is our most common error. We see it in 40% of support tickets. Here's why it happens:

1. Missing Authorization header entirely
   - Fix: Add the header, obviously
   
2. Wrong format - people keep using "X-API-Key" from version 1
   - Fix: Use "Authorization: Bearer [key]"
   
3. Using test keys in production
   - Test keys (sk-test-xxx) DO NOT WORK on production endpoints
   - They only work on sandbox.acme.com
   - Production requires sk-live-xxx keys
   - Get production keys from dashboard.acme.com/settings/api
   
4. Expired tokens (only applies to old JWT system)
   - New Bearer tokens don't expire (thank god)
   - But they can be revoked if compromised
   
5. Copy-paste errors - the key got truncated
   - Keys are exactly 48 characters after the prefix
   - Total length: sk-live- (8 chars) + 48 chars = 56 characters total
   - If yours is different length, you copied wrong
   
6. Whitespace before/after the token
   - Seriously, trim your strings people

**ERROR: 403 Forbidden**
You're authenticated but not authorized. Reasons:

1. API key exists but account is suspended
   - Usually non-payment (check billing)
   - Or Terms of Service violation (you know what you did)
   
2. Trying to access enterprise endpoints on free plan
   - Upgrade your account
   - Or use the free tier endpoints instead
   
3. IP whitelist enabled but your IP isn't on it
   - Check dashboard.acme.com/settings/security
   - Add your IP or disable whitelist
   - Note: Dynamic IPs are annoying with this feature
   
4. API key was rotated but you're using the old one
   - We send email when keys are rotated
   - Check your spam folder
   - Generate new key if needed

### Security Best Practices
(Written after we had 3 security incidents in 2023)

- Never commit keys to GitHub (we scan for this and auto-revoke)
- Use environment variables
- Rotate keys every 90 days (we'll remind you)
- Use test keys for development
- Don't share keys between team members (each person gets their own)
- Enable IP whitelist if you have static IPs
- Monitor API usage for anomalies

One time, a customer posted their production API key in a public GitHub repo. Within 2 hours, someone found it and made 50,000 API calls. Don't be that customer.

## SECTION 4: API ENDPOINTS & RATE LIMITING

### Base URLs
Sandbox: https://sandbox.acme.com/v2/
Production: https://api.acme.com/v2/

Note: v1 API was shut down in December 2023. If you're still on v1, migrate now or your stuff will break.

### Rate Limits (Updated Jan 2024)
We've changed rate limits 5 times in the past 2 years because of abuse. Current limits:

**Free Tier:**
- 60 requests per minute
- 10,000 requests per day
- Burst: 100 requests in 10 seconds (then throttled)

**Pro Tier ($99/month):**
- 300 requests per minute
- 100,000 requests per day
- Burst: 500 requests in 10 seconds

**Enterprise:**
- Custom limits (usually 1000+ per minute)
- Dedicated infrastructure
- Contact sales for pricing

### Rate Limit Headers
Every API response includes these headers:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1709856000
```

X-RateLimit-Reset is Unix timestamp (seconds since epoch)

### Handling 429 Too Many Requests
When you hit rate limit, you get:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "retry_after": 60
  }
}
```

DO implement exponential backoff:
```python
import time

retry_count = 0
max_retries = 5

while retry_count < max_retries:
    response = requests.get(url, headers=headers)
    
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 60))
        wait_time = retry_after * (2 ** retry_count)
        print(f"Rate limited. Waiting {wait_time} seconds...")
        time.sleep(wait_time)
        retry_count += 1
    else:
        break
```

DON'T:
- Retry immediately without backoff
- Make parallel requests when you're already rate limited
- Complain in support tickets that our rate limits are too low (we hear this daily)

Pro tip: Cache responses when possible. 80% of API calls we see are requesting the same data over and over. Use Redis or similar.

## SECTION 5: PAYMENT PROCESSING

### Payment Endpoints
POST /v2/payments/charge - Create a charge
GET /v2/payments/{id} - Get payment status  
POST /v2/payments/{id}/refund - Refund a payment

### Common Payment Issues

**504 Gateway Timeout During High Traffic**
This is NOT a rate limit issue! (customers always think it is)

What's actually happening:
- Our payment processor (Stripe) has a 30-second timeout
- When traffic is high (>1000 concurrent payments), our backend queue fills up
- Requests wait in queue longer than 30 seconds
- Stripe times out
- You get 504

This typically happens:
- Black Friday / Cyber Monday
- Flash sales
- Product launches
- Beginning/end of month (subscription billing)

Solution (what we tell customers):
1. Don't process payments synchronously
2. Use async payment processing with webhooks
3. Return immediately to user: "Payment processing..."
4. Process in background queue
5. Webhook notifies you when complete

Code example:
```python
# BAD: Synchronous (can timeout)
@app.post("/checkout")
def checkout(payment_info):
    result = payment_api.charge(amount)  # Waits up to 30s
    return {"status": result.status}

# GOOD: Async with webhook
@app.post("/checkout")
def checkout(payment_info):
    payment_id = payment_api.initiate_charge(amount)
    # Return immediately
    return {"payment_id": payment_id, "status": "processing"}

# Webhook endpoint
@app.post("/webhooks/payment")
def payment_webhook(event):
    if event.type == "payment.succeeded":
        # Update order status
        # Send confirmation email
    elif event.type == "payment.failed":
        # Notify user
```

Internal note (from Mike): We really need to scale the payment service horizontally. The database connection pool keeps getting exhausted. TODO: Add read replicas and implement caching.

**Declined Payments**
Reasons payments get declined:
- Insufficient funds (most common)
- Card expired
- Wrong CVV
- AVS mismatch (billing address doesn't match card)
- Card reported stolen
- Velocity checks (too many charges in short time)
- Country restrictions

You get a `declined` status with a reason code:
```json
{
  "status": "declined",
  "decline_code": "insufficient_funds",
  "message": "Card has insufficient funds"
}
```

**Duplicate Transactions**
Use idempotency keys! Seriously, use them.

If you retry a failed payment without an idempotency key, you might charge the customer twice. We've had angry customers about this.
```python
headers = {
    'Authorization': 'Bearer sk-live-xxx',
    'Idempotency-Key': f'order-{order_id}-{timestamp}'
}
```

Same idempotency key = same request. We'll return the original result, not create a new charge.

## SECTION 6: ERROR CODES REFERENCE

We return standard HTTP status codes, but customers still don't understand them. Here's the guide we copy-paste into tickets:

### 400 Bad Request
Your request is malformed. Common causes:
- Invalid JSON syntax (missing comma, extra bracket, etc.)
- Missing required fields
- Wrong data types (sent string instead of number)
- Invalid parameter values

Example of bad request:
```json
{
  "amount": "100.50",  // Should be number, not string
  "currency": "dollars"  // Should be "USD", "EUR", etc.
}
```

### 401 Unauthorized  
See Authentication section above. You're not authenticated properly.

### 403 Forbidden
You're authenticated but not allowed to do this. See Authentication section.

### 404 Not Found
The endpoint or resource doesn't exist. Common mistakes:
- Wrong API version in URL (/v1/ instead of /v2/)
- Typo in endpoint name (/paymant/ instead of /payment/)
- Trying to access a resource that was deleted
- Using sandbox URL with production key (or vice versa)

### 409 Conflict
Resource already exists or there's a conflict. Usually:
- Duplicate transaction (use idempotency keys!)
- Trying to create something that already exists
- Concurrent modification (two requests modified same resource)

### 422 Unprocessable Entity
Request format is valid but data doesn't pass business logic validation:
- Amount too large (we cap at $100,000 per transaction)
- Amount too small (minimum $0.50)
- Invalid currency for your account region
- Email format invalid
- Phone number format invalid

### 429 Too Many Requests
See Rate Limiting section above.

### 500 Internal Server Error
Something broke on our end. Not your fault (probably).

What to do:
- Retry after a few seconds
- If it persists, check status.acme.com for incidents
- Contact support with the request ID from response headers

We log all 500 errors and investigate. Usually caused by:
- Database connection issues
- Third-party service outage (Stripe, AWS, etc.)
- Memory leak in our code (we're working on it)
- Deployment went wrong

### 502 Bad Gateway
Our load balancer can't reach the backend servers. Usually temporary.

Retry with exponential backoff. If persists >5 minutes, we probably have an outage.

### 503 Service Unavailable  
We're temporarily overloaded or doing maintenance.

Check response headers for Retry-After:
```
Retry-After: 120
```

Means try again in 120 seconds.

Scheduled maintenance windows:
- Every Saturday 2-4 AM UTC
- We send email notifications 48 hours in advance
- Check status.acme.com for real-time updates

### 504 Gateway Timeout
Request took longer than 30 seconds to process. See Payment Processing section for why this happens.

Not a rate limit issue! It's a performance/capacity issue on our backend.

## SECTION 7: WEBHOOKS

Webhooks notify you when events happen (payment succeeded, subscription canceled, etc.)

### Setup
1. Add webhook URL in dashboard: dashboard.acme.com/webhooks
2. URL must be HTTPS (not HTTP)
3. URL must be publicly accessible (not localhost)
4. Must return 200 status within 10 seconds

### Events We Send
- payment.succeeded
- payment.failed
- payment.refunded
- subscription.created
- subscription.canceled
- subscription.renewed
- account.suspended (hope you never get this one)

### Webhook Payload
```json
{
  "id": "evt_1234567890",
  "type": "payment.succeeded",
  "created": 1709856000,
  "data": {
    "payment_id": "pay_abc123",
    "amount": 5000,
    "currency": "USD"
  }
}
```

### Security: Verify Signature
Every webhook has a signature header:
```
X-Webhook-Signature: t=1709856000,v1=abc123def456...
```

Verify it:
```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    # Extract timestamp and signature
    parts = signature.split(',')
    timestamp = parts[0].split('=')[1]
    sig = parts[1].split('=')[1]
    
    # Compute expected signature
    signed_payload = f"{timestamp}.{payload}"
    expected = hmac.new(
        secret.encode(),
        signed_payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Compare
    return hmac.compare_digest(sig, expected)
```

Always verify! Otherwise, anyone can send fake webhooks to your endpoint.

### Retry Logic
If webhook delivery fails (non-200 response or timeout), we retry:
- Immediately
- After 5 minutes
- After 30 minutes  
- After 2 hours
- After 6 hours

After 5 failed attempts, we give up and mark it as failed. Check dashboard to see failed webhooks.

### Handling Duplicates
Webhooks might be delivered multiple times (network issues, retries, etc.)

Always check event ID and ignore duplicates:
```python
processed_events = set()  # Or use database

@app.post("/webhook")
def webhook(event):
    event_id = event['id']
    
    if event_id in processed_events:
        return {"status": "already_processed"}
    
    # Process event
    process_event(event)
    
    processed_events.add(event_id)
    return {"status": "ok"}
```

## SECTION 8: DATABASE & PERFORMANCE ISSUES

(Written by Mike after our Black Friday incident in 2023)

### Connection Pool Exhaustion

Our customers hit this a lot during traffic spikes. Symptoms:
- TimeoutError: Unable to acquire connection from pool
- OperationalError: Too many connections
- Application hangs when making database queries

Root causes:
1. Connection pool too small for traffic
2. Long-running queries blocking connections
3. Connections not being released (leaks)
4. Database itself at max connections

Solutions:

**Increase Pool Size**
```python
# Before  
engine = create_engine(DATABASE_URL, pool_size=10)

# After
engine = create_engine(
    DATABASE_URL,
    pool_size=30,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600  # Recycle connections every hour
)
```

**Use Connection Context Manager**
```python
# BAD: Connection leak
def get_user(user_id):
    conn = engine.connect()
    result = conn.execute("SELECT * FROM users WHERE id = ?", user_id)
    return result  # Connection never closed!

# GOOD: Auto-closes
def get_user(user_id):
    with engine.connect() as conn:
        result = conn.execute("SELECT * FROM users WHERE id = ?", user_id)
        return result.fetchone()
```

**Add Connection Pooling at Load Balancer**
PgBouncer is great for this. We use it internally.

**Implement Read Replicas**
80% of queries are reads. Send reads to replica, writes to primary:
```python
# Write to primary
primary_engine.execute("INSERT INTO payments ...")

# Read from replica
replica_engine.execute("SELECT * FROM payments WHERE ...")
```

### Slow Queries
Queries taking >2 seconds cause connection pool backup.

Find slow queries:
```sql
-- PostgreSQL
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

Common culprits:
- Missing indexes (add them!)
- SELECT * when you only need 2 columns
- N+1 queries (use JOINs or eager loading)
- Full table scans on large tables

Add indexes:
```sql
-- If you're filtering by user_id a lot
CREATE INDEX idx_payments_user_id ON payments(user_id);

-- If you're sorting by created_at
CREATE INDEX idx_payments_created ON payments(created_at DESC);
```

### Deadlocks
We see these occasionally when multiple transactions try to modify the same rows in different orders.

Error message:
```
OperationalError: deadlock detected
DETAIL: Process 1234 waits for ShareLock on transaction 5678...
```

Solutions:
- Retry the transaction (deadlocks are usually transient)
- Use `SELECT FOR UPDATE SKIP LOCKED` for queue-like tables
- Access tables in consistent order across all transactions
- Keep transactions short

Example with retry:
```python
max_retries = 3
for attempt in range(max_retries):
    try:
        with engine.begin() as conn:
            # Your transactional code here
            conn.execute(...)
            break
    except OperationalError as e:
        if 'deadlock' in str(e) and attempt < max_retries - 1:
            time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
            continue
        raise
```

## SECTION 9: SSL/TLS CERTIFICATE ISSUES

### Certificate Errors
**Error: certificate verify failed: certificate has expired**

Our SSL cert expired once in 2022. It was a bad day. Now we have auto-renewal set up.

For customers getting this error:
1. Check your system clock (wrong time causes this)
2. Update your CA certificates bundle
3. If using custom certificate store, make sure it's up to date

**Error: hostname mismatch**
Certificate was issued for api.acme.com but you're calling www.api.acme.com

Don't add www. Just use api.acme.com

**Self-Signed Certificates (Development)**
For local development only:
```python
import requests
# Disable verification (NEVER DO THIS IN PRODUCTION!)
response = requests.get(url, verify=False)
```

Better approach: Add your self-signed cert to trusted store.

## SECTION 10: MEMORY LEAKS & PERFORMANCE

(From incident report after our server crashed during Super Bowl Sunday 2024)

### Symptoms
- Memory usage grows over time
- Application slows down after running for hours
- Eventually crashes with OutOfMemoryError
- Pod restarts frequently in Kubernetes

### Common Causes in Our Platform

**1. Unclosed Database Connections**
Already covered in Database section.

**2. Large Response Caching**
Don't cache entire API responses if they're large:
```python
# BAD: Caches 10MB response
@lru_cache(maxsize=1000)
def get_all_transactions():
    return fetch_transactions()  # Returns 100K records

# GOOD: Cache only IDs, fetch details when needed
@lru_cache(maxsize=1000)
def get_transaction_ids():
    return fetch_transaction_ids()  # Returns list of IDs
```

**3. Circular References in Objects**
Python garbage collector usually handles this, but not always:
```python
# Can cause memory issues
class Node:
    def __init__(self):
        self.children = []
        self.parent = None

# Better with weak references
import weakref

class Node:
    def __init__(self):
        self.children = []
        self._parent = None
    
    @property
    def parent(self):
        return self._parent() if self._parent else None
    
    @parent.setter  
    def parent(self, value):
        self._parent = weakref.ref(value) if value else None
```

**4. Logging Too Much**
Seen customers logging entire request/response bodies. On high-traffic endpoints, this fills memory fast.
```python
# BAD: Logs 1MB response body for every request
logger.info(f"Response: {response.json()}")

# GOOD: Log only what matters
logger.info(f"Response status: {response.status_code}")
```

### Debugging Memory Leaks

**Python:**
```python
import tracemalloc

tracemalloc.start()
# Run your code
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

for stat in top_stats[:10]:
    print(stat)
```

**Node.js:**
```bash
node --inspect app.js
# Open chrome://inspect in Chrome
# Take heap snapshot
```

### Prevention
- Set memory limits in Docker/Kubernetes
- Implement health checks that restart unhealthy pods
- Monitor memory usage (Prometheus + Grafana)
- Periodic restarts (every 12-24 hours) as band-aid solution

## SECTION 11: API VERSIONING & MIGRATION

### Current Status
- v1: Shut down December 2023 (RIP)
- v2: Current, stable
- v3: Beta (don't use in production yet)

### Breaking Changes from v1 to v2

**Authentication** (covered earlier)
v1: X-API-Key header
v2: Authorization: Bearer header

**Date Formats**
v1: Unix timestamps
v2: ISO 8601 strings
```python
# v1
{"created_at": 1709856000}

# v2
{"created_at": "2024-03-08T00:00:00Z"}
```

**Error Response Structure**
v1: Simple string
```json
{"error": "Invalid input"}
```

v2: Structured object
```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "Invalid input",
    "details": {
      "field": "email",
      "issue": "Invalid email format"
    }
  }
}
```

**Pagination**
v1: page/per_page parameters
v2: cursor-based pagination
```python
# v1
GET /payments?page=2&per_page=50

# v2  
GET /payments?cursor=abc123&limit=50
```

### Migration Timeline
- December 2023: v1 shut down
- January 2024: v2 became mandatory
- Customers who didn't migrate: Their apps broke (we sent 50 emails warning them)

We offered free migration help. 90% of customers ignored it until the last day. Chaos ensued.

### What's Coming in v3 (Beta)
- GraphQL support
- Webhooks 2.0 (better retry logic)
- Expanded currency support (100+ currencies)
- Real-time payment status via WebSockets

Don't use v3 yet. It's beta. Things will break.

## SECTION 12: DOCKER & KUBERNETES DEPLOYMENT

(Internal notes from DevOps team - partially relevant to customers doing self-hosted deployments)

### Container Issues

**Pods Restarting Constantly**
Check logs first:
```bash
kubectl logs <pod-name>
kubectl describe pod <pod-name>
```

Common causes:
- App crashes on startup (check application logs)
- Health check failing (usually /health endpoint returns non-200)
- OOMKilled (out of memory - increase memory limit)
- Can't bind to port (port already in use)

**Health Check Config**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30  # Wait 30s before first check
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3  # Restart after 3 failures
  
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 5
```

**Resource Limits**
Set appropriate limits:
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "500m"
```

If pod gets OOMKilled, increase memory limit.

**Image Pull Errors**
- Check image tag exists
- Verify registry credentials
- Check network connectivity to registry

### Environment Variables
Common mistake: Forgetting to set environment variables in deployment:
```yaml
env:
  - name: DATABASE_URL
    value: "postgresql://..."
  - name: API_KEY
    valueFrom:
      secretKeyRef:
        name: api-secrets
        key: key
```

## SECTION 13: MONITORING & ALERTS

(What we tell enterprise customers to set up)

### Key Metrics to Monitor

**API Response Time**
- p50: <100ms
- p95: <500ms  
- p99: <1000ms

If p95 goes above 500ms, something's wrong.

**Error Rate**
- 4xx errors: <5% of requests
- 5xx errors: <0.1% of requests

Sudden spike in errors = incident.

**Database Connections**
- Active connections / Max connections should stay under 80%
- Connection wait time should be <10ms

If connection pool is >80% full, scale up or optimize queries.

**Memory Usage**
- Should stay relatively stable
- Growing memory = memory leak
- Sudden spike = traffic surge or large query result

**Request Rate**
Monitor requests per second:
- Normal: 100-500 req/s
- High traffic: 1000-2000 req/s
- Unusual spike: >3000 req/s (might be DDoS)

### Alerts We Recommend

**Critical (Wake someone up at 3 AM):**
- API error rate >5%
- All pods down
- Database unreachable
- Payment processing failure rate >1%

**Warning (Can wait until morning):**
- API response time p95 >1s
- Memory usage >80%
- Disk space >85%
- Certificate expiring in <7 days

### Tools
We use:
- Prometheus for metrics
- Grafana for dashboards
- PagerDuty for alerts
- Sentry for error tracking

Customers can use whatever they want. Just monitor *something*.

## SECTION 14: COMMON SUPPORT SCENARIOS

These are conversations we have daily:

**Scenario: Customer Getting 401 Errors**
Customer: "I'm getting 401 errors!"
Us: "Can you share your code?"
Customer: *shares code with X-API-Key header*
Us: "You're using the old authentication format. Switch to Bearer tokens."
Customer: "Oh."

Happens at least 5 times per day.

**Scenario: "Your Rate Limits Are Too Low"**
Customer: "I need to make 10,000 requests per minute but you only allow 300!"
Us: "Are you caching responses?"
Customer: "No."
Us: "There's your problem. You're requesting the same data over and over."
Customer: "Can you just increase my limit?"
Us: "Upgrade to Enterprise or implement caching."

(They implement caching and realize they only need 50 requests per minute)

**Scenario: Payment Timeouts**
Customer: "Payments timing out during our flash sale!"
Us: "How many concurrent payments?"
Customer: "About 2000 per second."
Us: "That's your problem. Use async processing."
Customer: "But I need instant confirmation!"
Us: "You can't have instant AND reliable at that scale. Pick one."

(They pick reliable and implement webhooks)

**Scenario: "It Works in Sandbox But Not Production"**
Customer: "Works perfectly in sandbox but fails in production!"
Us: "Are you using test API keys?"
Customer: "Yes."
Us: "There's your problem. Test keys don't work in production."
Customer: "That's stupid."
Us: "It's a security feature."

**Scenario: Certificate Errors**
Customer: "Getting SSL errors!"
Us: "What's the exact error message?"
Customer: "I don't know, it just doesn't work."
Us: "Please send the error message."
Customer: *sends screenshot of generic error*
Us: "Check your system time."
Customer: "My system time was wrong. It works now."

This is more common than you'd think.

## SECTION 15: KNOWN ISSUES & WORKAROUNDS

Things we haven't fixed yet (engineering backlog):

**Issue #1: Webhook Delivery During Outages**
If our webhook delivery service is down, webhooks queue up. When it comes back up, they all fire at once. This can overwhelm your endpoint.

Workaround: Implement rate limiting on your webhook endpoint.

**Issue #2: Dashboard Lag**
Dashboard can be slow during peak hours. We're working on it.

Workaround: Use API for real-time data instead of dashboard.

**Issue #3: Test Environment Data Persistence**
Test environment data gets wiped every 30 days.

Workaround: Don't rely on test data persisting long-term.

**Issue #4: Partial Refunds**
Partial refunds sometimes show wrong amount in dashboard (but correct amount is refunded).

Workaround: Use API to verify refund amounts.

**Issue #5: Currency Conversion**
Currency conversion rates update daily, but our documentation says they update hourly (oops).

Workaround: Don't rely on exact conversion rates for critical calculations.

## SECTION 16: TROUBLESHOOTING CHECKLIST

When something doesn't work, go through this:

**Authentication Issues:**
1. [ ] Using correct API key format? (Bearer sk-live-xxx)
2. [ ] Key is for correct environment? (test vs prod)
3. [ ] Authorization header included?
4. [ ] No extra whitespace in key?
5. [ ] Account not suspended?

**Network Issues:**
1. [ ] Can you ping api.acme.com?
2. [ ] Firewall blocking outbound HTTPS?
3. [ ] Using correct base URL?
4. [ ] SSL certificate valid on your end?

**Rate Limit Issues:**
1. [ ] Check X-RateLimit-Remaining header
2. [ ] Implementing backoff?
3. [ ] Caching responses?
4. [ ] Upgrade plan if needed

**Payment Issues:**
1. [ ] Using correct endpoint? (POST /v2/payments/charge)
2. [ ] Amount format correct? (integer cents, not decimal dollars)
3. [ ] Currency code valid? (USD, EUR, etc.)
4. [ ] Idempotency key provided?
5. [ ] Card details valid?

**Performance Issues:**
1. [ ] Response time acceptable for your requests?
2. [ ] Database queries optimized?
3. [ ] Caching implemented?
4. [ ] Connection pooling configured?
5. [ ] Monitoring in place?

## SECTION 17: EMERGENCY CONTACTS

**Support:**
- Email: support@acme.com (24 hour response time)
- Enterprise: Phone support (included in plan)
- Status Page: status.acme.com

**Escalation:**
If something is truly broken and urgent:
1. Open support ticket
2. Mark as "Critical"
3. We'll respond within 1 hour

Don't email the CEO (yes, people do this).

## SECTION 18: RANDOM INTERNAL NOTES
(Not relevant to customers but somehow ended up in this document)

- Mike's extension: 4502
- Sarah on vacation until March 15
- Don't deploy on Fridays (we learned this the hard way)
- Coffee machine broken again (third time this month)
- New intern starts Monday, needs onboarding
- Q2 roadmap: GraphQL, WebSocket support, better docs
- Tech debt backlog: 237 issues (sigh)

## APPENDIX: CURL EXAMPLES

For people who learn better with examples:

**Authentication:**
```bash
curl https://api.acme.com/v2/account \
  -H "Authorization: Bearer sk-live-abc123..."
```

**Create Payment:**
```bash
curl -X POST https://api.acme.com/v2/payments/charge \
  -H "Authorization: Bearer sk-live-abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 5000,
    "currency": "USD",
    "description": "Test payment"
  }'
```

**With Idempotency:**
```bash
curl -X POST https://api.acme.com/v2/payments/charge \
  -H "Authorization: Bearer sk-live-abc123..." \
  -H "Idempotency-Key: order-12345-1709856000" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 5000,
    "currency": "USD"
  }'
```

**List Payments (Pagination):**
```bash
curl https://api.acme.com/v2/payments?limit=50&cursor=abc123 \
  -H "Authorization: Bearer sk-live-abc123..."
```

---

END OF COMPANY HANDBOOK

Last updated: March 2024 (various sections at different times)
Contributors: Mike, Sarah, John, DevOps Team, Support Team

If you find errors or outdated info, please create a ticket. We'll fix it... eventually.
"""

# Save document 1
with open('/home/claude/documents/company_handbook.md', 'w') as f:
    f.write(doc1)

print("Document 1 created: company_handbook.md (8500+ words)")