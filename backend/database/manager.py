import psycopg2
from psycopg2.extras import Json, RealDictCursor
import uuid


class DatabaseManager:
    def __init__(self, db_url):
        self.db_url = db_url

    def get_connection(self):
        return psycopg2.connect(self.db_url)

    def create_ticket(self, customer_message, customer_code=None):
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

        print(f"Created ticket {ticket_id}")
        return result[0]

    def update_ticket(self, ticket_id, **kwargs):
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