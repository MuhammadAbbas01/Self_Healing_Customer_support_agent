"""
testing.py - Test 3 customer scenarios through the full agent pipeline
"""
import agent
from database import DatabaseManager
from monitoring import send_metric
from config import DATABASE_URL
from data import setup_rag
import time

print("Setting up RAG system...")
collection, embedding_model = setup_rag()
agent.collection = collection
agent.embedding_model = embedding_model
db = DatabaseManager(DATABASE_URL)
app_graph = agent.build_graph()


def process_ticket(customer_message, customer_code=None):
    ticket_id = db.create_ticket(customer_message, customer_code)
    print(f"\nCreated ticket: {ticket_id}")
    start_time = time.time()
    initial_state = {
        "customer_message": customer_message,
        "customer_code": customer_code,
        "ticket_id": ticket_id,
        "attempt_count": 0,
        "max_attempts": 3
    }
    result = app_graph.invoke(initial_state)
    total_time = time.time() - start_time
    send_metric("langgraph_tickets_total", 1)
    if result.get("test_result") == "passed":
        send_metric("langgraph_tickets_success", 1)
    print(f"Time: {total_time:.2f}s")
    return result


print("\n" + "="*50)
print("TEST 1: Authentication Error")
print("="*50)
result1 = process_ticket("My API returns 401 error", "headers = {'Authorization': 'test123'}")
print("TEST 1 PASSED" if result1.get("test_result") == "passed" else "TEST 1 FAILED")

print("\n" + "="*50)
print("TEST 2: Database Connection Error")
print("="*50)
result2 = process_ticket("Getting 'Too many connections' error from database", "conn = db.connect()")
print("TEST 2 PASSED" if result2.get("test_result") == "passed" else "TEST 2 FAILED")

print("\n" + "="*50)
print("TEST 3: SSL Certificate Error")
print("="*50)
result3 = process_ticket("SSL certificate verification failed when calling API")
print("TEST 3 PASSED" if result3.get("test_result") == "passed" else "TEST 3 FAILED")

print("\n" + "="*50)
passed = sum([r.get("test_result") == "passed" for r in [result1, result2, result3]])
print(f"SUMMARY: {passed}/3 passed ({passed/3*100:.0f}%)")
if passed == 3:
    print("ALL TESTS PASSED")
elif passed >= 2:
    print("MOSTLY PASSING")
else:
    print("CHECK SYSTEM CONFIGURATION")
print("="*50)
