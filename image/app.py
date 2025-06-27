import os
import base64
from flask import Flask, jsonify, request

app = Flask(__name__)
IMAGE_FOLDER = "images"

@app.route("/api/images", methods=["GET"])
def get_images_base64():
    names_param = request.args.get("names")
    if not names_param:
        return jsonify({"error": "Missing 'names' parameter"}), 400

    requested_names = [name.strip() for name in names_param.split(",")]
    images_data = {}

    for name in requested_names:
        filepath = os.path.join(IMAGE_FOLDER, name+".png")
        if not os.path.exists(filepath):
            continue  # Skip missing files

        try:
            with open(filepath, "rb") as img_file:
                encoded = base64.b64encode(img_file.read()).decode("utf-8")
                images_data.update({
                    name: f"data:image/png;base64,{encoded}"
                })
        except Exception as e:
            print(f"Failed to read {name}: {e}")

    return jsonify(images_data)