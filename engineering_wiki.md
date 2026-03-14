# ACME TECH ENGINEERING WIKI
Internal Documentation - Last updated by multiple contributors
WARNING: Some sections outdated. Check timestamps.

---

## AUTHENTICATION SYSTEM ARCHITECTURE
Author: John (2022) | Updated by: Sarah (2023) | Last update by: Mike (2024)

### Historical Evolution

**Phase 1: Simple API Keys (2019-2022)**
Original implementation used basic string keys:
- Format: `acme_[random_alphanumeric]`
- Stored in plaintext in database (yikes!)
- No expiration
- No rotation capability

This was fine when we had 50 customers. At 5000 customers, security audit said "absolutely not."

**Phase 2: JWT Tokens (2022-2023)**
Migrated to JWT:
```python
payload = {
    'user_id': user.id,
    'exp': datetime.utcnow() + timedelta(hours=24)
}
token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
```

Problems we hit:
- Token expiry caused confusion (customers forgot to refresh)
- We got 500+ support tickets about "token expired" errors
- JWT decode overhead (every request decodes + validates)
- Secret key rotation nightmare

After 8 months, we gave up on JWT.

**Phase 3: Bearer Tokens (2023-present)**
Current system:
- Format: `sk-{environment}-{48_random_chars}`
- Environment: 'test' or 'live'
- Never expires (unless manually revoked)
- Stored hashed in database (bcrypt)
- Rate limited per key

Example:
```
Test: sk-test-abc123def456ghi789jkl012mno345pqr678stu901
Live: sk-live-xyz987wvu654tsr321qpo098nml876kji654hgf321
```

### Current Implementation

**Key Generation:**
```python
import secrets
import bcrypt

def generate_api_key(environment='live'):
    random_part = secrets.token_urlsafe(36)[:48]
    key = f"sk-{environment}-{random_part}"
    
    # Hash for storage
    hashed = bcrypt.hashpw(key.encode(), bcrypt.gensalt())
    
    # Store in database
    db.execute(
        "INSERT INTO api_keys (user_id, key_hash, environment, created_at) VALUES (?, ?, ?, ?)",
        (user_id, hashed, environment, datetime.now())
    )
    
    return key  # Show once, never again
```

**Validation (every request):**
```python
def validate_api_key(key):
    # Extract environment
    if key.startswith('sk-test-'):
        environment = 'test'
    elif key.startswith('sk-live-'):
        environment = 'live'
    else:
        return False
    
    # Check if request is to correct environment
    if environment == 'test' and request.host != 'sandbox.acme.com':
        return False
    if environment == 'live' and request.host != 'api.acme.com':
        return False
    
    # Fetch all active keys (we hash, so can't look up directly)
    active_keys = db.execute("SELECT key_hash FROM api_keys WHERE revoked = FALSE")
    
    for stored_hash in active_keys:
        if bcrypt.checkpw(key.encode(), stored_hash):
            return True
    
    return False
```

NOTE (Mike, 2024): This validation is slow when user has many keys. TODO: Add caching layer.

### Known Issues

**Issue #1: Validation Performance**
When user has 10+ API keys, validation takes 200-500ms (bcrypt is intentionally slow).

Workaround: Cache validation results in Redis (TTL: 5 minutes)

**Issue #2: No Key Rotation**
Keys never expire. If compromised, must manually revoke.

TODO: Add automatic rotation with 90-day expiry (Q2 2024 roadmap)

**Issue #3: GitHub Scanning**
We scan GitHub for leaked keys and auto-revoke. But only checks public repos.

If customer commits key to private repo then makes repo public, we don't catch it immediately.

---

## PAYMENT PROCESSING ARCHITECTURE
Author: Sarah (2023) | Updated during Black Friday incident (2023)

### System Overview

```
Customer Request
      ↓
Load Balancer (HAProxy)
      ↓
Payment Service (50 pods in K8s)
      ↓
Message Queue (RabbitMQ)
      ↓
Worker Pool (100 workers)
      ↓
Payment Processor (Stripe)
      ↓
Database (PostgreSQL - write to primary, read from replicas)
```

### Database Schema

