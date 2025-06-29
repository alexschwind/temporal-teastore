import asyncio
from flask import Flask, render_template, redirect, session, flash, request, make_response, jsonify, current_app
import requests
from math import ceil
import uuid
import random
from temporalio.client import Client
from workflows import ShippingWorkflow, LoginWorkflow, OrderWorkflow
from shared import LoginInput, OrderInput, CartItem, OrderInfo
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "123456789"
app.is_ready = False

async def connect_temporal(app):
    client = await Client.connect("temporal-core:7233")
    app.temporal_client = client
    app.is_ready = True

def get_client() -> Client:
    return current_app.temporal_client

MAX_CACHE_SIZE = 3
category_cache: dict[str, dict] = {}
products_cache: dict[str, list[dict]] = {}

GENERIC_IMAGE_URL = "/static/images/placeholder.png"
def get_images(image_names: list[str]) -> tuple[dict[str, str], list[str]]:
    try:
        query = ",".join(image_names)
        url = f"http://image:5000/api/images?names={query}"
        response = requests.get(url)
        response.raise_for_status()  # Raise error if request failed
        images_list = response.json()
        failed = [name for name in image_names if name not in images_list]
        for name in failed:
            images_list[name] = GENERIC_IMAGE_URL
        return images_list, failed
    except Exception:
        # all failed
        return {name: GENERIC_IMAGE_URL for name in image_names}, image_names

def get_image(image_name) -> tuple[str, bool]:
    try:
        url = f"http://image:5000/api/images?names={image_name}"
        response = requests.get(url)
        response.raise_for_status()  # Raise error if request failed
        images_list = response.json()
        return images_list.get(image_name, GENERIC_IMAGE_URL), True
    except Exception:
        return GENERIC_IMAGE_URL, False
    
@app.route("/retry-image")
def retry_image():
    name = request.args.get("name")
    if not name:
        return jsonify({"error": "No image name provided"}), 400
    image, ok = get_image(name)
    if ok:
        return jsonify({"image": image})
    else:
        return jsonify({"error": "could not load image, returned placeholder"})

def get_recommendations(num=3):
    try:
        response = requests.get(f"http://recommender:5000/api/recommendations?num={num}")
        response.raise_for_status()
        data = response.json()
        return [i for i in data]
    except Exception:
        try:
            # Fallback 1: try to fetch random products
            response = requests.get(f"http://product:5000/api/products")
            response.raise_for_status()
            data = response.json()
            all_products = [p["id"] for p in data]
            return random.sample(all_products, min(num, len(all_products)))
        except Exception:
            # Fallback 2: return random products from products cache
            all_products = []
            for prod_list in products_cache.values():
                all_products.extend(prod_list)
            random_products = random.sample(all_products, min(num, len(all_products)))
            return [p["id"] for p in random_products]
        
def render_template_base(template, **context):
    login = "user_id" in session
    context["login"] = login
    return render_template(template, **context)

@app.before_request
async def ensure_session_id():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        client = get_client()
        await client.start_workflow(
            OrderWorkflow.run, 
            OrderInput(session["session_id"], (session["user_id"] if "user_id" in session else None)),
            id=session["session_id"], task_queue="my-task-queue"
        )
    if "login_pending" in session and session["login_pending"] and "user_id" not in session:
        print("Login is pending")
        client = get_client()
        login_wf_id = f"login:{session['session_id']}"
        try:
            handle = client.get_workflow_handle(login_wf_id)
            result = await handle.result(rpc_timeout=timedelta(milliseconds=500))  # Short timeout
            if result:
                if result["success"]:
                    session["user_id"] = result["user_id"]
                    session["user_data"] = {
                        "realname": result["realname"],
                        "email": result["email"],
                        "username": result["username"],
                    }
                    session.pop("login_pending", None)

                    # signal order workflow that login succeeded
                    order_handle = client.get_workflow_handle(session["session_id"])
                    await order_handle.signal(OrderWorkflow.upgrade_user, result["user_id"])
                    flash("You are logged in now.")
                else:
                    session.pop("login_pending", None)
                    flash("Login failed.")
            
        except Exception:
            # No result yet — login still pending
            pass

    # cache newest 3 user orders in session
    if "user_id" in session and "last_orders" not in session:
        orders: list[dict] = get_user_orders(session["user_id"])
        if orders:
            sorted_orders = sorted(orders, key=lambda x: datetime.strptime(x.get("time"), "%Y-%m-%dT%H:%M:%S.%f"))
            session["last_orders"] = sorted_orders[:3]

