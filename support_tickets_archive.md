# ACME TECH - SUPPORT TICKETS ARCHIVE 2023-2024
Internal Use Only - Customer Support History
Total Tickets: 847 | Resolved: 701 | Pending: 89 | Closed-Won't Fix: 57

---

## TICKET #1847 - December 15, 2023
**Customer:** james@startup.com (Free Tier)
**Subject:** Getting random 401 errors
**Status:** RESOLVED
**Priority:** Medium
**Tags:** authentication, api-error

**Initial Message (Dec 15, 10:23 AM):**
Hey, I'm getting 401 errors randomly when calling your API. Sometimes it works, sometimes it doesn't. Very frustrating! This is blocking our production launch.

My code:
```python
import requests
url = "https://api.acme.com/v2/payments"
headers = {"X-API-Key": "acme_test_abc123xyz"}
response = requests.get(url, headers=headers)
```

What's going on???

**Support Agent (Sarah, Dec 15, 10:45 AM):**
Hi James,

Thanks for reaching out! I see a few issues here:

1. You're using the old authentication format (X-API-Key). We deprecated this in March 2023. You need to use Bearer tokens now.
2. You're using a test key (acme_test_xxx). Test keys only work on sandbox.acme.com, not production.
3. The header format should be: `Authorization: Bearer sk-live-YOUR_KEY`

Can you try updating your code and let me know if it works?

**Customer (Dec 15, 11:02 AM):**
Oh wow, I didn't know about the auth change. Where is this documented?

**Support Agent (Sarah, Dec 15, 11:15 AM):**
It's in our migration guide here: https://docs.acme.com/migration-v2
We also sent 5 emails about this between Jan-March 2023.

**Customer (Dec 15, 11:30 AM):**
I probably missed those emails (they might be in spam). Anyway, I updated my code:

```python
headers = {"Authorization": "Bearer sk-live-abc123xyz456"}
response = requests.get(url, headers=headers)
```

Still getting 401!