**payments table:**
```sql
CREATE TABLE payments (
    id UUID PRIMARY KEY,
    customer_id VARCHAR(255) NOT NULL,
    amount INTEGER NOT NULL,  -- Cents
    currency VARCHAR(3) NOT NULL,
    status VARCHAR(20) NOT NULL,  -- pending, processing, succeeded, failed
    processor_id VARCHAR(255),  -- Stripe charge ID
    idempotency_key VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_payments_customer ON payments(customer_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_created ON payments(created_at DESC);
CREATE INDEX idx_payments_idempotency ON payments(idempotency_key) WHERE idempotency_key IS NOT NULL;
```

### The Black Friday Incident (Nov 24, 2023)

**Timeline:**

**8:00 AM**: Traffic starts increasing (Black Friday sale begins)
**8:15 AM**: Response times increase from 200ms → 2s
**8:30 AM**: Database connection pool exhausted
**8:35 AM**: 504 errors at 60% of requests
**8:40 AM**: Enterprise customer (linda@ecommerce-pro.com) opens critical ticket
**8:45 AM**: On-call engineer (me) woken up
**8:50 AM**: Emergency scale up: 10 pods → 50 pods
**9:00 AM**: Still seeing issues - connection pool problem
**9:05 AM**: Increase DB pool: 100 → 500 connections
**9:15 AM**: Error rate drops to 20%
**9:20 AM**: Identify slow query blocking connections
**9:25 AM**: Add index to speed up query
**9:30 AM**: Error rate < 2%
**9:45 AM**: Declare incident resolved
**10:00 AM**: Post-mortem meeting

**Root Causes:**
1. Payment service scaled, but database didn't scale with it
2. Connection pool too small for burst traffic
3. Slow query (missing index) holding connections longer
4. No circuit breaker (kept hammering failing DB)

**Fixes Implemented:**
1. Auto-scaling for payment service (based on queue depth)
2. Larger default connection pool (500 instead of 100)
3. Added monitoring for connection pool usage
4. Implemented circuit breaker pattern
5. Added read replicas for reports/analytics (reduce primary DB load)

**Lessons Learned:**
- Test at scale before major sales events
- Monitor connection pool usage
- Have runbooks for common incident types
- Keep DBA's phone number handy

### Current Bottlenecks

**Problem:** Synchronous Stripe API calls
When we make synchronous calls to Stripe's API, we wait 2-5 seconds for response. During this time, we hold database connection + worker thread.

At 1000 concurrent payments, this means 1000 connections tied up.

**Solution (not yet implemented):**
Move to fully async processing:
1. Accept payment request → Return 202 Accepted immediately
2. Queue payment processing
3. Process in background
4. Webhook notifies customer when complete

This would reduce response time from 3s → 100ms and eliminate connection pool issues.

**Why not implemented?** Backwards compatibility. Existing customers expect synchronous response.

**Plan:** Offer both sync and async APIs. Default new customers to async.

---

## DATABASE ARCHITECTURE
Author: Mike (2024) | After 3 AM outage incident

### Current Setup

**Primary Database:**
- Server: db-cluster-prod-01.aws.internal
- Type: PostgreSQL 15.2
- Size: r6g.2xlarge (8 vCPU, 64 GB RAM)
- Storage: 2 TB SSD
- Max connections: 500

**Read Replicas (3):**
- db-replica-01, 02, 03
- Same specs as primary
- Lag: <100ms typically
- Used for: Reports, analytics, read-heavy queries

**Backup:**
- Daily full backup (3 AM UTC)
- Point-in-time recovery (PITR) enabled
- Retention: 30 days
- Backup stored in S3 (cross-region replication)

### Connection Pooling

**Application side (PgBouncer):**
```
[databases]
acme_prod = host=db-cluster-prod-01.aws.internal port=5432 dbname=acme

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = md5
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
reserve_pool_size = 10
reserve_pool_timeout = 5
```

This allows 1000 app connections pooled into 25 DB connections.

**Python connection pool:**
```python
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql://user:pass@pgbouncer:6432/acme",
    pool_size=30,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True  # Verify connection before use
)
```

### The 3 AM Outage (Feb 28, 2024)

**What happened:**
Scheduled backup started at 3 AM. Backup process locked tables. All writes blocked for 45 minutes.

**Why so long?**
Backup tried to backup a 500 GB table that we don't even need anymore (old analytics data from 2019).

