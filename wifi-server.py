from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/receive_json', methods=['POST'])
def receive_json():
        try:
                data = request.get_json()
                #extracting midi data 
                title = data.get("title", "unknown")
                key = data.get("key", "unknown")
                tempo = data.get("tempo", 0)

                notes = data.get("notes", [])
                note_tuples = [(note["note"], note["duration"]) for note in notes]

                #debugging output
                print("Received JSON:", data)
                print(f"Title:  {title}")
                print(f"Key: {key}")
                print(f"Tempo: {tempo}")
                print(f"Notes: {note_tuples}")

                return jsonify({"status": "success", "message": "Data Received"}), 200
        except Exception as e: 
                return jsonify({"status": "error", "message": str(e)}), 400

# SENDING JSON TO IPHONE (IPHONE DOES GET)
@app.route('/send_json', methods=['GET'])
def send_data():
        data = {('E5', 480), ('D4', 480)}
        return jsonify(list(data))


if __name__ == '__main__': 
        app.run(host='0.0.0.0', port=5000, debug=True)
