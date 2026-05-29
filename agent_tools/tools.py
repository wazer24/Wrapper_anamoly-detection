import psycopg2
import psycopg2.errors
import psycopg2.sql
import json
import os
import re
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Pydantic Schemas for all tools
# ---------------------------------------------------------------------------

class ExplainAnalyzeInput(BaseModel):
    query: str = Field(..., description="The raw SQL query to analyze.")

class HypotheticalIndexInput(BaseModel):
    table: str = Field(..., description="Table name to create index on.")
    columns: list[str] = Field(..., description="Column(s) for the index.")
    index_type: str = Field(default="btree", description="Index type (btree, hash, gin, gist).")

class PrismaSchemaInput(BaseModel):
    model_name: Optional[str] = Field(default=None, description="Optional: specific Prisma model to read.")

class SourceFileInput(BaseModel):
    file_path: str = Field(..., description="Path to the source file to inspect (relative to project root).")

class TableStatisticsInput(BaseModel):
    table_name: str = Field(..., description="Table name to fetch statistics for.")

class CodeChangeInput(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier.")
    query_text: str = Field(..., description="Original slow query text.")
    proposed_fix: str = Field(..., description="The proposed code change or index definition.")
    fix_type: str = Field(..., description="Type of fix: 'index_addition', 'code_rewrite', 'schema_change'.")
    risk_level: int = Field(default=1, ge=1, le=3, description="Risk level 1 (low) - 3 (high).")

class PRCommentInput(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier.")
    pr_number: int = Field(default=0, description="PR number. 0 means no PR context.")
    diagnosis: str = Field(..., description="Diagnosis summary.")
    proposed_fix: str = Field(..., description="Proposed fix text.")
    risk_level: int = Field(..., description="Risk level 1-3.")

class HumanApprovalInput(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier.")
    proposed_fix: str = Field(..., description="The fix waiting for approval.")
    risk_level: int = Field(..., description="Risk level that triggered the gate.")

# ---------------------------------------------------------------------------
# Database connection helper
# ---------------------------------------------------------------------------

def _get_db_connection():
    return psycopg2.connect(
        host=os.environ.get("PG_HOST", "localhost"),
        port=os.environ.get("PG_PORT", 5432),
        dbname=os.environ.get("PG_DBNAME", "postgres"),
        user=os.environ.get("PG_USER", "postgres"),
        password=os.environ.get("PG_PASSWORD", ""),
    )

# ---------------------------------------------------------------------------
# Tool 1: run_explain_analyze (existing, consolidated)
# ---------------------------------------------------------------------------

def run_explain_analyze(input_data: ExplainAnalyzeInput) -> str:
    conn = None
    try:
        conn = _get_db_connection()
        conn.autocommit = False
        with conn.cursor() as cursor:
            cursor.execute("SET statement_timeout = 5000;")
            cursor.execute("SET TRANSACTION READ ONLY;")
            cursor.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) $1", (input_data.query,))
            result = cursor.fetchone()
            if result:
                return json.dumps({"status": "success", "plan": result[0]})
            return json.dumps({"status": "success", "plan": []})
    except psycopg2.errors.QueryCanceled as e:
        if conn: conn.rollback()
        return json.dumps({"status": "error", "error_type": "QueryCanceled", "message": "Query timed out after 5000ms."})
    except psycopg2.errors.InFailedSqlTransaction as e:
        if conn: conn.rollback()
        return json.dumps({"status": "error", "error_type": "InFailedSqlTransaction", "message": f"Transaction failed: {str(e)}"})
    except psycopg2.Error as e:
        if conn: conn.rollback()
        return json.dumps({"status": "error", "error_type": type(e).__name__, "message": f"Database error: {str(e)}"})
    except Exception as e:
        if conn: conn.rollback()
        return json.dumps({"status": "error", "error_type": type(e).__name__, "message": f"Execution error: {str(e)}"})
    finally:
        if conn: conn.close()

# ---------------------------------------------------------------------------
# Tool 2: create_hypothetical_index (wraps HypoPG logic from run_phase_2.py)
# ---------------------------------------------------------------------------

_IDENTIFIER_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

def _validate_identifier(name: str, label: str) -> None:
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid {label}: '{name}' does not match ^[a-zA-Z_][a-zA-Z0-9_]*$")

def create_hypothetical_index(input_data: HypotheticalIndexInput) -> str:
    conn = None
    try:
        for col in input_data.columns:
            _validate_identifier(col, "column name")
        _validate_identifier(input_data.table, "table name")
        _validate_identifier(input_data.index_type, "index type")

        conn = _get_db_connection()
        conn.autocommit = False
        with conn.cursor() as cursor:
            cursor.execute("SET statement_timeout = 10000;")
            cursor.execute("SET TRANSACTION READ ONLY;")

            cursor.execute("SELECT 1 FROM pg_tables WHERE tablename = %s", (input_data.table,))
            if not cursor.fetchone():
                return json.dumps({"status": "error", "message": f"Table '{input_data.table}' does not exist in pg_catalog."})

            safe_table = psycopg2.sql.Identifier(input_data.table)
            safe_type = psycopg2.sql.SQL(input_data.index_type)
            safe_cols = psycopg2.sql.SQL(", ").join(psycopg2.sql.Identifier(c) for c in input_data.columns)
            create_stmt = psycopg2.sql.SQL("CREATE INDEX ON {} USING {} ({})").format(safe_table, safe_type, safe_cols)
            hypopg_sql = psycopg2.sql.SQL("SELECT hypopg_create_index({})").format(psycopg2.sql.Literal(str(create_stmt)))

            cursor.execute("SELECT hypopg_reset();")
            cursor.execute(hypopg_sql)
            row = cursor.fetchone()
            hypoid = row[0] if row else None
            conn.rollback()
            return json.dumps({"status": "success", "hypoid": str(hypoid) if hypoid else None, "table": input_data.table, "columns": input_data.columns, "index_type": input_data.index_type})
    except ValueError as e:
        return json.dumps({"status": "error", "error_type": "ValidationError", "message": str(e)})
    except psycopg2.Error as e:
        if conn: conn.rollback()
        return json.dumps({"status": "error", "error_type": type(e).__name__, "message": f"HypoPG error: {str(e)}"})
    except Exception as e:
        if conn: conn.rollback()
        return json.dumps({"status": "error", "error_type": type(e).__name__, "message": f"Execution error: {str(e)}"})
    finally:
        if conn: conn.close()

# ---------------------------------------------------------------------------
# Tool 3: read_prisma_schema
# ---------------------------------------------------------------------------

def read_prisma_schema(input_data: PrismaSchemaInput) -> str:
    schema_path = PROJECT_ROOT / "prisma" / "schema.prisma"
    if not schema_path.exists():
        return json.dumps({"status": "error", "message": f"schema.prisma not found at {schema_path}"})
    try:
        content = schema_path.read_text(encoding="utf-8")
        if input_data.model_name:
            model_pattern = rf"model {input_data.model_name} \{{(.*?)\n\}}"
            match = re.search(model_pattern, content, re.DOTALL)
            if match:
                return json.dumps({"status": "success", "model": input_data.model_name, "schema": match.group(0)})
            return json.dumps({"status": "error", "message": f"Model {input_data.model_name} not found in schema."})
        return json.dumps({"status": "success", "schema": content})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to read schema: {str(e)}"})

# ---------------------------------------------------------------------------
# Tool 4: read_source_file
# ---------------------------------------------------------------------------

def read_source_file(input_data: SourceFileInput) -> str:
    full_path = (PROJECT_ROOT / input_data.file_path).resolve()
    try:
        full_path.relative_to(PROJECT_ROOT)
    except ValueError:
        return json.dumps({"status": "error", "message": "Path traversal denied."})
    if not full_path.exists() or not full_path.is_file():
        return json.dumps({"status": "error", "message": f"File not found: {full_path}"})
    try:
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return json.dumps({"status": "success", "path": str(full_path), "content": content})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to read file: {str(e)}"})

# ---------------------------------------------------------------------------
# Tool 5: fetch_table_statistics
# ---------------------------------------------------------------------------

def fetch_table_statistics(input_data: TableStatisticsInput) -> str:
    conn = None
    try:
        conn = _get_db_connection()
        conn.autocommit = False
        with conn.cursor() as cursor:
            cursor.execute("SET statement_timeout = 5000;")
            cursor.execute("SET TRANSACTION READ ONLY;")
            cursor.execute("""
                SELECT
                    relname, n_live_tup, n_dead_tup,
                    seq_scan, seq_tup_read, idx_scan,
                    last_vacuum, last_analyze,
                    pg_size_pretty(pg_total_relation_size(relid)) AS total_size
                FROM pg_stat_user_tables
                WHERE relname = %s
            """, (input_data.table_name,))
            row = cursor.fetchone()
            if not row:
                return json.dumps({"status": "error", "message": f"Table '{input_data.table_name}' not found in pg_stat_user_tables."})
            return json.dumps({"status": "success", "table": input_data.table_name, "stats": {
                "n_live_tup": row[1], "n_dead_tup": row[2],
                "seq_scan": row[3], "seq_tup_read": row[4], "idx_scan": row[5],
                "last_vacuum": str(row[6]) if row[6] else None,
                "last_analyze": str(row[7]) if row[7] else None,
                "total_size": row[8],
            }})
    except psycopg2.Error as e:
        if conn: conn.rollback()
        return json.dumps({"status": "error", "error_type": type(e).__name__, "message": f"Database error: {str(e)}"})
    except Exception as e:
        if conn: conn.rollback()
        return json.dumps({"status": "error", "message": f"Execution error: {str(e)}"})
    finally:
        if conn: conn.close()

# ---------------------------------------------------------------------------
# Tool 6: propose_code_change
# ---------------------------------------------------------------------------

_proposed_changes: list[dict] = []

def propose_code_change(input_data: CodeChangeInput) -> str:
    change = {
        "tenant_id": input_data.tenant_id,
        "query_text": input_data.query_text,
        "proposed_fix": input_data.proposed_fix,
        "fix_type": input_data.fix_type,
        "risk_level": input_data.risk_level,
        "status": "pending",
    }
    _proposed_changes.append(change)
    return json.dumps({"status": "success", "change_id": len(_proposed_changes) - 1, "change": change})

def get_pending_changes() -> list[dict]:
    return [c for c in _proposed_changes if c["status"] == "pending"]

# ---------------------------------------------------------------------------
# Tool 7: publish_pr_comment
# ---------------------------------------------------------------------------

def publish_pr_comment(input_data: PRCommentInput) -> str:
    comment = (
        f"## AI Database Optimization Report\n\n"
        f"**Tenant:** `{input_data.tenant_id}`\n\n"
        f"### Diagnosis\n{input_data.diagnosis}\n\n"
        f"### Proposed Fix\n```\n{input_data.proposed_fix}\n```\n\n"
        f"**Risk Level:** {input_data.risk_level}/3\n"
    )
    if input_data.pr_number > 0:
        comment += f"\n*Posted to PR #{input_data.pr_number}*"
    return json.dumps({"status": "success", "comment": comment, "pr_number": input_data.pr_number})

# ---------------------------------------------------------------------------
# Tool 8: request_human_approval
# ---------------------------------------------------------------------------

_approval_requests: list[dict] = []

def request_human_approval(input_data: HumanApprovalInput) -> str:
    request = {
        "tenant_id": input_data.tenant_id,
        "proposed_fix": input_data.proposed_fix,
        "risk_level": input_data.risk_level,
        "status": "pending",
    }
    _approval_requests.append(request)
    return json.dumps({"status": "awaiting_approval", "request_id": len(_approval_requests) - 1, "request": request})

def get_approval_status(request_id: int) -> str:
    if request_id < 0 or request_id >= len(_approval_requests):
        return json.dumps({"status": "error", "message": "Invalid request_id."})
    return json.dumps({"status": "ok", "request": _approval_requests[request_id]})

def set_approval_status(request_id: int, status: str) -> str:
    if request_id < 0 or request_id >= len(_approval_requests):
        return json.dumps({"status": "error", "message": "Invalid request_id."})
    if status not in ("APPROVED", "DENIED"):
        return json.dumps({"status": "error", "message": f"Invalid status '{status}'. Must be APPROVED or DENIED."})
    _approval_requests[request_id]["status"] = status
    logger = __import__("logging").getLogger(__name__)
    logger.info("[Approval] Request %d set to %s", request_id, status)
    return json.dumps({"status": "ok", "request": _approval_requests[request_id]})
