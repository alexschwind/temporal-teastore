import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from activities import (
    reserve_items, 
    release_items,
    get_total_price, 
    simulate_payment, 
    store_order, 
    store_order_items,
    get_user_email,
    send_email,
    set_shipping_done,
    get_order_items,
    compute_popular_item_ranking,
    set_recommendations,
    get_user
)
from workflows import OrderWorkflow, ShippingWorkflow, RecommendationWorkflow, LoginWorkflow


async def main() -> None:
    await asyncio.sleep(5)
    client: Client = await Client.connect("temporal-core:7233", namespace="default")

    # Run the worker
    worker: Worker = Worker(
        client,
        task_queue="my-task-queue",
        workflows=[OrderWorkflow, ShippingWorkflow, RecommendationWorkflow, LoginWorkflow],
        activities=[
            reserve_items, 
            release_items,
            get_total_price, 
            simulate_payment, 
            store_order, 
            store_order_items,
            get_user_email,
            send_email,
            set_shipping_done,
            get_order_items,
            compute_popular_item_ranking,
            set_recommendations,
            get_user
        ],
    )
    print("Starting worker.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())