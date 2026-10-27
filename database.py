import json
import uuid
from datetime import datetime
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from config import DATABASE_URL


class DatabaseManager:
    """
    DatabaseManager with Supabase PostgreSQL (async version, with connection pooling)

    Functions:
    create_ticket()
    update_ticket()
    log_Agent_Step()
    save_solution()
    get_ticket_history()
    update_metrics()
    get_pending_escalations()
    save_draft()
    """

    def __init__(self, db_url):
        # The pool cannot be opened here (it needs an async context).
        # Call open_pool() at app startup and close_pool() at shutdown.
        # prepare_threshold=None: the Supabase pooler (port 6543) does not support prepared statements.
        self.db_url = db_url
        self.pool = AsyncConnectionPool(
            conninfo=db_url,
            open=False,
            kwargs={"autocommit": True, "prepare_threshold": None},
            check=AsyncConnectionPool.check_connection,
            max_idle=60,
        )

    async def open_pool(self):
        """Call this at app startup to open the connection pool"""
        await self.pool.open()

    async def close_pool(self):
        """Call this at app shutdown to close all connections"""
        await self.pool.close()

    async def create_ticket(self, customer_message, customer_code=None):
        """Create new ticket in database"""
        ticket_id = f"TICKET-{uuid.uuid4().hex[:8].upper()}"

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO tickets (ticket_id, customer_message, customer_code, status)
                    VALUES (%s, %s, %s, 'processing')
                    RETURNING ticket_id
                    """,
                    (ticket_id, customer_message, customer_code),
                )
                result = await cur.fetchone()

        print(f"ticket_created: {ticket_id}")
        return result[0]

    async def update_ticket(self, ticket_id, **kwargs):
        """Update ticket with new information"""
        values = []
        updates = []

        for key, value in kwargs.items():
            updates.append(f"{key} = %s")
            values.append(value)

        values.append(ticket_id)

        query = f"""
            UPDATE tickets
            SET {', '.join(updates)}, updated_at = NOW()
            WHERE ticket_id = %s
        """

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, values)

    async def log_Agent_Step(self, ticket_id, node_name, input_data, output_data, attempt_count, error_logs=None):
        """Save what happened in each node"""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO agent_step (ticket_id, node_name, input_data, output_data, attempt_count, error_logs)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        ticket_id,
                        node_name,
                        json.dumps(input_data, default=str),
                        json.dumps(output_data if output_data else {"note": "no state changes"}, default=str),
                        attempt_count,
                        error_logs or "No errors",
                    ),
                )

    async def save_solution(self, ticket_id, proposed_fix, fix_explanation, test_result, estimated_risk,
                            verified=False, attempt_number=1, human_approved=True, human_feedback=None):
        """Save the final solution"""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO solution (ticket_id, proposed_fix, fix_explanation, test_result,
                    estimated_risk, verified, attempt_number, human_approved, human_feedback)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (ticket_id, proposed_fix, fix_explanation, test_result or "not_run",
                     estimated_risk or "unknown", verified, attempt_number, human_approved,
                     human_feedback or "Approved without comments"),
                )

    async def get_ticket_history(self, ticket_id):
        """Get complete ticket history"""
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM tickets WHERE ticket_id = %s",
                    (ticket_id,),
                )
                ticket = await cur.fetchone()

                await cur.execute(
                    """
                    SELECT * FROM agent_step
                    WHERE ticket_id = %s
                    ORDER BY created_at
                    """,
                    (ticket_id,),
                )
                agent_steps = await cur.fetchall()

                await cur.execute(
                    "SELECT * FROM solution WHERE ticket_id = %s",
                    (ticket_id,),
                )
                solution = await cur.fetchone()

        return {
            "ticket": dict(ticket) if ticket else None,
            "agent_steps": [dict(step) for step in agent_steps],
            "solution": dict(solution) if solution else None,
        }

    async def update_metrics(self, total_tickets, auto_solved, failed):
        """Track daily performance metrics"""
        success_rate = (auto_solved / total_tickets * 100) if total_tickets > 0 else 0

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO metrics (date, total_tickets, auto_solved, failed, success_rate)
                    VALUES (CURRENT_DATE, %s, %s, %s, %s)
                    ON CONFLICT (date) DO UPDATE SET
                    total_tickets = metrics.total_tickets + EXCLUDED.total_tickets,
                    auto_solved = metrics.auto_solved + EXCLUDED.auto_solved,
                    failed = metrics.failed + EXCLUDED.failed,
                    success_rate = EXCLUDED.success_rate
                    """,
                    (total_tickets, auto_solved, failed, success_rate),
                )

    async def get_pending_escalations(self):
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute("SELECT * FROM tickets WHERE status = %s", ("escalated",))
                results = await cur.fetchall()

        return [dict(row) for row in results]

    async def record_review(self, ticket_id, human_approved, human_feedback):
        """Store the human decision on the newest draft (the one the human just reviewed)."""
        if human_feedback:
            feedback = human_feedback
        elif human_approved:
            feedback = "Approved without comments"
        else:
            feedback = "Rejected without comments"
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE ticket_draft SET human_approved = %s, human_feedback = %s
                    WHERE draft_id = (
                        SELECT draft_id FROM ticket_draft
                        WHERE ticket_id = %s ORDER BY created_at DESC LIMIT 1
                    )
                    """,
                    (human_approved, feedback, ticket_id),
                )

    async def save_draft(self, ticket_id, attempt_number, proposed_fix, fix_explanation,
                         test_result, human_approved, human_feedback):
        draft_id = f"DRAFT-{uuid.uuid4().hex[:8].upper()}"

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO ticket_draft (draft_id, ticket_id, attempt_number, proposed_fix,
                    fix_explanation, test_result, human_approved, human_feedback)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (draft_id, ticket_id, attempt_number, proposed_fix, fix_explanation,
                     test_result, human_approved, human_feedback),
                )
