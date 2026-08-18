from flask import Flask, request, jsonify, render_template
import requests
import json
import os

app = Flask(__name__)
DATA_FILE = 'data.json'

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"activated": [], "pending_actions": [], "online_players": []}
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

def get_roblox_user(username):
    try:
        req = requests.post("https://users.roblox.com/v1/usernames/users", json={"usernames": [username], "excludeBannedUsers": False})
        data = req.json()
        if not data.get("data"): return None
        user_id = data["data"][0]["id"]
        
        thumb_req = requests.get(f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png&isCircular=false")
        thumb_data = thumb_req.json()
        avatar = thumb_data["data"][0]["imageUrl"]
        return {"username": username, "id": user_id, "avatar": avatar}
    except:
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/check_player', methods=['POST'])
def check_player():
    req_data = request.json
    username = req_data.get('username')
    user_info = get_roblox_user(username)
    if not user_info:
        return jsonify({"error": "اللاعب غير موجود"})
    return jsonify({"success": True, "player": user_info})

@app.route('/api/activate', methods=['POST'])
def activate_player():
    req_data = request.json
    player_data = req_data.get('player')
    data = load_data()
    
    for p in data["activated"]:
        if p["id"] == player_data["id"]:
            return jsonify({"error": "اللاعب مفعل مسبقا"})
            
    data["activated"].append(player_data)
    save_data(data)
    return jsonify({"success": True})

@app.route('/api/deactivate', methods=['POST'])
def deactivate_player():
    req_data = request.json
    user_id = req_data.get('id')
    data = load_data()
    data["activated"] = [p for p in data["activated"] if p["id"] != user_id]
    save_data(data)
    return jsonify({"success": True})

@app.route('/api/data', methods=['GET'])
def get_dashboard_data():
    data = load_data()
    return jsonify({
        "activated": data["activated"],
        "online": data.get("online_players", [])
    })

@app.route('/api/action', methods=['POST'])
def submit_action():
    req_data = request.json
    data = load_data()
    data["pending_actions"].append({
        "type": req_data["type"],
        "user_id": req_data["user_id"],
        "reason": req_data.get("reason", "")
    })
    save_data(data)
    return jsonify({"success": True})

@app.route('/roblox/sync', methods=['POST'])
def roblox_sync():
    req_data = request.json
    data = load_data()
    data["online_players"] = req_data.get("players", [])
    actions = data["pending_actions"]
    data["pending_actions"] = [] 
    save_data(data)
    return jsonify({
        "activated_ids": [p["id"] for p in data["activated"]],
        "actions": actions
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