**Fix:**
1. Deleted old analytics table (freed 500 GB)
2. Changed backup strategy (use pg_dump with --exclude-table)
3. Moved backup window to 4 AM (less traffic)

**Lesson:** Clean up old data regularly. Don't backup tables you don't need.

### Query Performance

**Slow Query Log (top offenders):**

**Query #1: Customer payment history**
```sql
SELECT * FROM payments WHERE customer_id = ? ORDER BY created_at DESC LIMIT 50
```
**Problem:** SELECT * pulls entire row (including large metadata JSON)
**Fix:** SELECT only needed columns
**Time:** 2.3s → 145ms

**Query #2: Daily revenue report**
```sql
SELECT SUM(amount) FROM payments WHERE created_at::date = CURRENT_DATE AND status = 'succeeded'
```
**Problem:** ::date cast prevents index usage
**Fix:** Use range query instead
```sql
SELECT SUM(amount) FROM payments 
WHERE created_at >= CURRENT_DATE 
AND created_at < CURRENT_DATE + interval '1 day'
AND status = 'succeeded'
```
**Time:** 5.1s → 80ms

**Query #3: Search by transaction ID**
```sql
SELECT * FROM payments WHERE processor_id = ?
```
**Problem:** No index on processor_id
**Fix:** `CREATE INDEX idx_payments_processor ON payments(processor_id)`
**Time:** 3.8s → 12ms

### Deadlock Issues

We occasionally see deadlocks on payments table:

```
ERROR: deadlock detected
DETAIL: Process 4512 waits for ShareLock on transaction 8934
Process 8934 waits for ShareLock on transaction 4512
```

**Cause:** Multiple workers trying to update same customer's payments in different orders.

**Temporary fix:** Retry transaction with exponential backoff

**Real fix (TODO):** Use `SELECT FOR UPDATE SKIP LOCKED` for payment queue processing

---

## RATE LIMITING IMPLEMENTATION
Author: John (2022) | Updated by: Mike (2023)

### Algorithm

We use token bucket algorithm:

```python
import redis
import time

redis_client = redis.Redis(host='redis-cache')

def rate_limit(api_key, limit=60, window=60):
    """
    limit: number of requests allowed
    window: time window in seconds
    """
    current_time = int(time.time())
    window_start = current_time - window
    
    key = f"rate_limit:{api_key}"
    
    # Remove old entries outside window
    redis_client.zremrangebyscore(key, 0, window_start)
    
    # Count requests in current window
    current_requests = redis_client.zcard(key)
    
    if current_requests >= limit:
        return False  # Rate limited
    
    # Add current request
    redis_client.zadd(key, {current_time: current_time})
    redis_client.expire(key, window)
    
    return True  # Allowed
```

### Rate Limit Tiers

**Free Tier:**
- 60 requests/minute
- 10,000 requests/day
- Burst: 100 requests in 10 seconds

**Pro Tier:**
- 300 requests/minute
- 100,000 requests/day
- Burst: 500 requests in 10 seconds

**Enterprise:**
- Custom (usually 1000-5000 per minute)
- Unlimited daily
- Dedicated Redis instance

### Headers

Every response includes:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1709856543
```

**Implementation:**
```python
@app.after_request
def add_rate_limit_headers(response):
    if hasattr(request, 'api_key'):
        limit = get_user_limit(request.api_key)
        remaining = get_remaining_requests(request.api_key)
        reset_time = get_reset_time(request.api_key)
        
        response.headers['X-RateLimit-Limit'] = str(limit)
        response.headers['X-RateLimit-Remaining'] = str(remaining)
        response.headers['X-RateLimit-Reset'] = str(reset_time)
    
    return response
```

### Known Issues

**Issue #1: Distributed Rate Limiting**
With 50 payment service pods, rate limit is per-pod, not global.

If user sends 10 req/s to each pod, they get 500 req/s total (bypassing 300/min limit).

**Workaround:** Use Redis as central rate limit store (not per-pod memory)

**Status:** Implemented in v2.4 (Jan 2024)

**Issue #2: Burst Allowance Not Enforced**
Documentation says burst is allowed, but code doesn't actually implement it.

**Status:** TODO (low priority)

---

## WEBHOOK DELIVERY SYSTEM
Author: Sarah (2023)

### Architecture

```
Event occurs (payment succeeded, etc.)
      ↓
