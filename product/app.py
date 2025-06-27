from flask import Flask, request, jsonify, abort
from threading import Lock
import os
import pickle

class Category:
    def __init__(self, id: str, name: str, description: str):
        self.id = id
        self.name = name
        self.description = description

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
        }
    
class Product:
    def __init__(self, id: str, category_id: str, name: str, description: str, price_in_cents: str, img_name: str):
        self.id = id
        self.category_id = category_id
        self.name = name
        self.description = description
        self.price_in_cents = int(price_in_cents)
        self.img_name = img_name

    def to_dict(self):
        return {
            "id": self.id,
            "category_id": self.category_id,
            "name": self.name,
            "description": self.description,
            "price_in_cents": self.price_in_cents,
            "img_name": self.img_name
        }

CATEGORIES_FILE = "categories.pkl"
PRODUCTS_FILE = "products.pkl"

if os.path.exists(CATEGORIES_FILE):
    with open(CATEGORIES_FILE, "rb") as f:
        categories = pickle.load(f)
else:
    categories = [
        Category("1", "Black Tea", "All kinds of black tea"),
        Category("2", "Green Tea", "All kinds of green tea"),
        Category("3", "Herbal Tea", "All kinds of herbal tea"),
        Category("4", "White Tea", "All kinds of white tea"),
        Category("5", "Rooibos Tea", "All kinds of rooibos tea"),
        Category("6", "Infusers", "All kinds of infusers"),
        Category("7", "Tea Cups", "All kinds of cups"),
        Category("8", "Tea Pods", "All kinds of pods"),
    ]

    # Save initial state
    with open(CATEGORIES_FILE, "wb") as f:
        pickle.dump(categories, f)

if os.path.exists(PRODUCTS_FILE):
    with open(PRODUCTS_FILE, "rb") as f:
        products = pickle.load(f)
