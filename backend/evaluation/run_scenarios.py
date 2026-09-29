"""Run a few sample tickets through the agent.

Run from the backend folder:
    python -m evaluation.run_scenarios
"""
from main import process_ticket

SCENARIOS = [
    {
        "name": "Authentication error (401)",
        "message": "My API returns 401 error",
        "code": "headers = {'Authorization': 'test123'}",
    },
    {
        "name": "Database connection error",
        "message": "Getting 'Too many connections' error from database",
        "code": "conn = db.connect()",
    },
    {
        "name": "SSL certificate error",
        "message": "SSL certificate verification failed when calling API",
        "code": None,
    },
]


def main():
    passed = 0
    for i, scenario in enumerate(SCENARIOS, start=1):
        print(f"\nTest {i}: {scenario['name']}")
        result = process_ticket(scenario["message"], scenario["code"])
        ok = result.get("test_result") == "passed"
        passed += ok
        print(f"Test {i} {'passed' if ok else 'failed'}")

    print(f"\n{passed}/{len(SCENARIOS)} scenarios passed")


if __name__ == "__main__":
    main()