def get_category_list():
    try:
        response = requests.get(f"http://product:5000/api/categories")
        response.raise_for_status()  # Raise error if request failed
        data = response.json()

        for category in data:
            category_cache[category["id"]] = category.copy()

        return data
    except Exception:
        return list(category_cache.values())

@app.route("/")
def index():
    category_list = get_category_list()
    return render_template_base("index.html", category_list=category_list)

def get_user(user_id):
    try:
        response = requests.get(f"http://user:5000/api/users/{user_id}")
        response.raise_for_status()  
        data = response.json()
        session["user_data"] = data
        return data
    except Exception:
        return session.get("user_data", None)

def get_user_orders(user_id):
    try:
        response = requests.get(f"http://order:5000/api/orders/{user_id}")
        response.raise_for_status() 
        data = response.json()
        return data
    except:
        return []

@app.route("/profile")
async def profile():

    login = "user_id" in session
    if not login:
        flash("You are not signed in.")
        response = make_response(redirect("/login"))
        response.headers["Referer"] = "/"
        return response

    category_list = get_category_list()

    user_id = session.get("user_id")
    user = get_user(user_id)
    if user is None:
        user = {
            "id": user_id,
            "username": "-",
            "realname": "-",
            "email": "-"
        }
    orders: list[dict] = get_user_orders(user_id)

    if orders:
        sorted_orders = sorted(orders, key=lambda x: datetime.strptime(x.get("time"), "%Y-%m-%dT%H:%M:%S.%f"))
        session["last_orders"] = sorted_orders[:3]
        is_orders_fresh = True
    else:
        if "last_orders" in session:
            orders = session["last_orders"]
        is_orders_fresh = False

    for order in orders:
        if bool(order.get("shipping_done")):
            order["status"] = "Delivered"
        else:
            client = get_client()
            handle = client.get_workflow_handle(order.get("shipping_workflow_id"))
            results = await handle.query(ShippingWorkflow.get_status)
            order["status"] = results.status

    return render_template_base("profile.html", category_list=category_list, user=user, orders=orders, is_orders_fresh=is_orders_fresh)

async def call_login(username, password):
    try:
        if not session.get("login_pending", False):
            client = get_client()
            await client.start_workflow(
                LoginWorkflow.run, 
                LoginInput(username, password),
                id="login:"+session["session_id"], task_queue="my-task-queue"
            )
            session["login_pending"] = True
        
        return True
    except:
        session["login_pending"] = False
        return False

@app.route("/login", methods=["GET", "POST"])
async def login():
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        referer = request.form.get("referer", None)
        if await call_login(username, password):
            flash("Login process started.")
            if referer:
                return redirect(referer)
            return redirect("/")
        else:
            flash('Could not start the login process. Please try again.')
            return render_template_base("login.html")
    
    if "user_id" in session:
        flash("You are already logged in. Please sign out before logging in.")
        return redirect("/")
    
    if session.get("login_pending", False):
        flash("Your login process is still running.")
        return redirect("/")

    category_list = get_category_list()
    referer = request.referrer
    return render_template_base("login.html", referer=referer, category_list=category_list)

def call_logout():
    # also need changes here
    session.pop("session_id")
    session.pop("user_id")
    session.pop("user_data")
    session.pop("login_pending", None)
    return True

@app.route("/logout")
def logout():
    if call_logout():
        flash("You have been logged out.")
        return redirect("/")
    
    flash("Logout failed.")
    return redirect("/")

