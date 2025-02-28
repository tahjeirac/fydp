from flask import Flask, request, jsonify
import time 
import subprocess

app = Flask(__name__)
feedback_data = None #store the feedback data globally 
song_data = None #the song data that will get passed to combo.py to start lighting up LEDs 

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

# Call the function on startup
setup_hotspot()

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
                
                return jsonify({"status": "success", "message": "Data received",  "song_data": song_data }), 200
        except Exception as e: 
                return jsonify({"status": "error", "message": str(e)}), 400

# SENDING JSON TO IPHONE (IPHONE DOES GET)
@app.route('/send_json', methods=['GET'])
def send_data():
    global feedback_data 
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
        data = request.get_json()
        
        # CHANGE BASED ON STRUCTURE OF THE STORED NOTES
        if "played_notes" not in data or not isinstance(data["played_notes"], list):
            return jsonify({"status": "error", "message": "Invalid data format"}), 400

        feedback_data = data  # Store feedback globally

        print("Feedback received:", feedback_data)  # Debugging output

        return jsonify({"status": "success", "message": "Feedback received"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    

if __name__ == '__main__': 
        app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
