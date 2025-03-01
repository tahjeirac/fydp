import signal
import time 
import os
import subprocess
import json 
import logging
from flask import Flask, request, jsonify
import sys
app = Flask(__name__)

# Configure logging
logging.basicConfig(
    filename="output.log",  # Save logs to a file
    level=logging.DEBUG,  # Set log level
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
)

feedback_data = None #store the feedback data globally 
song_data = None #the song data that will get passed to combo.py to start lighting up LEDs 
FEEDBACK_FILE_PATH = 'feedback.json'

def setup_hotspot():
    #Configures Raspberry Pi as a Wi-Fi hotspot
    try:
        print("Setting up the Raspberry Pi as a hotspot...")

        # Restart the hotspot services
        subprocess.run(["sudo", "systemctl", "restart", "hostapd", "dnsmasq"], check=True)

        # Assign a static IP to wlan0
        subprocess.run(["sudo", "ip", "addr", "add", "192.168.4.1/24", "dev", "wlan0"], check=True)

        print("Hotspot setup complete.")
    except subprocess.CalledProcessError as e:
        print(f"Error setting up hotspot: {e}")

def disable_hotspot():
    print("Shutting down hotspot...")
    subprocess.run(["sudo", "systemctl", "stop", "hostapd", "dnsmasq"], check=True)
    subprocess.run(["sudo", "ip", "addr", "flush", "dev", "wlan0"], check=True)
    print("Hotspot has been disabled.")

@app.route('/receive_json', methods=['POST'])
def receive_json():
        global song_data #storing received song data in JSON 
        try:
                data = request.get_json()
                # Extracting song data
                song_data = {
                "title": data.get("title", "unknown"),
                "notes": data.get("notes", [])  # Ensure it's passed as a list
                }

                # Debugging output
                print("Received JSON:", song_data)
                with open('song.json', 'w') as file:
                    json.dump(song_data, file, indent=4)  # 'indent' makes the JSON more readable
                return jsonify({"status": "success", "message": "Data received",  "song_data": song_data }), 200
        except Exception as e: 
                return jsonify({"status": "error", "message": str(e)}), 400


# SENDING JSON TO IPHONE (IPHONE DOES GET)
@app.route('/send_json', methods=['GET'])
def send_data():
    global feedback_data 
    mock_data = [
            {"C4": 1.0001378059387207},
            {"C4": 0.5009052753448486},
            {"A4": 0.25047969818115234}
        ]
        
    feedback_data = mock_data  # Store feedback globally
    timeout = 20 #maximum wait time 
    interval = 1 #how often to check 
    elapsed_time = 0

    while feedback_data is None and elapsed_time < timeout:
        time.sleep(interval)
        elapsed_time += interval 

    if feedback_data: 
        response = jsonify(feedback_data)
        feedback_data = None 
        return response, 200 
    else: 
        return jsonify({"status": "pending"}), 204  # no feedback yet
    

# RECEIVING FEEDBACK DATA FROM RASPBERRY PI. pi will do post to here w feedback data
@app.route('/send_feedback', methods=['POST'])
def receive_feedback():
    global feedback_data
    try:
        mock_data = [
            {"C4": 1.0001378059387207},
            {"C4": 0.5009052753448486},
            {"A4": 0.25047969818115234}
        ]
        
        feedback_data = mock_data  # Store feedback globally

        print("Feedback received:", feedback_data)  # Debugging output

        return jsonify({"status": "success", "message": "Feedback received"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


if __name__ == '__main__':
    disable_hotspot()
    setup_hotspot()  # Start the hotspots
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
    