def get_category(category_id):
    try:
        response = requests.get(f"http://product:5000/api/categories/{category_id}")
        response.raise_for_status()
        data = response.json()
        category_cache[category_id] = data.copy()
        return data
    except Exception:
        return category_cache.get(category_id, None)

def get_products_for_category(category_id):
    try:
        response = requests.get(f"http://product:5000/api/categories/{category_id}/products")
        response.raise_for_status()
        data = response.json()
        products_cache[category_id] = data[:MAX_CACHE_SIZE].copy() # cache 100 items at max per category
        return data
    except Exception:
        return products_cache.get(category_id, None)

@app.route("/category", methods=['GET', 'POST'])
def category():
    if request.method == 'POST':
        selected_number_of_products = request.form['number']
        session["selected_number_of_products"] = selected_number_of_products

    product_number_options = [1, 2, 3, 4, 5]
    page = request.args.get('page', default=1, type=int)
    selected_number_of_products = int(session.get("selected_number_of_products", 3))

    category_id = request.args.get('category', None)
    if not category_id:
        message = {
            "title": "Category not found",
            "text": "No category was provided."
        }
        return render_template_base("error.html", message=message)

    category = get_category(category_id)
    if category is None:
        message = {
            "title": "Category could not be loaded.",
            "text": "There was an error in loading the category."
        }
        return render_template_base("error.html", message=message)
    
    products = get_products_for_category(category_id)
    if products is None:
        message = {
            "title": "Products could not be loaded.",
            "text": "There was an error in loading the products."
        }
        return render_template_base("error.html", message=message)
    products_page = products[(0 + (page-1)*selected_number_of_products):(page*selected_number_of_products)]

    images, failed_images = get_images([p.get("img_name") for p in products_page])
    for p in products_page:
        p["image"] = images.get(p.get("img_name"))

    total_pages = ceil(len(products) / selected_number_of_products)
    pagination = []
    if page > 1:
        pagination.append("previous")
    for n in range(1, total_pages+1):
        pagination.append(n)
    if page < total_pages:
        pagination.append("next")

    category_list = get_category_list()
    return render_template_base("category.html", 
                                category_list=category_list,
                                category=category,
                                products=products_page,
                                pagination=pagination,
                                current_page_number=page,
                                product_number_options=product_number_options,
                                selected_number_of_products=selected_number_of_products,
                                failed_images=failed_images
                                )

def get_product(product_id):
    try:
        response = requests.get(f"http://product:5000/api/products/{product_id}")
        response.raise_for_status()
        data = response.json()
        category_id = data.get("category_id")
        if category_id is not None:
            product_list = products_cache.get(category_id, [])
            product_list = [p for p in product_list if p.get("id") != product_id]
            product_list.append(data)
            if len(product_list) > MAX_CACHE_SIZE:
                product_list = product_list[-MAX_CACHE_SIZE:]
            products_cache[category_id] = product_list
        return data
    except Exception:
        for product_list in products_cache.values():
            for product in product_list:
                if product.get("id") == product_id:
                    return product
        return None

def get_products(product_ids):
    products = []

    for id in product_ids:
        product = get_product(id)
        if product is not None:
            products.append(product)
    
    return products

@app.route("/product")
def product():
    product_id = request.args.get('id', None)
    if not product_id:
        message = {
            "title": "Product not found",
            "text": "No product was provided."
        }
        return render_template_base("error.html", message=message)

    product = get_product(product_id)
    if product is None:
        message = {
            "title": "Product not found",
            "text": "There was an error in finding this product."
        }
        return render_template_base("error.html", message=message)
    
    product_image, product_image_ok = get_image(product.get("img_name"))
    product["image"] = product_image

    ads_ids = get_recommendations()
    ads = get_products(ads_ids)
    ad_images, failed_ad_images = get_images([p.get("img_name") for p in ads])
    for p in ads:
        p["image"] = ad_images[p.get("img_name")]

    failed_images = []
    if not product_image_ok:
        failed_images.append(product.get("img_name"))
    failed_images += failed_ad_images

    category_list = get_category_list()
    return render_template_base("product.html", category_list=category_list, product=product, ads=ads, failed_images=failed_images)

