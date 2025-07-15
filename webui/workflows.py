
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
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
        get_user,
    )
    from shared import (
        OrderInfo, 
        CartItem, 
        OrderInput, 
        StoreOrderItemsInput, 
        EmailInput, 
        ShippingInfo, 
        LoginInput, 
        LoginOutput,
        ReservationInput
    )


@workflow.defn
class OrderWorkflow:
    def __init__(self) -> None:
        self.info = OrderInfo()
        self.cart_items: list[CartItem] = []
        self.submitted = False
    
    @workflow.run
    async def run(self, data: OrderInput):
        self.info.session_id = data.session_id
        self.info.user_id = data.user_id

        await workflow.wait_condition(
            lambda: self.submitted and workflow.all_handlers_finished()
        )

        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=5),
            non_retryable_error_types=["NotEnoughInventoryError", "NotEnoughFundsPaymentError"],
        )

        # Start order processing, since the user submitted the form.
        reservation_id = str(workflow.uuid4())
        # 1. Check + reserve inventory
        await workflow.execute_activity(
            reserve_items, ReservationInput(reservation_id, self.cart_items),
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=retry_policy,
        )

        # 2. Get product prices and calculate total price
        total_price: int = await workflow.execute_activity(
            get_total_price, self.cart_items,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=retry_policy,
        )

        self.info.total_price = total_price

        # 3. Simulate payment
        try:
            await workflow.execute_activity(
                simulate_payment, self.info,
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=retry_policy,
            )
        except ActivityError as e:
            # try to release the items, if it fails we return this error.
            await workflow.execute_activity(
                release_items, reservation_id,
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=retry_policy,
            )
            raise e

        # 4. Store order
        self.info.order_id = str(workflow.uuid4())
        result = await workflow.execute_activity(
            store_order, self.info,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=retry_policy,
        )
        workflow.logger.info(f"Order creation result: {result}")

        # 5. Store order items
        order_items_ids=[str(workflow.uuid4()) for _ in self.cart_items]
        await workflow.execute_activity(
            store_order_items, StoreOrderItemsInput(
                info=self.info, 
                cart_items=self.cart_items,
                order_items_ids=order_items_ids
            ),
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=retry_policy,
        )

        # 6. Send message to recommendation workflow
        handle = workflow.get_external_workflow_handle("recommendations")
        await handle.signal(RecommendationWorkflow.start)

        # 7. Send email notification
        user_mail_address = await workflow.execute_activity(
            get_user_email, self.info,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=retry_policy,
        )

        await workflow.execute_activity(
            send_email, EmailInput(address=user_mail_address, header="Thank you for your order!", message=f"Hi {self.info.address_name}, thank you for your order #{self.info.order_id}."),
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=retry_policy,
        )

        # 6. Dispatch shipping workflow
        await workflow.execute_child_workflow(
            ShippingWorkflow.run, self.info.order_id,
            id="shipping:"+self.info.session_id,
            task_queue="my-task-queue",
        )

        # After the user submitted the form we have to set a new session_id for the user so 
        # it can create a new order workflow. 
        # since this one is still runnning.

    ### INFO OPERATIONS ###
    @workflow.query
    def get_info(self) -> OrderInfo:
        return self.info
    
    @workflow.signal
    def upgrade_user(self, user_id: str):
        if not self.submitted:
            self.info.user_id = user_id

    @workflow.signal
    def submit(self, new_info: OrderInfo):
        if not self.submitted:
            self.info.address_name = new_info.address_name
            self.info.address1 = new_info.address1
            self.info.address2 = new_info.address2
            self.info.credit_card_company = new_info.credit_card_company
            self.info.credit_card_number = new_info.credit_card_number
            self.info.credit_card_expiry = new_info.credit_card_expiry

            if self.info.user_id is not None and self.info.user_id != "":
                self.submitted = True

    ### CART ITEM OPERATIONS ###
    @workflow.query
    def get_cart_items(self) -> list[CartItem]:
        return self.cart_items
    
    @workflow.signal
    def add_cart_item(self, product_id: str):
        if not self.submitted:
            for item in self.cart_items:
                if item.product_id == product_id:
                    item.quantity += 1
                    return
                
            self.cart_items.append(CartItem(product_id=product_id, quantity=1))

    @workflow.signal
    def remove_cart_item(self, product_id: str):
        if not self.submitted:
            self.cart_items = [item for item in self.cart_items if item.product_id != product_id]

    @workflow.signal
    def update_cart_items(self, cart_items: list[CartItem]):
        if not self.submitted:
            for old_item in self.cart_items:
                # find item that corresponds to this item in the cart
                new_item = next((item for item in cart_items if item.product_id == old_item.product_id), None)
                if new_item is not None:
                    old_item.quantity = new_item.quantity

@workflow.defn
class ShippingWorkflow:
    def __init__(self) -> None:
        self.order_id: str|None = None
        self.info: ShippingInfo = ShippingInfo()
        self.done = False
    
    @workflow.run
    async def run(self, order_id: str):
        self.order_id = order_id

        await workflow.sleep(timedelta(seconds=10))

        self.info.status = "Shipping"

        await workflow.sleep(timedelta(seconds=10))

        self.info.status = "Shipped"

        self.done = True

        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=5),
        )
        
        await workflow.execute_activity(
            set_shipping_done, self.order_id,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=retry_policy,
        )

    @workflow.query
    def get_status(self) -> ShippingInfo:
        return self.info
    
@workflow.defn
class RecommendationWorkflow:
    def __init__(self):
        self.do_run = True

    @workflow.run
    async def run(self):

        await workflow.sleep(timedelta(seconds=30))

        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=5),
        )

        order_items = await workflow.execute_activity(
            get_order_items,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=retry_policy,
        )

        counts = await workflow.execute_activity(
            compute_popular_item_ranking, order_items,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=retry_policy,
        )

        await workflow.execute_activity(
            set_recommendations, counts,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=retry_policy,
        )

        while True:
            await workflow.wait_condition(
                lambda: self.do_run and workflow.all_handlers_finished()
            )

            order_items = await workflow.execute_activity(
                get_order_items,
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=retry_policy,
            )

            counts = await workflow.execute_activity(
                compute_popular_item_ranking, order_items,
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=retry_policy,
            )

            await workflow.execute_activity(
                set_recommendations, counts,
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=retry_policy,
            )

            self.do_run = False
    
    @workflow.signal
    def start(self):
        self.do_run = True

@workflow.defn
class LoginWorkflow:
    @workflow.run
    async def run(self, input: LoginInput):

        retry_policy = RetryPolicy(
            maximum_interval=timedelta(seconds=3)
        )

        try:

            user = await workflow.execute_activity(
                get_user, input.username,
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=retry_policy,
            )

            if user.get("password") == input.password:
                return LoginOutput(True, user.get("id"), user.get("username"), user.get("realname"), user.get("email"))
            else:
                return LoginOutput(False, "", "", "", "")
        except ActivityError:
            return LoginOutput(False, "", "", "", "")