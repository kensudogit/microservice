from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # CORSを有効にする

# ダミーデータを返すエンドポイント
@app.route('/api/property', methods=['GET'])
def get_properties():
    properties = [
        {"id": 1, "name": "Property 1", "location": "Location 1", "price": 100000},
        {"id": 2, "name": "Property 2", "location": "Location 2", "price": 150000}
    ]
    return jsonify(properties)

if __name__ == '__main__':
    app.run(debug=True)