else:
    products = [
        Product("1", "1", "Darjeeling Classic", "Premium Darjeeling black tea leaves.", "1599", "black-tea"),
        Product("2", "1", "Assam Bold", "Strong and malty Assam tea for mornings.", "1399", "black-tea"),
        Product("3", "1", "Earl Grey", "Black tea with bergamot flavor.", "1499", "black-tea"),
        Product("4", "1", "English Breakfast", "Classic British black tea blend.", "1299", "black-tea"),
        Product("5", "1", "Ceylon Sunrise", "Bright and brisk black tea from Sri Lanka.", "1449", "black-tea"),
        Product("6", "1", "Russian Caravan", "Smoky black tea blend.", "1549", "black-tea"),
        Product("7", "1", "Lapsang Souchong", "Smoked black tea from China.", "1699", "black-tea"),
        Product("8", "2", "Sencha Green", "Traditional Japanese green tea.", "1399", "green-tea"),
        Product("9", "2", "Matcha Powder", "High-grade ceremonial matcha.", "2299", "green-tea"),
        Product("10", "2", "Genmaicha", "Green tea with roasted brown rice.", "1499", "green-tea"),
        Product("11", "2", "Gunpowder Green", "Rolled pellets of Chinese green tea.", "1349", "green-tea"),
        Product("12", "2", "Jasmine Green", "Floral green tea with jasmine petals.", "1499", "green-tea"),
        Product("13", "2", "Dragon Well", "Smooth and nutty Chinese green tea.", "1999", "green-tea"),
        Product("14", "3", "Chamomile Calm", "Soothing herbal tea with chamomile flowers.", "1299", "herbal-tea"),
        Product("15", "3", "Peppermint Pure", "Refreshing peppermint herbal infusion.", "1199", "herbal-tea"),
        Product("16", "3", "Hibiscus Burst", "Tart and vibrant hibiscus petals.", "1399", "herbal-tea"),
        Product("17", "3", "Lemon Ginger", "Zesty and warming herbal blend.", "1499", "herbal-tea"),
        Product("18", "3", "Turmeric Glow", "Spicy turmeric and pepper blend.", "1549", "herbal-tea"),
        Product("19", "3", "Rose Petal Infusion", "Delicate herbal tea with rose petals.", "1449", "herbal-tea"),
        Product("20", "4", "White Peony", "Mild white tea with a floral aroma.", "1799", "white-tea"),
        Product("21", "4", "Silver Needle", "Premium white tea with young buds.", "2299", "white-tea"),
        Product("22", "4", "White Jasmine", "White tea blended with jasmine flowers.", "1899", "white-tea"),
        Product("23", "4", "Peach White", "White tea with natural peach flavor.", "1699", "white-tea"),
        Product("24", "4", "Coconut White", "Tropical twist on white tea.", "1749", "white-tea"),
        Product("25", "5", "Classic Rooibos", "Earthy and smooth caffeine-free tea.", "1399", "rooibos"),
        Product("26", "5", "Vanilla Rooibos", "Sweet vanilla blended with rooibos.", "1499", "rooibos"),
        Product("27", "5", "Spiced Rooibos", "Cinnamon and clove rooibos blend.", "1549", "rooibos"),
        Product("28", "5", "Honeybush Harmony", "Naturally sweet and soothing.", "1399", "rooibos"),
        Product("29", "5", "Citrus Rooibos", "Zesty rooibos with lemon and orange peel.", "1499", "rooibos"),
        Product("30", "6", "Classic Infuser Ball", "Simple steel mesh ball infuser.", "499", "infusers"),
        Product("31", "6", "Silicone Leaf Infuser", "Colorful and fun silicone infuser.", "699", "infusers"),
        Product("32", "6", "Glass Tube Infuser", "Elegant glass tea infuser.", "1299", "infusers"),
        Product("33", "6", "Tea Spoon Infuser", "Scoop and steep tool.", "799", "infusers"),
        Product("34", "6", "Mug Lid Infuser", "Combo infuser and lid for mugs.", "899", "infusers"),
        Product("35", "7", "Porcelain Tea Cup", "Classic white tea cup.", "999", "tea-cups"),
        Product("36", "7", "Double Wall Glass", "Insulated glass cup.", "1299", "tea-cups"),
        Product("37", "7", "Cast Iron Cup", "Heavy-duty cup with Japanese design.", "1499", "tea-cups"),
        Product("38", "7", "Travel Tea Mug", "Spill-proof and insulated.", "1799", "tea-cups"),
        Product("39", "7", "Matcha Bowl", "Ceramic bowl for matcha.", "1999", "tea-cups"),
        Product("40", "8", "Earl Grey Pod", "Convenient pod with black tea and bergamot.", "799", "tea-pots"),
        Product("41", "8", "Green Tea Pod", "Quick-brew green tea pod.", "749", "tea-pots"),
        Product("42", "8", "Chai Spice Pod", "Spicy chai in pod form.", "849", "tea-pots"),
        Product("43", "8", "Mint Herbal Pod", "Refreshing herbal mint in a pod.", "749", "tea-pots"),
        Product("44", "8", "Peach White Pod", "Light white tea with peach.", "849", "tea-pots"),
        Product("45", "8", "Rooibos Vanilla Pod", "Sweet rooibos pod blend.", "799", "tea-pots"),
        Product("46", "2", "Iced Green Tea", "Cold brew green tea option.", "1399", "green-tea"),
        Product("47", "3", "Herbal Detox", "Cleansing herbal tea blend.", "1499", "herbal-tea"),
        Product("48", "4", "Berry White", "White tea with berry flavors.", "1599", "white-tea"),
        Product("49", "5", "Rooibos Latte Mix", "Rooibos blend for lattes.", "1699", "rooibos"),
        Product("50", "6", "Infuser Mug Set", "Mug with built-in infuser.", "1999", "infusers"),
    ]

    # Save initial state
    with open(PRODUCTS_FILE, "wb") as f:
        pickle.dump(products, f)

lock = Lock()

def find_by_id(items, id):
    return next((item for item in items if item.id == id), None)

def next_id(items):
    return max((item.id for item in items), default=0) + 1

app = Flask(__name__)

@app.route("/api/categories", methods=["GET"])
def get_categories():
    return jsonify([c.to_dict() for c in categories])

@app.route("/api/products", methods=["GET"])
def get_products():
    with lock:
        result = [p.to_dict() for p in products]
    return jsonify(result)

@app.route("/api/categories/<id>", methods=["GET"])
def get_category(id):
    with lock:
        category = find_by_id(categories, id)

    if category:
        return jsonify(category.to_dict())
    abort(404)

@app.route("/api/categories/<id>/products", methods=["GET"])
def get_products_by_category(id):
    with lock:
        matched_category = find_by_id(categories, id)

    if not matched_category:
        abort(404, description=f"Category with id {id} not found.")
    with lock:
        filtered_products = [p.to_dict() for p in products if p.category_id == id]
    return jsonify(filtered_products)

@app.route("/api/products/<id>", methods=["GET"])
def get_product(id):
    with lock:
        product = find_by_id(products, id)
    if product:
        return jsonify(product.to_dict())
    abort(404)

@app.route("/api/products/bulk", methods=["POST"])
def get_products_bulk():
    data = request.get_json()
    if not data or "ids" not in data:
        abort(400, description="Missing 'ids' in request body")

    ids = data["ids"]

    with lock:
        result = [p.to_dict() for p in products if p.id in ids]
    return jsonify(result)