@app.route("/cart")
async def cart():
    client = get_client()
    handle = client.get_workflow_handle(session["session_id"])
    cart_items = await handle.query(OrderWorkflow.get_cart_items)
    products = get_products([i.product_id for i in cart_items])
    products_map = {
        p.get("id") : p for p in products
    }

    ads_ids = get_recommendations()
    ads = get_products(ads_ids)
    ad_images, failed_images = get_images([p.get("img_name") for p in ads])
    for p in ads:
        p["image"] = ad_images[p.get("img_name")]

    category_list = get_category_list()
    return render_template_base("cart.html", category_list=category_list, products=products_map, ads=ads, order_items=cart_items, failed_images=failed_images)

@app.route("/cart/add", methods=["POST"])
async def add_to_cart():
    product_id = request.form.get("productid")
    if product_id is not None:
        client = get_client()
        handle = client.get_workflow_handle(session["session_id"])
        await handle.signal(OrderWorkflow.add_cart_item, product_id)
        flash("Product added to cart.")
        return redirect("/cart")
    else:
        flash("Failed to add product to cart.")
        return redirect("/cart")

@app.route("/update-cart", methods=["POST"])
async def update_cart():
    # remove item
    product_to_remove = request.form.get("remove_item")
    if product_to_remove:
        client = get_client()
        handle = client.get_workflow_handle(session["session_id"])
        await handle.signal(OrderWorkflow.remove_cart_item, product_to_remove)

    # update cart
    all_items = []
    for key, val in request.form.items():
        if key.startswith("quantity_"):
            product_id = key.strip("quantity_")
            all_items.append(CartItem(product_id, int(val)))

    client = get_client()
    handle = client.get_workflow_handle(session["session_id"])
    await handle.signal(OrderWorkflow.update_cart_items, all_items)
    flash("Cart updated.")
    return redirect("/cart")

@app.route("/checkout", methods=["POST"])
def checkout():
    if not "user_id" in session:
        response = make_response(redirect("/login"))
        response.headers["Referer"] = "/cart"
        return response

    return redirect("/order")

@app.route("/order")
async def order():
    client = get_client()
    handle = client.get_workflow_handle(session["session_id"])
    cart_items = await handle.query(OrderWorkflow.get_cart_items)

    if not cart_items:
        flash("You have no items in your cart.")
        return redirect("/cart")

    return render_template_base("order.html")

@app.route("/place_order", methods=["POST"])
async def place_order():
    if "user_id" not in session:
        flash("You are not logged in.")
        return redirect("/cart")
    required_fields = [
        "firstname", "lastname",
        "address1", "address2",
        "cardtype", "cardnumber", "expirydate"
    ]

    # Ensure all fields are present
    for field in required_fields:
        if field not in request.form or not request.form[field].strip():
            flash("Some entries are not provided.")
            return redirect("/order")

    # Extract values
    firstname = request.form["firstname"]
    lastname = request.form["lastname"]
    address1 = request.form["address1"]
    address2 = request.form["address2"]
    cardtype = request.form["cardtype"]
    cardnumber = request.form["cardnumber"]
    expirydate = request.form["expirydate"]

    client = get_client()
    handle = client.get_workflow_handle(session["session_id"])
    await handle.signal(OrderWorkflow.submit, OrderInfo(
        address_name=firstname + " " + lastname,
        address1=address1,
        address2=address2,
        credit_card_company=cardtype,
        credit_card_number=cardnumber,
        credit_card_expiry=expirydate
    ))

    session.pop("session_id")
    return redirect("/")

@app.route('/healthz')
def healthz():
    return jsonify(status="alive"), 200

@app.route('/ready')
def ready():
    if app.is_ready:
        return jsonify(status="ready"), 200
    else:
        return jsonify(status="not ready"), 503

if __name__ == "__main__":
    asyncio.run(connect_temporal(app))
    app.run(debug=True, host="0.0.0.0")