"""
testing.py - Test different customer scenarios

This file tests your system with 3 different issues to verify it works
"""

import time
from main import process_ticket

# ============================================
# TEST 1: Authentication Error (401)
# ============================================
print("\n" + "="*50)
print("TEST 1: Authentication Error")
print("="*50)

# What we're testing: Customer has wrong API key
result1 = process_ticket(
    customer_message="My API returns 401 error",
    customer_code="headers = {'Authorization': 'test123'}"
)

# Check if solution was found
if result1.get("test_result") == "passed":
    print("✅ TEST 1 PASSED - Solution found!")
else:
    print("❌ TEST 1 FAILED - No solution")

# ============================================
# TEST 2: Database Connection Error
# ============================================
print("\n" + "="*50)
print("TEST 2: Database Connection Error")
print("="*50)

# What we're testing: Customer's database pool is full
result2 = process_ticket(
    customer_message="Getting 'Too many connections' error from database",
    customer_code="conn = db.connect()"
)

if result2.get("test_result") == "passed":
    print("✅ TEST 2 PASSED - Solution found!")
else:
    print("❌ TEST 2 FAILED - No solution")

# ============================================
# TEST 3: SSL Certificate Error
# ============================================
print("\n" + "="*50)
print("TEST 3: SSL Certificate Error")
print("="*50)

# What we're testing: Customer's SSL certificates are expired
result3 = process_ticket(
    customer_message="SSL certificate verification failed when calling API",
    customer_code=None  # No code provided
)

if result3.get("test_result") == "passed":
    print("✅ TEST 3 PASSED - Solution found!")
else:
    print("❌ TEST 3 FAILED - No solution")

# ============================================
# SUMMARY
# ============================================
print("\n" + "="*50)
print("TEST SUMMARY")
print("="*50)

passed = sum([
    result1.get("test_result") == "passed",
    result2.get("test_result") == "passed",
    result3.get("test_result") == "passed"
])

print(f"Tests Passed: {passed}/3")
print(f"Success Rate: {passed/3*100:.0f}%")

if passed == 3:
    print("\n🎉 ALL TESTS PASSED! System working perfectly!")
elif passed >= 2:
    print("\n✅ Most tests passed. System mostly working.")
else:
    print("\n⚠️ Multiple failures. Check system configuration.")