import requests
from dataclasses import dataclass
from temporalio import activity
import random
import uuid

from shared import CartItem, OrderInfo, StoreOrderItemsInput, EmailInput, ReservationInput

### ORDER ###

@dataclass
class NotEnoughInventoryError(Exception):
    def __init__(self, message) -> None:
        self.message: str = message
        super().__init__(self.message)

@dataclass
class NotEnoughFundsPaymentError(Exception):
    def __init__(self, message) -> None:
        self.message: str = message
        super().__init__(self.message)

@activity.defn
async def reserve_items(input: ReservationInput):
    payload = {
        "product_ids": [item.product_id for item in input.cart_items],
        "quantities": [item.quantity for item in input.cart_items],
        "reservation_id": input.reservation_id
    }
    resp = requests.post("http://inventory:5000/api/inventory/check_and_reserve", json=payload)
    if 400 <= resp.status_code < 500:
        data: dict = resp.json()
        raise ValueError(data.get("error"))
    if resp.status_code >= 500:
        raise NotEnoughInventoryError("We dont have enough inventory.")

@activity.defn
async def release_items(reservation_id: str):
    payload = {
        "reservation_id": reservation_id
    }
    resp = requests.post("http://inventory:5000/api/inventory/release", json=payload)
    resp.raise_for_status()

@activity.defn
async def get_total_price(cart_items: list[CartItem]) -> int:
    product_ids = [i.product_id for i in cart_items]
    resp = requests.post("http://product:5000/api/products/bulk", json={"ids": product_ids})
    resp.raise_for_status()
    products = resp.json()
    price_map = {str(p["id"]): int(p["price_in_cents"]) for p in products}
    total_price = sum(item.quantity * price_map[item.product_id] for item in cart_items)
    return total_price

@activity.defn
async def simulate_payment(order_info: OrderInfo):
    success = random.randint(1, 100) <= 90
    if success:
        print(f"✅ Payment successful for user {order_info.user_id}, amount: {order_info.total_price} cents")
    else:
        print(f"❌ Payment failed for user {order_info.user_id}, amount: {order_info.total_price} cents")
        raise NotEnoughFundsPaymentError("Not enough money in the bank.")

@activity.defn
async def store_order(order_info: OrderInfo) -> str:
    order_data = {
        "id": order_info.order_id,
        "user_id": order_info.user_id,
        "total_price_in_cents": order_info.total_price,
        "address_name": order_info.address_name,
        "address1": order_info.address1,
        "address2": order_info.address2,
        "credit_card_company": order_info.credit_card_company,
        "credit_card_number": order_info.credit_card_number,
        "credit_card_expiry": order_info.credit_card_expiry,
        "shipping_workflow_id": "shipping:"+order_info.session_id
    }

    response = requests.post("http://order:5000/api/orders", json=order_data)
    if response.status_code == 409:
        # Already exists — consider this a success
        return "already_exists"
    response.raise_for_status()
    return "created"

@activity.defn
async def store_order_items(input: StoreOrderItemsInput):
    for item, id in zip(input.cart_items, input.order_items_ids):
        order_item_data = {
            "id": id,
            "product_id": item.product_id,
            "order_id": input.info.order_id,  
            "quantity": item.quantity
        }

        response = requests.post("http://order:5000/api/orderitems", json=order_item_data)
        if response.status_code == 409:
            continue

        response.raise_for_status()

@activity.defn
async def get_user_email(order_info: OrderInfo) -> str:
    user_resp = requests.get(f"http://user:5000/api/users/{order_info.user_id}")
    user_resp.raise_for_status()
    user_data = user_resp.json()
    email = user_data.get("email", None)  # fallback email
    if email is None:
        raise ValueError("No email received")
    
    return email

@activity.defn
async def send_email(input: EmailInput):
    activity.logger.info("Sending email to: ", input.address, "\nHeader: ", input.header, "\nMessage: ", input.message)

### SHIPPING ###

@activity.defn
async def set_shipping_done(order_id: str):
    payload = {
        "shipping_done": True
    }
    response = requests.post(f"http://order:5000/api/orders/{order_id}/shipping_done", json=payload)
    response.raise_for_status()

### RECOMMENDER ###

@activity.defn
async def get_order_items():
    response = requests.get("http://order:5000/api/orderitems")
    response.raise_for_status()
    order_items = response.json()
    return order_items

@activity.defn
async def compute_popular_item_ranking(order_items):
    counts = {}
    for item in order_items:
        p_id = item.get("product_id")
        counts[p_id] = counts.get(p_id, 0) + item.get("quantity", 1)
    
    counts = sorted(counts.items(), key=lambda x: x[1])
    counts = [x[0] for x in counts]
    return counts

@activity.defn
async def set_recommendations(counts):
    response = requests.post("http://recommender:5000/api/recommendations", json=counts)
    response.raise_for_status()

### LOGIN ###
@activity.defn
async def get_user(username: str):
    resp = requests.get(f"http://user:5000/api/users/username/{username}")
    resp.raise_for_status()
    user_data = resp.json()
    return user_data
