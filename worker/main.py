import asyncio
import os
import time
import redis.asyncio as redis
from temporalio.client import Client
from temporalio.worker import Worker
from prometheus_client import start_http_server, Counter, Histogram
import logging

from temporal_workflows import OptimizeQueryWorkflow, execute_langgraph_agent

EVENTS_PROCESSED = Counter('agent_events_processed_total', 'Total slow query events processed')
AGENT_LOOP_DURATION = Histogram('agent_loop_duration_seconds', 'Time spent in the optimization loop',
                                buckets=[1, 2.5, 5, 10, 30, 60, 120, 300])

async def main():
    logging.basicConfig(level=logging.INFO)
    start_http_server(8000)
    logging.info("Prometheus metrics server running on port 8000")

    temporal_client = await Client.connect(
        os.getenv("TEMPORAL_HOST", "localhost:7233")
    )

    worker = Worker(
        temporal_client,
        task_queue="agent-task-queue",
        workflows=[OptimizeQueryWorkflow],
        activities=[execute_langgraph_agent],
        max_concurrent_activities=5,
    )

    worker_task = asyncio.create_task(worker.run())
    logging.info("Temporal Agent Worker started. Polling task queue 'agent-task-queue'.")

    redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

    try:
        await redis_client.xgroup_create("slow_queries", "agent_workers", id="0", mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise e

    logging.info("Listening to Redis stream 'slow_queries'...")

    while True:
        try:
            messages = await redis_client.xreadgroup(
                "agent_workers",
                "worker-1",
                {"slow_queries": ">"},
                count=1,
                block=1000,
            )

            if messages:
                for stream, msg_list in messages:
                    for msg_id, msg_data in msg_list:
                        payload_json = msg_data.get(b"full_payload", b"{}").decode("utf-8")
                        tenant_id = msg_data.get(b"tenant_id", b"unknown").decode("utf-8")

                        logging.info(f"Received event {msg_id} for tenant {tenant_id}. Starting Workflow.")

                        loop_start = time.time()

                        await temporal_client.start_workflow(
                            OptimizeQueryWorkflow.run,
                            payload_json,
                            id=f"optimize-{tenant_id}-{msg_id.decode('utf-8')}",
                            task_queue="agent-task-queue",
                        )

                        loop_duration = time.time() - loop_start
                        AGENT_LOOP_DURATION.observe(loop_duration)

                        await redis_client.xack("slow_queries", "agent_workers", msg_id)
                        EVENTS_PROCESSED.inc()

                        logging.info(f"Workflow started for tenant {tenant_id} in {loop_duration:.2f}s")

        except Exception as e:
            logging.error(f"Error in ingestion loop: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
