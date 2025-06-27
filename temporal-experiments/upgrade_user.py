import asyncio

from workflows import OrderWorkflow
from temporalio.client import Client


async def main():
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")

    session_id = "12345"
    handle = client.get_workflow_handle(session_id)
    # Execute a workflow
    await handle.signal(OrderWorkflow.upgrade_user, "user_1")

    print(f"User upgraded.")


if __name__ == "__main__":
    asyncio.run(main())