Published to RabbitMQ (webhooks queue)
      ↓
Webhook Worker picks up event
      ↓
POST to customer webhook URL
      ↓
Response received?
  ├─ 200 OK → Mark delivered
  └─ Error → Retry logic
```

### Retry Logic

**Retry Schedule:**
1. Immediate
2. 5 minutes
3. 30 minutes
4. 2 hours
5. 6 hours

After 5 failed attempts, we give up and mark as permanently failed.

**Exponential backoff:**
```python
def get_retry_delay(attempt):
    delays = [0, 300, 1800, 7200, 21600]  # seconds
    return delays[attempt] if attempt < len(delays) else None
```

### Signature Verification

Every webhook includes signature:
```
X-Webhook-Signature: t=1709856000,v1=abc123def456...
```

**Generation:**
```python
import hmac
import hashlib
import time

def generate_signature(payload, secret):
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload}"
    
    signature = hmac.new(
        secret.encode(),
        signed_payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return f"t={timestamp},v1={signature}"
```

**Customer should verify:**
```python
def verify_signature(payload, signature_header, secret):
    parts = dict(p.split('=') for p in signature_header.split(','))
    timestamp = int(parts['t'])
    received_sig = parts['v1']
    
    # Reject if timestamp too old (>5 minutes)
    if abs(time.time() - timestamp) > 300:
        return False
    
    # Compute expected signature
    signed_payload = f"{timestamp}.{payload}"
    expected_sig = hmac.new(
        secret.encode(),
        signed_payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Compare securely
    return hmac.compare_digest(received_sig, expected_sig)
```

### Webhook Events

**Payment Events:**
- `payment.created`
- `payment.succeeded`
- `payment.failed`
- `payment.refunded`

**Subscription Events:**
- `subscription.created`
- `subscription.renewed`
- `subscription.canceled`
- `subscription.trial_ending`

**Account Events:**
- `account.updated`
- `account.suspended` (hope customers never get this)

### Delivery Stats (Feb 2024)

- Total webhook deliveries: 5.2 million
- Success rate (first attempt): 87%
- Success rate (after retries): 96%
- Permanently failed: 4%

**Common failure reasons:**
- Endpoint returns 500 error: 45%
- Timeout (>10s): 30%
- DNS resolution failure: 15%
- SSL certificate error: 7%
- Other: 3%

---

## MONITORING & ALERTING
Author: Mike (2024)

### Metrics We Track

**Application Metrics (Prometheus):**
- Request rate (req/s)
- Response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- Active connections
- Queue depth

**Database Metrics:**
- Connection pool usage
- Query execution time
- Slow query count
- Deadlock count
- Replication lag

**Infrastructure Metrics:**
- CPU usage
- Memory usage
- Disk I/O
- Network throughput

### Grafana Dashboards

**Main Dashboard:**
- Request rate graph (last 24h)
- Error rate (target: <1%)
- Response time (p95 target: <500ms)
- Database connection pool
- Active payments processing

**Payment Dashboard:**
- Payments per minute
- Success rate
- Average payment amount
- Top customers by volume
- Processor (Stripe) response time

**Alert Dashboard:**
- Active alerts
- Alert history
- Mean time to resolve (MTTR)
- On-call rotation

### Alert Rules

**Critical (PagerDuty):**
```yaml
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
  for: 5m
  annotations:
    summary: "Error rate >5% for 5 minutes"
    
- alert: DatabaseDown
  expr: up{job="postgresql"} == 0
  for: 1m
  annotations:
    summary: "Database is down!"
    
- alert: HighPaymentFailureRate
  expr: rate(payments_failed[10m]) > 0.10
  for: 5m
  annotations:
    summary: "Payment failure rate >10%"
```

**Warning (Slack):**
```yaml
- alert: SlowResponseTime
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1.0
  for: 10m
  annotations:
    summary: "p95 response time >1s"
    
- alert: HighMemoryUsage
  expr: (node_memory_MemTotal - node_memory_MemAvailable) / node_memory_MemTotal > 0.85
  for: 15m
  annotations:
    summary: "Memory usage >85%"
```

### On-Call Rotation

**Week 1-2:** Mike
**Week 3-4:** Sarah
**Week 5-6:** Tom

**On-call responsibilities:**
- Respond to PagerDuty alerts within 15 minutes
- Investigate and resolve critical issues
- Document incidents in wiki
- Hand off to next person on Monday morning

**Escalation:**
If on-call engineer can't resolve within 1 hour, escalate to:
1. Senior engineer (John)
2. CTO (if John unavailable)
3. CEO (if truly catastrophic)

(We've never had to call the CEO. Yet.)

---

## INFRASTRUCTURE & DEPLOYMENT
Author: Tom (DevOps, 2024)

### AWS Architecture

**Regions:**
- Primary: us-east-1
- DR (Disaster Recovery): us-west-2

**Services:**
- EKS (Kubernetes) - Application hosting
- RDS (PostgreSQL) - Database
- ElastiCache (Redis) - Caching & rate limiting
- S3 - Backups & static assets
- CloudFront - CDN
- Route53 - DNS
- ACM - SSL certificates

### Kubernetes Setup

**Namespaces:**
- `production` - Production services
- `staging` - Staging environment
- `monitoring` - Prometheus, Grafana

**Production Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
  namespace: production
spec:
  replicas: 50
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 10
      maxUnavailable: 5
  template:
    spec:
      containers:
      - name: payment-service
        image: acme/payment-service:v2.7.3
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
```

### Deployment Process

**CI/CD Pipeline (GitHub Actions):**

1. **Code pushed to main branch**
2. **Run tests:**
   - Unit tests
   - Integration tests
   - Linting
3. **Build Docker image:**
   - Tag with git commit SHA
   - Push to ECR
4. **Deploy to staging:**
   - Update K8s deployment
   - Wait for health checks
   - Run smoke tests
5. **Deploy to production:**
   - Requires manual approval
   - Rolling update (10 pods at a time)
   - Monitor error rates
   - Auto-rollback if error rate >5%

**Manual Deployment:**
```bash
# Build
docker build -t acme/payment-service:v2.7.4 .

# Push
docker push acme/payment-service:v2.7.4

# Deploy
kubectl set image deployment/payment-service payment-service=acme/payment-service:v2.7.4 -n production

# Watch rollout
kubectl rollout status deployment/payment-service -n production

# Rollback if needed
kubectl rollout undo deployment/payment-service -n production
```

### Disaster Recovery Plan

**RTO (Recovery Time Objective):** 1 hour
**RPO (Recovery Point Objective):** 15 minutes

**DR Steps:**
1. Switch DNS from us-east-1 to us-west-2 (Route53)
2. Promote read replica to primary in us-west-2
3. Scale up K8s cluster in us-west-2
4. Deploy latest Docker images
5. Verify all services healthy
6. Announce on status page

**Last DR drill:** February 1, 2024
**Result:** Completed in 52 minutes (within RTO)
**Issues found:** Redis cache not replicating properly (fixed)

---

## SECURITY INCIDENTS & POSTMORTEMS
Author: Various

### Incident #1: GitHub Key Leak (March 2023)

**What happened:**
Customer committed their production API key to public GitHub repo. Within 2 hours, attacker found it and made 50,000 API calls.

**Timeline:**
- 10:23 AM: Key committed to GitHub
- 12:15 PM: Our GitHub scanner detected it
- 12:16 PM: Auto-revoked key
- 12:17 PM: Emailed customer
- 12:45 PM: Customer responded, generated new key

**Damage:**
- 50,000 API calls (mostly payment attempts)
- $2,300 in fraudulent charges (all refunded)
- Customer downtime: 30 minutes

**Lessons:**
- GitHub scanning works!
- Need faster notification (email delayed by 30 minutes)
- Consider SMS/phone call for critical security issues

**Actions taken:**
1. Added SMS notification for key leaks
2. Improved email deliverability
3. Added warning in dashboard when generating keys

### Incident #2: DDoS Attack (June 2023)

**What happened:**
Coordinated DDoS attack on our API. 500,000 req/s from botnet.

**Timeline:**
- 3:42 PM: Attack begins
- 3:44 PM: CloudFront rate limiting triggers
- 3:47 PM: Enable CloudFront AWS Shield
- 3:52 PM: Attack blocked
- 4:15 PM: Attack stops

**Impact:**
- Minimal - CloudFront absorbed most traffic
- Slight slowdown for legitimate users (500ms → 800ms)
- No downtime

**Cost:**
- AWS Shield: $3,000/month
- CloudFront overage: $12,000 for that day

**Decision:**
Keep AWS Shield enabled permanently. Worth the cost.

### Incident #3: Database Connection Leak (August 2023)

**What happened:**
Bug in payment service caused connection leaks. Over 3 hours, all 500 connections were exhausted.

**Timeline:**
- 2:15 PM: Deploy v2.3.1 (introduced bug)
- 2:30 PM: Connection count starts increasing
- 4:45 PM: Connection pool exhausted
- 4:47 PM: All API requests start failing
- 4:52 PM: On-call engineer (Sarah) alerted
- 5:05 PM: Identified issue (connection leak)
- 5:10 PM: Rollback to v2.3.0
- 5:20 PM: Connection pool recovered
- 5:30 PM: All services normal

**Root cause:**
```python
# Bug introduced in v2.3.1
def process_payment(payment_id):
    conn = db.connect()
    result = conn.execute(f"SELECT * FROM payments WHERE id = {payment_id}")
    return result  # BUG: Connection never closed!

# Fixed in v2.3.2
def process_payment(payment_id):
    with db.connect() as conn:  # Auto-closes
        result = conn.execute(f"SELECT * FROM payments WHERE id = {payment_id}")
        return result.fetchone()
```

**Impact:**
- 38 minutes of complete API outage
- ~5000 failed payment attempts
- Enterprise customers VERY unhappy

**Actions taken:**
1. Added code review checklist (check for connection leaks)
2. Added connection pool monitoring
3. Implemented automatic rollback on high error rate
4. Apologized profusely to customers

**Lesson:**
ALWAYS use context managers for database connections!

---

## RANDOM INTERNAL NOTES & TODO

**TODO List (Incomplete, Forever):**
- [ ] Implement key rotation (90 days)
- [ ] Add GraphQL API (v3 beta)
- [ ] Migrate to Rust for payment service (performance)
- [ ] Better documentation (customers keep asking same questions)
- [ ] Hire more DevOps engineers (Tom is drowning)
- [ ] Fix webhook burst issue
- [ ] Add more currencies (100+ requested)
- [ ] Implement WebSocket for real-time updates
- [ ] Refactor authentication service (spaghetti code)
- [ ] Clean up old data (500 GB of 2019 logs)

**Team Contacts:**
- Mike: mike@acme.com, ext 4502, Slack: @mike
- Sarah: sarah@acme.com, ext 4503, Slack: @sarah
- Tom: tom@acme.com, ext 4504, Slack: @tom (DevOps)
- John: john@acme.com, ext 4501, Slack: @john (CTO)

**Random Notes:**
- Don't deploy on Fridays (we learned this the hard way)
- Coffee machine broken (again)
- New intern starts Monday (needs laptop setup)
- Company offsite next month (Vegas!)
- Q2 goals: 99.9% uptime, <200ms response time
- Technical debt backlog: 237 issues (someone should look at that...)

**Meeting Notes (Feb 15, 2024):**
- Discussed moving to microservices (decided against - not worth complexity)
- Need to hire 2 more backend engineers
- Marketing wants API for analytics data (low priority)
- Enterprise customer wants on-premise deployment (told them no)

**Incident Response Runbook:**
1. Check status page: status.acme.com
2. Check Grafana dashboards
3. Check CloudWatch logs
4. SSH into production pods (if needed)
5. Roll back recent deploys (if suspicious)
6. Scale up if capacity issue
7. Contact Stripe/AWS if third-party issue
8. Update status page every 30 minutes
9. Post-mortem within 24 hours

**Useful Commands:**
```bash
# Check pod status
kubectl get pods -n production

# View logs
kubectl logs -f deployment/payment-service -n production

# Scale up
kubectl scale deployment/payment-service --replicas=100 -n production

# Rollback
kubectl rollout undo deployment/payment-service -n production

# Connect to database
psql -h db-cluster-prod-01.aws.internal -U admin -d acme

# Check Redis
redis-cli -h redis-cache.aws.internal
```

---

**END OF ENGINEERING WIKI**

Last updated: March 8, 2024 (multiple sections at different times)

If you're reading this and something is outdated, please update it! Or at least leave a comment.

Remember: Document your changes. Future you (and your teammates) will thank you.
