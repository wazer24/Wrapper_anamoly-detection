import os
os.environ['GEMINI_API_KEY'] = 'dummy'
from agent_tools.langgraph_agent import agent_app
initial_state = {
    'tenant_id': 'test_tenant',
    'query_text': 'Prisma customer.findUnique({""where"":{""customerId"":123}})',
    'params': {},
    'duration_ms': '5.5',
    'schema_context': '',
    'table_stats': {},
    'explain_plan': {},
    'hypotheses': [],
    'current_iteration': 0,
    'memory_match_found': False,
    'memory_match_id': None,
    'proposed_fix': '',
    'validated_cost_reduction': 0.0,
    'risk_level': 0,
    'approval_status': 'PENDING',
    'approval_request_id': None,
}
thread_config = {'configurable': {'thread_id': 'debug-1'}}
final_state = agent_app.invoke(initial_state, thread_config)
print('Final state:')
for k, v in final_state.items():
    print(f'  {k}: {v}')
