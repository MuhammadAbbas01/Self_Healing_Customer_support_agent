import psycopg2
from psycopg2.extras import Json, RealDictCursor
import uuid
from datetime import datetime
from config import DATABASE_URL


class DatabaseManager:
    """
    Database manager for Supabase PostgreSQL

    Functions:
    1. create_ticket() - Create new ticket
    2. update_ticket() - Update ticket info
    3. log_agent_step() - Save what each node did
    4. save_solution() - Save final solution
    5. get_ticket_history() - Get complete ticket info
    6. update_metrics() - Track daily performance
    """

    def __init__(self, db_url):
        """Initialize with database connection string"""
        self.db_url = db_url

    def get_connection(self):
        """Connect to Supabase database"""
        return psycopg2.connect(self.db_url)

    def create_ticket(self, customer_message, customer_code=None):
        """Create new ticket in database"""
        ticket_id = f"TICKET-{uuid.uuid4().hex[:8].upper()}"

        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO tickets (ticket_id, customer_message, customer_code, status)
            VALUES (%s, %s, %s, 'processing')
            RETURNING ticket_id
        """, (ticket_id, customer_message, customer_code))

        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        print(f"✅ Created ticket: {ticket_id}")
        return result[0]

    def update_ticket(self, ticket_id, **kwargs):
        """Update ticket with new information"""
        conn = self.get_connection()
        cur = conn.cursor()

        updates = []
        values = []
        for key, value in kwargs.items():
            updates.append(f"{key} = %s")
            values.append(value)

        values.append(ticket_id)

        query = f"""
            UPDATE tickets
            SET {', '.join(updates)}, updated_at = NOW()
            WHERE ticket_id = %s
        """
        cur.execute(query, values)

        conn.commit()
        cur.close()
        conn.close()

    def log_agent_step(self, ticket_id, node_name, attempt_count,
                       input_data, output_data, error_logs=None):
        """Save what happened in each node"""
        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO agent_steps
            (ticket_id, node_name, attempt_count, input_data, output_data, error_logs)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (ticket_id, node_name, attempt_count,
              Json(input_data), Json(output_data), error_logs))

        conn.commit()
        cur.close()
        conn.close()

    def save_solution(self, ticket_id, proposed_fix, fix_explanation,
                      estimated_risk, test_result, verified=False):
        """Save the final solution"""
        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO solutions
            (ticket_id, proposed_fix, fix_explanation, estimated_risk, test_result, verified)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (ticket_id, proposed_fix, fix_explanation,
              estimated_risk, test_result, verified))

        conn.commit()
        cur.close()
        conn.close()

    def get_ticket_history(self, ticket_id):
        """Get complete ticket history"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT * FROM tickets WHERE ticket_id = %s", (ticket_id,))
        ticket = cur.fetchone()

        cur.execute("""
            SELECT * FROM agent_steps
            WHERE ticket_id = %s
            ORDER BY created_at
        """, (ticket_id,))
        steps = cur.fetchall()

        cur.execute("SELECT * FROM solutions WHERE ticket_id = %s", (ticket_id,))
        solution = cur.fetchone()

        cur.close()
        conn.close()

        return {
            'ticket': dict(ticket) if ticket else None,
            'steps': [dict(s) for s in steps],
            'solution': dict(solution) if solution else None
        }

    def update_metrics(self, total_tickets, auto_solved, failed):
        """Track daily performance metrics"""
        success_rate = (auto_solved / total_tickets * 100) if total_tickets > 0 else 0

        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO metrics (date, total_tickets, auto_solved, failed, success_rate)
            VALUES (CURRENT_DATE, %s, %s, %s, %s)
            ON CONFLICT (date) DO UPDATE SET
                total_tickets = metrics.total_tickets + EXCLUDED.total_tickets,
                auto_solved = metrics.auto_solved + EXCLUDED.auto_solved,
                failed = metrics.failed + EXCLUDED.failed,
                success_rate = EXCLUDED.success_rate
        """, (total_tickets, auto_solved, failed, success_rate))

        conn.commit()
        cur.close()
        conn.close()