from prefect import flow
from pathlib import Path

source=str(Path.cwd())
entrypoint = "forecast.py:forecast_both_pipeline" 
print(f'entrypoint:{entrypoint}, source:{source}')

if __name__ == "__main__":
    flow.from_source(
        source=source,
        entrypoint=entrypoint,
    ).deploy(
        name="forecast_deployment",
        parameters={},
        work_pool_name="default-agent-pool",
        cron="27 * * * *",  
    )
