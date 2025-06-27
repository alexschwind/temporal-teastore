import asyncio

from workflows import OrderWorkflow
from temporalio.client import Client


async def main():
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")

    session_id = "12345"
    handle = client.get_workflow_handle(session_id)
    # Execute a workflow
    results = await handle.query(OrderWorkflow.get_info)

    print(f"Cart info: {results}")


if __name__ == "__main__":
    asyncio.run(main())