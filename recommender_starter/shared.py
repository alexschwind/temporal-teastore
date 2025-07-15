from dataclasses import dataclass

@dataclass
class CartItem:
    product_id: str
    quantity: int

@dataclass
class OrderInfo:
    session_id: str = ""
    user_id: str | None = None
    address_name: str = ""
    address1: str = ""
    address2: str = ""
    credit_card_company: str = ""
    credit_card_number: str = ""
    credit_card_expiry: str = ""
    total_price: int = -1
    order_id: str | None = None

@dataclass
class OrderInput:
    session_id: str
    user_id: str | None

@dataclass
class StoreOrderItemsInput:
    info: OrderInfo
    cart_items: list[CartItem]
    order_items_ids: list[str]

@dataclass
class EmailInput:
    address: str
    header: str
    message: str

@dataclass
class ShippingInfo:
    status: str = "Processing"
    expected_days: int = 3

@dataclass
class LoginInput:
    username: str
    password: str

@dataclass
class LoginOutput:
    success: bool
    user_id: str
    username: str
    realname: str
    email: str

@dataclass
class ReservationInput:
    reservation_id: str
    cart_items: list[CartItem]