import asyncio

from workflows import OrderWorkflow
from temporalio.client import Client
from shared import CartItem


async def main():
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")

    session_id = "12345"
    handle = client.get_workflow_handle(session_id)
    new_cart_items = [CartItem(product_id="product_1", quantity=5)]
    # Execute a workflow
    await handle.signal(OrderWorkflow.update_cart_items, new_cart_items)

    print(f"Cart updated.")


if __name__ == "__main__":
    asyncio.run(main())