import asyncio
import json
import logging
import uuid
from datetime import timedelta
from temporalio import activity, workflow
from temporalio.common import RetryPolicy
import pybreaker
from opentelemetry import trace

tracer = trace.get_tracer(__name__)
llm_breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=300)


async def _build_initial_state(payload: dict) -> dict:
    return {
        "tenant_id": payload.get("tenant_id", "unknown"),
        "query_text": payload.get("query_text", ""),
        "params": json.loads(payload.get("params", "{}")),
        "duration_ms": payload.get("duration_ms", "0"),
        "schema_context": "",
        "table_stats": {},
        "explain_plan": {},
        "hypotheses": [],
        "current_iteration": 0,
        "memory_match_found": False,
        "memory_match_id": None,
        "proposed_fix": "",
        "validated_cost_reduction": 0.0,
        "risk_level": 0,
        "approval_status": "PENDING",
        "approval_request_id": None,
    }


@activity.defn(retry_policy=RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=15),
    maximum_attempts=3,
))
async def execute_langgraph_first_pass(payload_json: str) -> str:
    payload = json.loads(payload_json)
    tenant_id = payload.get("tenant_id", "unknown")

    with tracer.start_as_current_span("execute_langgraph_first_pass") as span:
        span.set_attribute("tenant_id", tenant_id)
        span.set_attribute("query_text", payload.get("query_text", ""))

        logging.info("[Tenant %s] Starting LangGraph first pass.", tenant_id)

        try:
            from agent_tools.langgraph_agent import agent_app, write_memory

            thread_id = str(uuid.uuid4())
            thread_config = {"configurable": {"thread_id": thread_id}}
            initial_state = await _build_initial_state(payload)

            final_state = await asyncio.to_thread(agent_app.invoke, initial_state, thread_config)

            # Check if graph was interrupted (human-in-the-loop approval needed)
            state_snapshot = agent_app.get_state(thread_config)
            if state_snapshot and state_snapshot.next:
                request_id = final_state.get("approval_request_id", -1)
                logging.info(
                    "[Tenant %s] Graph interrupted at %s. Approval request_id=%s, thread_id=%s",
                    tenant_id, state_snapshot.next, request_id, thread_id,
                )
                return json.dumps({
                    "status": "interrupted",
                    "tenant_id": tenant_id,
                    "thread_id": thread_id,
                    "approval_request_id": request_id,
                    "proposed_fix": final_state.get("proposed_fix", "")[:200],
                    "risk_level": final_state.get("risk_level", 0),
                })

            write_memory(final_state)
            return json.dumps({
                "status": "completed",
                "tenant_id": tenant_id,
                "risk_level": final_state.get("risk_level"),
                "validated_cost_reduction": final_state.get("validated_cost_reduction"),
                "proposed_fix": final_state.get("proposed_fix", "")[:200],
                "iterations": final_state.get("current_iteration", 0),
            })

        except Exception as e:
            logging.error("[Tenant %s] LangGraph first pass failed: %s", tenant_id, e)
            return json.dumps({"status": "failed", "tenant_id": tenant_id, "error": str(e)})


@activity.defn
async def execute_langgraph_resume(resume_payload: str) -> str:
    data = json.loads(resume_payload)
    thread_id = data["thread_id"]
    approved = data["approved"]
    tenant_id = data.get("tenant_id", "unknown")

    with tracer.start_as_current_span("execute_langgraph_resume") as span:
        span.set_attribute("tenant_id", tenant_id)
        span.set_attribute("thread_id", thread_id)
        span.set_attribute("approved", str(approved))

        logging.info("[Tenant %s] Resuming LangGraph (thread=%s, approved=%s)", tenant_id, thread_id, approved)

        try:
            from agent_tools.langgraph_agent import agent_app, write_memory
            from langgraph.types import Command

            thread_config = {"configurable": {"thread_id": thread_id}}
            final_state = await asyncio.to_thread(
                agent_app.invoke,
                Command(resume={"status": "APPROVED" if approved else "DENIED"}),
                thread_config,
            )
            write_memory(final_state)

            return json.dumps({
                "status": "completed",
                "tenant_id": tenant_id,
                "risk_level": final_state.get("risk_level"),
                "validated_cost_reduction": final_state.get("validated_cost_reduction"),
                "proposed_fix": final_state.get("proposed_fix", "")[:200],
                "iterations": final_state.get("current_iteration", 0),
                "approval_status": final_state.get("approval_status", ""),
            })

        except Exception as e:
            logging.error("[Tenant %s] LangGraph resume failed: %s", tenant_id, e)
            return json.dumps({"status": "failed", "tenant_id": tenant_id, "error": str(e)})


@workflow.defn
class OptimizeQueryWorkflow:
    def __init__(self) -> None:
        self._approved: bool | None = None

    @workflow.signal
    async def approve_signal(self, approved: bool) -> None:
        self._approved = approved

    @workflow.run
    async def run(self, payload_json: str) -> str:
        result = await workflow.execute_activity(
            execute_langgraph_first_pass,
            payload_json,
            start_to_close_timeout=timedelta(minutes=2),
        )
        result_data = json.loads(result)

        if result_data.get("status") == "interrupted":
            request_id = result_data.get("approval_request_id", -1)
            workflow.logger.info(
                "Workflow interrupted, waiting for approval signal (request_id=%s)", request_id
            )

            await workflow.wait_condition(
                lambda: self._approved is not None,
                timeout=timedelta(hours=24),
            )

            resume_payload = json.dumps({
                "thread_id": result_data["thread_id"],
                "approved": self._approved,
                "tenant_id": result_data.get("tenant_id", "unknown"),
            })

            result = await workflow.execute_activity(
                execute_langgraph_resume,
                resume_payload,
                start_to_close_timeout=timedelta(minutes=2),
            )

        return result
