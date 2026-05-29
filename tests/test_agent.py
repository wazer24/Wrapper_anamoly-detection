import json
import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_tools.langgraph_agent import agent_app


def load_golden_dataset():
    dataset_path = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
    with open(dataset_path, "r") as f:
        return json.load(f)


@pytest.mark.parametrize("test_case", load_golden_dataset(), ids=lambda tc: tc["id"])
def test_agent_golden_dataset(test_case):
    initial_state = {
        "tenant_id": test_case["input_payload"]["tenant_id"],
        "query_text": test_case["input_payload"]["query_text"],
        "params": json.loads(test_case["input_payload"]["params"]),
        "duration_ms": test_case["input_payload"]["duration_ms"],
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

    thread_config = {"configurable": {"thread_id": f"test-{test_case['id']}"}}
    final_state = agent_app.invoke(initial_state, thread_config)

    assert "current_iteration" in final_state
    assert final_state.get("current_iteration", 0) >= 1

    assert final_state.get("validated_cost_reduction", 0.0) >= test_case.get("expected_min_cost_reduction", 10.0)

    if "expected_risk_level" in test_case:
        assert final_state.get("risk_level", 0) == test_case["expected_risk_level"]

    assert final_state.get("proposed_fix", "") != "", f"Test {test_case['id']} should produce a proposed_fix"

    print(f"Test {test_case['id']} passed: risk={final_state.get('risk_level')}, reduction={final_state.get('validated_cost_reduction'):.1f}%")
