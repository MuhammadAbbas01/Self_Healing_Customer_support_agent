import agent
from database import DatabaseManager
from monitoring import send_metric
from config import DATABASE_URL
from data import setup_rag
import time
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

print("Setting up RAG system...")
collection, embedding_model = setup_rag()

agent.collection = collection
agent.embedding_model = embedding_model

db = DatabaseManager(DATABASE_URL)
app_graph = agent.build_graph()

app = FastAPI(title="AI Support Agent")


class TicketRequest(BaseModel):
    message: str
    code: str | None = None


class TicketResponse(BaseModel):
    ticket_id: str
    status: str
    solution: str


def process_ticket(customer_message, customer_code=None):
    ticket_id = db.create_ticket(customer_message, customer_code)
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

    return result


@app.get("/")
def home():
    return {
        "status": "AI Support Agent is running!",
        "endpoints": {
            "/": "Health check",
            "/ticket": "POST - Submit ticket",
            "/docs": "API documentation"
        }
    }


@app.post("/ticket", response_model=TicketResponse)
def create_ticket_api(ticket: TicketRequest):
    if not ticket.message.strip():
        return {"error": "Message required"}

    result = process_ticket(ticket.message, ticket.code)

    return TicketResponse(
        ticket_id=result["ticket_id"],
        status="processed",
        solution=result["customer_response"]
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)