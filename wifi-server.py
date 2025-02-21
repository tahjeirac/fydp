from flask import Flask, request, jsonify
import time 

app = Flask(__name__)
feedback_data = None #store the feedback data globally 
song_data = None #the song data that will get passed to combo.py to start lighting up LEDs 

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

                return jsonify({"status": "success", "message": "Data received"}), 200
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
    

if __name__ == '__main__': 
        app.run(host='0.0.0.0', port=5000, debug=True)