**Support Agent (Sarah, Dec 15, 2:18 PM):**
Can you send me your full API key? (You can DM it if you don't want to post publicly... wait, this is a ticket not a forum post, never mind)

Actually, don't send the full key. Just send the first 10 characters so I can verify the format.

**Customer (Dec 15, 2:45 PM):**
sk-live-ab

**Support Agent (Sarah, Dec 15, 3:02 PM):**
That looks correct. Let me check our logs...

[Internal note: Checked logs, seeing 401s from this IP. The key exists but account shows "suspended" status. Checking with billing...]

**Support Agent (Sarah, Dec 15, 3:30 PM):**
Hi James,

I found the issue. Your account was suspended due to a failed payment on your credit card. Your free trial ended on Dec 1, and the charge for the Pro plan ($99) failed.

Can you update your payment method in the dashboard? Once that's done, your API key will work again.

**Customer (Dec 15, 4:15 PM):**
OMG I had no idea! I thought I was still on free tier. Updated my card, can you reactivate my account?

**Support Agent (Sarah, Dec 15, 4:20 PM):**
Done! Your account is active now. Please test and confirm it's working.

**Customer (Dec 15, 4:35 PM):**
Working perfectly now! Thanks for the help. Sorry for the confusion.

**Support Agent (Sarah, Dec 15, 4:40 PM):**
No worries! Happy to help. Let us know if you have any other issues.

**Resolution:** Account suspended due to payment failure. Reactivated after customer updated payment method.
**Time to Resolution:** 6 hours 17 minutes

---

## TICKET #2103 - January 3, 2024
**Customer:** linda@ecommerce-pro.com (Enterprise)
**Subject:** Payment endpoint timing out during high traffic
**Status:** RESOLVED
**Priority:** CRITICAL
**Tags:** performance, payment, timeout, 504

**Initial Message (Jan 3, 8:47 AM):**
URGENT: Our payment endpoint is timing out constantly. We're in the middle of our biggest sale of the year (New Year sale) and customers can't check out!

Getting 504 Gateway Timeout errors on POST /v2/payments/charge

This is costing us thousands of dollars per minute. PLEASE HELP IMMEDIATELY!

**Support Agent (Mike, Jan 3, 8:52 AM):**
Hi Linda,

I'm escalating this to our engineering team right now. Can you tell me:
1. What time did this start?
2. How many requests per minute are you making?
3. Are you seeing this on all payment attempts or just some?

**Customer (Jan 3, 8:55 AM):**
Started around 8:00 AM when our sale went live.
Traffic is ~2000 payment requests per minute (way higher than usual, we normally do 200/min).
About 60% of payment attempts are timing out.

**Engineering Team (Tom, Jan 3, 9:10 AM):**
[Internal note: Checked our payment service logs. Database connection pool is completely exhausted. Payment service trying to connect to DB but all 100 connections are in use. Queries are backing up.]

Linda - this is a capacity issue on our end. Your traffic spike is legitimate but our payment service can't handle 2000 concurrent requests. The issue isn't rate limiting, it's our backend struggling under load.

Immediate workaround: Can you implement asynchronous payment processing? Instead of waiting for payment to complete, return immediately and process via webhook?

**Customer (Jan 3, 9:15 AM):**
We can't change our code in the middle of a sale! That would take hours. We need this fixed NOW.

**Engineering Team (Tom, Jan 3, 9:25 AM):**
Understood. We're implementing emergency measures:
1. Scaling payment service from 10 pods to 50 pods (ETA: 5 minutes)
2. Increasing database connection pool from 100 to 500 (ETA: 10 minutes)
3. Adding Redis caching layer for payment status checks (ETA: 15 minutes)

This should handle your traffic.

**Customer (Jan 3, 9:45 AM):**
Timeout rate dropped to 20%. Better but not good enough.

**Engineering Team (Tom, Jan 3, 9:50 AM):**
Increasing to 100 pods now. Also identified a slow query that was blocking connections - optimized it.

**Customer (Jan 3, 10:15 AM):**
Timeout rate now <2%. This is acceptable. Thank you!

**Engineering Team (Tom, Jan 3, 10:20 AM):**
Good to hear. We'll keep the increased capacity running through your sale period. 

For future: I strongly recommend implementing async payment processing. Synchronous payment processing at this scale will always be fragile. We can provide code examples if you'd like.

**Customer (Jan 3, 10:30 AM):**
Yes please send examples. We'll implement this before our next big sale.

**Follow-up (Jan 8):**
Customer implemented async payment processing with webhooks. No issues during subsequent traffic spikes.

**Resolution:** Emergency infrastructure scaling + query optimization. Customer advised to implement async processing for future.
**Cost Impact:** ~$15,000 in lost sales before resolution.
**Time to Resolution:** 1 hour 28 minutes

---

## TICKET #2156 - January 8, 2024
**Customer:** bob@mobile-app.io (Pro)
**Subject:** 404 error on /v2/users endpoint
**Status:** CLOSED - USER ERROR
**Priority:** Low
**Tags:** api-error, 404, documentation

**Initial Message (Jan 8, 2:15 PM):**
Your documentation says there's a /v2/users endpoint but I'm getting 404 Not Found.

```bash
curl https://api.acme.com/v2/users \
  -H "Authorization: Bearer sk-live-xxx"
```

Is this endpoint down?

**Support Agent (Sarah, Jan 8, 2:45 PM):**
Hi Bob,

The endpoint is /v2/user (singular), not /v2/users (plural).

Try:
```bash
curl https://api.acme.com/v2/user \
  -H "Authorization: Bearer sk-live-xxx"
```

**Customer (Jan 8, 3:10 PM):**
But your documentation at https://docs.acme.com/api/users clearly says /v2/users with an 's'!

**Support Agent (Sarah, Jan 8, 3:25 PM):**
Can you send a screenshot? I'm looking at our docs and it shows /v2/user everywhere.

**Customer (Jan 8, 3:40 PM):**
[Attached screenshot showing third-party blog post about ACME API]

**Support Agent (Sarah, Jan 8, 3:50 PM):**
Ah, that's not our official documentation. That's a blog post from 2021 (before we changed the endpoint name).

Our official docs are at: https://docs.acme.com

The correct endpoint is /v2/user (singular).

**Customer (Jan 8, 4:05 PM):**
That's confusing. Can you add a redirect from /v2/users to /v2/user?

**Support Agent (Sarah, Jan 8, 4:20 PM):**
I'll pass this to our engineering team as a feature request, but for now please use /v2/user.

**Customer (Jan 8, 4:25 PM):**
Fine. It works with /v2/user. Thanks.

**Resolution:** User reading outdated third-party documentation. Directed to official docs.
**Feature Request:** Add redirect for common endpoint name variations (Status: Backlog)

---

## TICKET #2234 - January 15, 2024
**Customer:** maria@fintech-startup.com (Pro)
**Subject:** Duplicate transactions being created
**Status:** RESOLVED
**Priority:** High
**Tags:** payment, duplicate, idempotency

**Initial Message (Jan 15, 11:20 AM):**
We're seeing duplicate transactions! When a customer's payment fails and they retry, sometimes they get charged twice.

This is a MAJOR issue - we're having to manually refund duplicate charges.

Example:
- Transaction ID: pay_abc123 - Amount: $50.00 - Status: Failed
- Transaction ID: pay_def456 - Amount: $50.00 - Status: Success

Same customer, same amount, 2 seconds apart. Customer got charged twice.

**Support Agent (Mike, Jan 15, 11:45 AM):**
Hi Maria,

This is typically caused by not using idempotency keys. Are you including an Idempotency-Key header in your payment requests?

```python
headers = {
    "Authorization": "Bearer sk-live-xxx",
    "Idempotency-Key": f"order-{order_id}-{timestamp}"
}
```

If you use the same idempotency key for a retry, we'll return the original transaction result instead of creating a new charge.

**Customer (Jan 15, 12:10 PM):**
No, we're not using idempotency keys. I didn't know this was required!

Where is this documented?

**Support Agent (Mike, Jan 15, 12:30 PM):**
It's in our payment API docs: https://docs.acme.com/api/payments#idempotency

It's not technically required, but it's strongly recommended to prevent duplicate charges when retrying failed payments.

**Customer (Jan 15, 1:15 PM):**
We've implemented idempotency keys now. Testing...

**Customer (Jan 15, 2:40 PM):**
Tested with 50 retry scenarios - no duplicates! This fixed it.

But we now have 23 customers who were charged twice yesterday. Can you help us identify and refund them?

**Support Agent (Mike, Jan 15, 3:00 PM):**
Yes, I can query our logs for duplicate charges. Give me 30 minutes.

[Internal note: Queried payment logs for duplicate charges (same customer_id, same amount, within 5 seconds). Found 23 cases.]

**Support Agent (Mike, Jan 15, 3:35 PM):**
I found 23 duplicate transactions. I've initiated refunds for all of them:
[List of transaction IDs]

Refunds typically process within 5-7 business days.

**Customer (Jan 15, 3:50 PM):**
Thank you! This is resolved. We'll make sure to use idempotency keys going forward.

**Resolution:** Customer not using idempotency keys. Implemented fix. Refunded 23 duplicate charges.
**Prevention:** Added idempotency key requirement to onboarding checklist.

---

## TICKET #2389 - January 22, 2024
**Customer:** alex@saas-company.co (Enterprise)
**Subject:** Webhooks not being delivered
**Status:** RESOLVED  
**Priority:** Medium
**Tags:** webhooks, delivery-failure

**Initial Message (Jan 22, 9:30 AM):**
We're not receiving webhook notifications for payment events. We have a webhook URL configured: https://our-app.com/webhooks/acme

Checked our server logs - no incoming requests from your webhook service.

**Support Agent (Sarah, Jan 22, 10:00 AM):**
Hi Alex,

I checked our webhook delivery logs for your account. We're attempting to send webhooks but getting timeouts (no response within 10 seconds).

Your webhook endpoint must:
1. Be publicly accessible (not behind VPN/firewall)
2. Return 200 status within 10 seconds
3. Use HTTPS (not HTTP)

Can you verify these requirements?

**Customer (Jan 22, 10:25 AM):**
Our endpoint is HTTPS and publicly accessible. But it might be taking >10 seconds to respond because we process the webhook synchronously (update database, send email, etc.).

**Support Agent (Sarah, Jan 22, 10:45 AM):**
That's the issue! Your endpoint needs to return 200 immediately, then process the webhook asynchronously.

Example:
```python
@app.post("/webhooks/acme")
async def webhook(event: dict):
    # Return 200 immediately
    background_tasks.add_task(process_webhook, event)
    return {"status": "received"}

async def process_webhook(event):
    # Long processing here (database, email, etc.)
    ...
```

This way we get a 200 response quickly and don't timeout.

**Customer (Jan 22, 11:30 AM):**
That makes sense. We'll refactor our webhook handler.

**Customer (Jan 22, 3:15 PM):**
Refactored to process asynchronously. Can you resend the failed webhooks?

**Support Agent (Sarah, Jan 22, 3:30 PM):**
Done! Resent the last 50 failed webhook events. Check your logs.

**Customer (Jan 22, 3:45 PM):**
All received successfully! Thanks.

**Resolution:** Customer webhook endpoint processing synchronously and timing out. Fixed by implementing async processing.

---

## TICKET #2445 - January 28, 2024
**Customer:** ryan@marketplace.app (Free)
**Subject:** Rate limit too low!
**Status:** RESOLVED
**Priority:** Low
**Tags:** rate-limit, upgrade

**Initial Message (Jan 28, 4:20 PM):**
Your rate limit of 60 requests/minute is way too low! I need to make 500 requests/minute for my app to work.

Can you increase my limit?

**Support Agent (Mike, Jan 28, 4:45 PM):**
Hi Ryan,

Free tier includes 60 req/min. If you need higher limits, you can upgrade to:
- Pro: 300 req/min ($99/month)
- Enterprise: Custom limits (contact sales)

Also, are you caching API responses? Many apps make unnecessary repeat requests.

**Customer (Jan 28, 5:10 PM):**
I'm not caching anything. I'm polling your API every second to check payment status.

**Support Agent (Mike, Jan 28, 5:25 PM):**
That's very inefficient! Instead of polling, use webhooks. We'll notify you when payment status changes.

With webhooks, you'd make 1 API call to create the payment, then 0 calls while waiting. Our webhook notifies you when status changes.

This would reduce your API usage by 99%.

**Customer (Jan 28, 5:50 PM):**
I didn't know webhooks were an option. How do I set that up?

**Support Agent (Mike, Jan 28, 6:05 PM):**
Guide here: https://docs.acme.com/webhooks

Setup takes ~10 minutes.

**Customer (Jan 29, 10:30 AM):**
Implemented webhooks. My API usage dropped from 500 req/min to 5 req/min! 

I don't need to upgrade anymore. Thanks for the suggestion!

**Support Agent (Mike, Jan 29, 10:45 AM):**
Glad it worked out! Webhooks are almost always better than polling.

**Resolution:** Customer polling instead of using webhooks. Educated on webhooks, problem solved without upgrade.
**Lesson:** Most "rate limit is too low" tickets are architecture issues, not actual limits problems.

---

## TICKET #2567 - February 5, 2024
**Customer:** jenny@nonprofit.org (Free)
**Subject:** SSL certificate error
**Status:** RESOLVED
**Priority:** Low
**Tags:** ssl, certificate, troubleshooting

**Initial Message (Feb 5, 1:15 PM):**
Getting SSL error when calling your API:

```
SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate has expired
```

Is your SSL certificate expired???

**Support Agent (Sarah, Feb 5, 1:40 PM):**
Hi Jenny,

Our SSL certificate is valid until 2026. I just checked.

This error usually means your system's SSL certificates are outdated, or your system clock is wrong.

Can you check:
1. What operating system are you using?
2. Run `date` command and share the output
3. When was the last time you updated your system?

**Customer (Feb 5, 2:05 PM):**
I'm on Ubuntu 18.04 (pretty old, I know).

Date output: `Mon Feb 5 14:05:23 UTC 2022`

Wait... that says 2022?!

**Support Agent (Sarah, Feb 5, 2:15 PM):**
There's your problem! Your system clock is 2 years behind.

When SSL certificates are checked, your system compares the cert's expiry date with your system time. Since your clock is in 2022, it thinks our 2024-2026 cert hasn't been issued yet.

Fix:
```bash
sudo ntpdate -s time.nist.gov
# Or
sudo timedatectl set-ntp true
```

This will sync your system clock.

**Customer (Feb 5, 2:45 PM):**
Fixed the clock. SSL error is gone now! 

I have no idea how my clock got that far off. Thank you!

**Support Agent (Sarah, Feb 5, 2:50 PM):**
Glad it's working! System clocks can drift over time, especially on VMs. Setting up NTP (automatic time sync) prevents this.

**Resolution:** Customer system clock was 2 years behind, causing SSL verification to fail.

---

## TICKET #2678 - February 12, 2024
**Customer:** carlos@trading-platform.io (Enterprise)
**Subject:** Database connection errors during peak hours
**Status:** RESOLVED
**Priority:** High
**Tags:** database, connection-pool, performance

**Initial Message (Feb 12, 8:45 AM):**
Every day between 9-10 AM (market open), we get massive database connection errors:

```
OperationalError: FATAL: sorry, too many clients already
TimeoutError: Unable to acquire connection from pool within 30 seconds
```

Our app basically stops working for an hour. This is a critical issue affecting our trading platform.

**Support Agent (Tom, Feb 12, 9:15 AM):**
Hi Carlos,

This is a connection pool exhaustion issue on your end (not our API). Your application is running out of database connections.

Questions:
1. What's your database connection pool size?
2. Are you using connection context managers (with blocks)?
3. Do you have any long-running queries?
4. What's your peak concurrent users during 9-10 AM?

**Customer (Feb 12, 9:40 AM):**
1. Pool size: 20 connections
2. Not sure what context managers are
3. Some reports can take 5-10 seconds
4. Peak users: ~500 concurrent

**Support Agent (Tom, Feb 12, 10:00 AM):**
20 connections for 500 users is way too low, especially with long-running queries.

Here's what's happening:
- User makes request → app grabs DB connection
- Query runs for 10 seconds
- Connection is locked for 10 seconds
- With only 20 connections and lots of slow queries, pool gets exhausted quickly

Solutions:

1. Increase pool size:
```python
engine = create_engine(
    DATABASE_URL,
    pool_size=50,  # Increase from 20
    max_overflow=30,
    pool_timeout=30
)
```

2. Use context managers (auto-release connections):
```python
# BAD - connection never released
def get_data():
    conn = engine.connect()
    return conn.execute(query)

# GOOD - auto-releases
def get_data():
    with engine.connect() as conn:
        return conn.execute(query).fetchall()
```

3. Optimize slow queries (add indexes)
4. Use read replicas for reports (separate read traffic from writes)

**Customer (Feb 12, 11:30 AM):**
We found the issue! We have a data export feature that was grabbing a connection and never releasing it. Fixed with context manager.

Also increased pool size to 50.

Testing during next market open...

**Customer (Feb 13, 9:45 AM):**
No connection errors today! Problem solved. Thanks for the guidance.

**Resolution:** Connection pool too small + connection leaks. Fixed with larger pool and proper connection management.

---

## TICKET #2789 - February 18, 2024
**Customer:** priya@mobile-wallet.app (Pro)
**Subject:** 3D Secure redirect not working
**Status:** RESOLVED
**Priority:** Medium
**Tags:** payment, 3ds, authentication

**Initial Message (Feb 18, 3:20 PM):**
Payments requiring 3D Secure verification are failing. After customer enters their PIN on bank page, they're redirected to a blank page instead of back to our app.

We're losing ~40% of payments because of this.

**Support Agent (Mike, Feb 18, 3:50 PM):**
Hi Priya,

This is usually a redirect URL issue. Can you share:
1. The redirect URL you're providing in payment request
2. Whether you're testing in sandbox or production
3. Example failed payment ID

**Customer (Feb 18, 4:15 PM):**
1. Redirect URL: `http://localhost:3000/payment-success`
2. Production
3. Payment ID: pay_3ds_abc123

**Support Agent (Mike, Feb 18, 4:30 PM):**
Found the problem! You're using `http://localhost:3000` as your redirect URL in production.

Localhost only works on your computer. When your customer tries to redirect to localhost, it tries to connect to *their* computer (which isn't running your app).

You need to use your actual production URL:
```
https://your-actual-domain.com/payment-success
```

**Customer (Feb 18, 4:50 PM):**
Oh no! That was a copy-paste error from our test environment. Updated to production URL now.

Testing...

**Customer (Feb 18, 5:20 PM):**
Working perfectly now! Customers are successfully completing 3DS verification.

I feel silly for that localhost mistake. Thanks for catching it!

**Support Agent (Mike, Feb 18, 5:25 PM):**
No worries, it's a common mistake! Glad it's working now.

**Resolution:** Customer using localhost URL for 3DS redirects in production. Changed to production domain.

---

## TICKET #2891 - February 24, 2024
**Customer:** david@subscription-service.com (Pro)
**Subject:** Subscription renewals failing silently
**Status:** INVESTIGATING
**Priority:** High
**Tags:** subscription, renewal, webhook

**Initial Message (Feb 24, 10:30 AM):**
We have customers complaining that their subscriptions expired even though they have valid payment methods on file.

Looking at our logs, we're not receiving `subscription.renewed` webhook events. We *are* receiving `subscription.created` and `subscription.canceled` events, but not renewals.

This started around Feb 20.

**Support Agent (Sarah, Feb 24, 11:00 AM):**
Hi David,

Let me check our webhook delivery logs...

[Internal note: Checked logs. Renewal webhooks ARE being sent, but customer endpoint is returning 500 errors. Other webhook types (created, canceled) are succeeding.]

Your endpoint is returning 500 errors for renewal webhooks specifically. Can you check your server logs for errors?

**Customer (Feb 24, 11:35 AM):**
Checking... found it!

We recently refactored our webhook handler and accidentally broke the renewal event handling:

```python
elif event_type == "subscription.renewed":
    customer_id = event.data.customer_id  # ← This line throws error
```

The field is actually `customer` not `customer_id` for renewal events. Will fix now.

**Customer (Feb 24, 12:15 PM):**
Fixed! Can you resend the failed renewal webhooks from Feb 20-24?

**Support Agent (Sarah, Feb 24, 12:30 PM):**
Resending now... Done! Sent 234 renewal events.

**Customer (Feb 24, 12:45 PM):**
All processed successfully. Subscriptions are renewing correctly now.

**Resolution:** Customer webhook handler had bug in renewal event processing. Fixed and resent failed events.

---

## TICKET #2945 - March 1, 2024
**Customer:** kevin@api-aggregator.com (Free)
**Subject:** Getting 403 Forbidden randomly
**Status:** RESOLVED
**Priority:** Medium
**Tags:** api-error, 403, ip-whitelist

**Initial Message (Mar 1, 2:50 PM):**
I keep getting 403 Forbidden errors randomly. Sometimes API works fine, sometimes 403. No pattern to it.

**Support Agent (Mike, Mar 1, 3:15 PM):**
Hi Kevin,

403 usually means you're authenticated but not authorized. Checking your account...

I see you have IP whitelist enabled with these IPs:
- 203.0.113.5
- 203.0.113.12

Are you making requests from different IPs?

**Customer (Mar 1, 3:40 PM):**
Oh! I'm running my app on AWS Lambda. Lambda functions get different IPs each time they run.

So sometimes my Lambda gets an IP on the whitelist, sometimes not. That explains the randomness!

What should I do?

**Support Agent (Mike, Mar 1, 4:00 PM):**
Two options:

1. Disable IP whitelist (less secure but works with dynamic IPs)
2. Use AWS VPC with NAT Gateway (all Lambda traffic goes through fixed IP)

Option 2 is more secure but requires AWS setup.

**Customer (Mar 1, 4:25 PM):**
I'll disable IP whitelist for now and set up NAT Gateway later.

**Customer (Mar 1, 4:40 PM):**
Disabled IP whitelist. No more 403 errors!

**Resolution:** Customer using IP whitelist with dynamic IPs (AWS Lambda). Disabled whitelist as temporary solution.

---

## TICKET #3012 - March 5, 2024
**Customer:** lisa@fintech-app.co (Enterprise)
**Subject:** Currency conversion rates are wrong
**Status:** CLOSED - NOT A BUG
**Priority:** Low
**Tags:** currency, conversion, documentation

**Initial Message (Mar 5, 11:20 AM):**
Your currency conversion rates don't match the official exchange rates!

Example:
- Your rate (USD to EUR): 0.85
- Official rate: 0.92

This is a huge discrepancy!

**Support Agent (Sarah, Mar 5, 11:50 AM):**
Hi Lisa,

Can you tell me where you're seeing our rate of 0.85? Also, what's your source for the "official rate"?

**Customer (Mar 5, 12:15 PM):**
I'm seeing 0.85 in your API response. My source is xe.com.

**Support Agent (Sarah, Mar 5, 12:40 PM):**
I just checked our current USD/EUR rate: 0.9187

Not 0.85. Can you share the exact API request you're making?

**Customer (Mar 5, 1:10 PM):**
```bash
curl https://api.acme.com/v2/exchange-rates/USD/EUR
```

Response: `{"rate": 0.8523}`

**Support Agent (Sarah, Mar 5, 1:25 PM):**
That's odd. Let me check...

[Internal note: Checked API. Current rate is 0.9187. Wait... customer is on free tier with cached rates. Free tier gets cached rates (updated daily). Pro/Enterprise get real-time rates.]

Found it! You're on the free tier, which gets cached exchange rates updated once per day. The rate you're seeing (0.8523) is from yesterday.

Pro and Enterprise tiers get real-time rates (updated every minute).

**Customer (Mar 5, 1:50 PM):**
Ah, that explains it! I need real-time rates. Will upgrade to Pro.

**Customer (Mar 5, 2:30 PM):**
Upgraded. Now seeing real-time rates. Thanks!

**Resolution:** Customer on free tier expecting real-time rates. Free tier uses daily cached rates. Upgraded to Pro for real-time.

---

## TICKET #3089 - March 8, 2024 (TODAY)
**Customer:** tech@big-retailer.com (Enterprise)
**Subject:** URGENT: Complete API outage
**Status:** INVESTIGATING
**Priority:** CRITICAL
**Tags:** outage, api-down

**Initial Message (Mar 8, 8:03 AM):**
YOUR ENTIRE API IS DOWN!!!

All requests timing out. Our website is broken. This is costing us millions!

**Support Agent (Tom, Mar 8, 8:05 AM):**
Checking status page and internal monitors...

[Internal note: Status page shows all systems operational. Internal monitors show no issues. Hmm...]

Can you share:
1. Example request that's timing out
2. Your location
3. Traceroute output to api.acme.com

**Customer (Mar 8, 8:10 AM):**
```bash
curl https://api.acme.com/v2/health
# Hangs for 60 seconds, then times out
```

Location: AWS us-west-2

Traceroute: [shows connection dying at their firewall]

**Support Agent (Tom, Mar 8, 8:15 AM):**
Your traceroute shows the connection failing at *your* firewall, not our servers.

Did your IT team make any firewall changes this morning?

**Customer (Mar 8, 8:25 AM):**
Let me check with IT...

**Customer (Mar 8, 8:40 AM):**
IT confirmed they updated firewall rules at 8:00 AM and accidentally blocked outbound HTTPS to *.acme.com.

They're fixing it now...

**Customer (Mar 8, 8:50 AM):**
Fixed! API working again.

Sorry for the false alarm. Our IT team messed up, not you guys.

**Support Agent (Tom, Mar 8, 8:55 AM):**
No worries! Glad it's resolved quickly.

Pro tip: Set up external monitoring (from outside your network) to distinguish between your infrastructure issues vs our API issues.

**Resolution:** Customer's firewall blocking ACME API. Not an actual API outage.

---

[End of Support Tickets Archive - 847 total tickets]
[For full archive access, contact support@acme.com]
