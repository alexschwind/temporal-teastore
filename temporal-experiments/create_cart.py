import asyncio

from workflows import OrderWorkflow
from temporalio.client import Client
from shared import OrderInput


async def main():
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")

    session_id = "12345"
    # user not logged in yet
    data = OrderInput(session_id=session_id, user_id=None)

    # Execute a workflow
    await client.execute_workflow(
        OrderWorkflow.run, data, id=session_id, task_queue="my-task-queue"
    )

    print(f"Cart successfully created.")


if __name__ == "__main__":
    asyncio.run(main())