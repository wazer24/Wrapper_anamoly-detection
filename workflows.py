from render_sdk import Workflows, Retry

app = Workflows()

@app.task
def calculate_square(n: int) -> int:
    return n * n

@app.task(
    name="process_claim",
    retry=Retry(max_retries=3, wait_duration_ms=1000, backoff_scaling=1.5),
    timeout_seconds=300,
    plan="standard",
)
def process_claim(claim: dict):
    result = calculate_square(claim["value"])
    return {"claim_id": claim["id"], "result": result}

if __name__ == "__main__":
    app.start()
