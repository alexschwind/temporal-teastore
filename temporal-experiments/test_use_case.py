import asyncio

from workflows import OrderWorkflow
from temporalio.client import Client
from shared import CartItem, OrderInput, OrderInfo


async def main():
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")

    session_id = "12345"
    data = OrderInput(session_id=session_id, user_id=None)
    # Execute a workflow
    await client.start_workflow(
        OrderWorkflow.run, data, 
        id=session_id, 
        task_queue="my-task-queue", 
    )
    handle = client.get_workflow_handle(session_id)
    await handle.signal(OrderWorkflow.add_cart_item, "1")
    print(f"Product added.")
    await handle.signal(OrderWorkflow.upgrade_user, "1")
    print("User upgraded.")
    await handle.signal(OrderWorkflow.submit, OrderInfo(address_name="Alex", address1="street", address2="city", credit_card_company="penis", credit_card_number="123", credit_card_expiry="today"))
    print(f"Submitted.")


if __name__ == "__main__":
    asyncio.run(main())