import asyncio
from temporalio.client import Client
from workflows import RecommendationWorkflow 

async def main():
    await asyncio.sleep(5)
    client = await Client.connect("temporal-core:7233")
    print("Starting recommendation workflow...")
    await client.start_workflow(
        RecommendationWorkflow.run,
        id="recommendations",
        task_queue="my-task-queue",
    )
    print("Workflow started.")

if __name__ == "__main__":
    asyncio.run(main())