import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import subprocess
import psutil

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])
socketio = SocketIO(app, cors_allowed_origins="*")

# Store the process ID of the running script
script_process = None
system_status = "stopped"

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

@app.route('/start', methods=['POST', 'OPTIONS'])
def start_system():
    global script_process, system_status
    
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        if script_process is not None:
            return jsonify({'success': False, 'message': 'System is already running'})

        data = request.get_json()
        driver_name = data.get('driver_name', 'Driver')

        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'driving_aid.py'))
        
        if not os.path.exists(script_path):
            return jsonify({'success': False, 'message': 'System files not found'})

        script_process = subprocess.Popen(['python3', script_path, driver_name])
        system_status = "starting"
        socketio.emit('system_status', system_status)
        
        return jsonify({'success': True, 'message': 'System started successfully'})
    except Exception as e:
        system_status = "error"
        socketio.emit('system_status', system_status)
        return jsonify({'success': False, 'message': str(e)})

@app.route('/stop', methods=['POST'])
def stop_system():
    global script_process, system_status
    try:
        if script_process is None:
            return jsonify({'success': True, 'message': 'System is not running'})

        # Get the process and all its children
        parent = psutil.Process(script_process.pid)
        children = parent.children(recursive=True)
        
        # Terminate children first
        for child in children:
            child.terminate()
        
        # Terminate parent
        script_process.terminate()
        script_process = None
        system_status = "stopped"
        socketio.emit('system_status', system_status)
        
        return jsonify({'success': True, 'message': 'System stopped successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@socketio.on('connect')
def handle_connect():
    emit('system_status', system_status)

@socketio.on('toggle_system')
def handle_toggle(data):
    global system_status
    system_status = data.get('status', 'stopped')
    emit('system_status', system_status, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, port=5000, debug=True)