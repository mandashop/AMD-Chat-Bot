from flask import Flask, jsonify
from config import config

app = Flask(__name__)

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"status": "ok", "message": "Bot server is running!"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=config.PORT)
