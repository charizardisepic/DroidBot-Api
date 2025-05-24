from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

latest_command = "stop"

@app.route('/api/command', methods=['POST'])
def set_command():
    global latest_command
    data = request.get_json()
    latest_command = data.get("command", "stop")
    return jsonify({"status": "received"})

@app.route('/api/command', methods=['GET'])
def get_command():
    return jsonify({"command": latest_command})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)