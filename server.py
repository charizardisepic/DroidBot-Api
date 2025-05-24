from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from collections import deque
import threading
import time

app = Flask(__name__)
CORS(app)

# Command queue to store multiple commands
command_queue = deque()
queue_lock = threading.Lock()

# Current command being executed (for ESP32 to fetch)
current_command = "stop"
command_lock = threading.Lock()

@app.route('/')
def index():
    """Web interface with buttons for robot control"""
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Robot Controller</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 20px; }
            .button-grid { display: inline-block; margin: 20px; }
            .control-btn { 
                width: 80px; height: 80px; margin: 5px; 
                font-size: 16px; font-weight: bold;
                border: 2px solid #333; border-radius: 10px;
                cursor: pointer; background: #f0f0f0;
            }
            .control-btn:hover { background: #ddd; }
            .control-btn:active { background: #bbb; }
            #queue-display { 
                margin: 20px; padding: 10px; 
                border: 1px solid #ccc; border-radius: 5px;
                background: #f9f9f9; min-height: 50px;
            }
            .clear-btn { 
                background: #ff6b6b; color: white; 
                border: none; padding: 10px 20px; 
                border-radius: 5px; cursor: pointer; margin: 10px;
            }
        </style>
    </head>
    <body>
        <h1>🤖 Robot Controller</h1>
        
        <div class="button-grid">
            <div>
                <button class="control-btn" onclick="addCommand('F')">↑<br>Forward</button>
            </div>
            <div>
                <button class="control-btn" onclick="addCommand('L')">←<br>Left</button>
                <button class="control-btn" onclick="addCommand('S')">⏹<br>Stop</button>
                <button class="control-btn" onclick="addCommand('R')">→<br>Right</button>
            </div>
            <div>
                <button class="control-btn" onclick="addCommand('B')">↓<br>Reverse</button>
            </div>
        </div>
        
        <div>
            <button class="clear-btn" onclick="clearQueue()">Clear Queue</button>
        </div>
        
        <div id="queue-display">
            <h3>Command Queue:</h3>
            <div id="queue-content">Empty</div>
        </div>
        
        <div id="status"></div>

        <script>
            function addCommand(cmd) {
                fetch('/api/queue', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({command: cmd})
                })
                .then(response => response.json())
                .then(data => {
                    updateDisplay();
                    document.getElementById('status').innerHTML = 
                        `<p style="color: green;">Added: ${cmd}</p>`;
                })
                .catch(error => {
                    document.getElementById('status').innerHTML = 
                        `<p style="color: red;">Error: ${error}</p>`;
                });
            }
            
            function clearQueue() {
                fetch('/api/queue', {method: 'DELETE'})
                .then(response => response.json())
                .then(data => {
                    updateDisplay();
                    document.getElementById('status').innerHTML = 
                        `<p style="color: blue;">Queue cleared</p>`;
                });
            }
            
            function updateDisplay() {
                fetch('/api/queue')
                .then(response => response.json())
                .then(data => {
                    const queueContent = document.getElementById('queue-content');
                    if (data.queue.length === 0) {
                        queueContent.innerHTML = 'Empty';
                    } else {
                        queueContent.innerHTML = data.queue.join(' → ');
                    }
                });
            }
            
            // Update display every 2 seconds
            setInterval(updateDisplay, 2000);
            updateDisplay(); // Initial load
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template)

@app.route('/api/queue', methods=['POST'])
def add_to_queue():
    """Add a command to the queue"""
    global command_queue
    data = request.get_json()
    command = data.get("command", "").upper()
    
    # Validate command
    valid_commands = ['F', 'B', 'L', 'R', 'S']
    if command not in valid_commands:
        return jsonify({"error": "Invalid command"}), 400
    
    with queue_lock:
        command_queue.append(command)
    
    return jsonify({
        "status": "added", 
        "command": command,
        "queue_length": len(command_queue)
    })

@app.route('/api/queue', methods=['GET'])
def get_queue():
    """Get current queue status"""
    with queue_lock:
        queue_list = list(command_queue)
    
    return jsonify({
        "queue": queue_list,
        "length": len(queue_list)
    })

@app.route('/api/queue', methods=['DELETE'])
def clear_queue():
    """Clear the command queue"""
    global command_queue
    with queue_lock:
        command_queue.clear()
    
    return jsonify({"status": "cleared"})

@app.route('/api/command', methods=['GET'])
def get_command():
    """ESP32 endpoint - get next command from queue"""
    global current_command, command_queue
    
    with queue_lock:
        if command_queue:
            next_command = command_queue.popleft()
            with command_lock:
                current_command = next_command
        else:
            with command_lock:
                current_command = "stop"
    
    return jsonify({"command": current_command})

@app.route('/api/command', methods=['POST'])
def set_command():
    """Legacy endpoint - directly set command (also adds to queue)"""
    data = request.get_json()
    command = data.get("command", "stop").upper()
    
    # Add to queue instead of direct set
    valid_commands = ['F', 'B', 'L', 'R', 'S']
    if command.upper() in valid_commands:
        with queue_lock:
            command_queue.append(command)
        return jsonify({"status": "added_to_queue"})
    
    return jsonify({"status": "invalid_command"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
