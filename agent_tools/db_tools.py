import psycopg2
import psycopg2.errors
import json
import os
from pydantic import BaseModel, Field

class ExplainAnalyzeInput(BaseModel):
    query: str = Field(..., description="The raw SQL query to analyze.")

def run_explain_analyze(input_data: ExplainAnalyzeInput) -> str:
    """
    Safely runs EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) on the provided query.
    Enforces a strict 5000ms timeout and read-only transaction.
    """
    conn = None
    try:
        conn = psycopg2.connect(
            host=os.environ.get("PG_HOST", "localhost"),
            port=os.environ.get("PG_PORT", 5432),
            dbname=os.environ.get("PG_DBNAME", "postgres"),
            user=os.environ.get("PG_USER", "postgres"),
            password=os.environ.get("PG_PASSWORD", "")
        )
        # Ensure we control the transaction
        conn.autocommit = False
        
        with conn.cursor() as cursor:
            # ==========================================
            # CRITICAL SECURITY GUARDS
            # ==========================================
            cursor.execute("SET statement_timeout = 5000;")
            cursor.execute("SET TRANSACTION READ ONLY;")
            
            cursor.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) $1", (input_data.query,))
            
            result = cursor.fetchone()
            if result:
                return json.dumps({"status": "success", "plan": result[0]})
            return json.dumps({"status": "success", "plan": []})
            
    except psycopg2.errors.QueryCanceled as e:
        if conn:
            conn.rollback()
        return json.dumps({
            "status": "error",
            "error_type": "QueryCanceled",
            "message": "Query timed out after 5000ms."
        })
    except psycopg2.errors.InFailedSqlTransaction as e:
        if conn:
            conn.rollback()
        return json.dumps({
            "status": "error",
            "error_type": "InFailedSqlTransaction",
            "message": f"Transaction failed: {str(e)}"
        })
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "message": f"Database error: {str(e)}"
        })
    except Exception as e:
        if conn:
            conn.rollback()
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "message": f"Execution error: {str(e)}"
        })
    finally:
        if conn:
            conn.close()
