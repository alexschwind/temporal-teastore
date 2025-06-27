import asyncio

from workflows import OrderWorkflow
from temporalio.client import Client
from shared import OrderInfo


async def main():
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")

    session_id = "12345"
    handle = client.get_workflow_handle(session_id)
    # Execute a workflow
    await handle.signal(OrderWorkflow.submit, OrderInfo(address_name="Alex", address1="street", address2="city", credit_card_company="penis", credit_card_number="123", credit_card_expiry="today"))
    print(f"Cart updated.")


if __name__ == "__main__":
    asyncio.run(main())