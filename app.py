from flask import Flask, request, jsonify, render_template
import requests
import json
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
DATA_FILE = 'data.json'

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "activated": [],
            "pending_actions": [],
            "online_players": [],
            "banned": []
        }
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {
            "activated": [],
            "pending_actions": [],
            "online_players": [],
            "banned": []
        }

def save_data(data):
    try:
        if os.path.exists(DATA_FILE):
            backup_file = f"{DATA_FILE}.backup"
            with open(DATA_FILE, 'r', encoding='utf-8') as src:
                with open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

def get_roblox_user(username):
    try:
        req = requests.post(
            "https://users.roblox.com/v1/usernames/users",
            json={"usernames": [username], "excludeBannedUsers": False},
            timeout=10
        )
        req.raise_for_status()
        data = req.json()
        
        if not data.get("data"):
            return None
            
        user_id = data["data"][0]["id"]
        
        thumb_req = requests.get(
            f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png&isCircular=false",
            timeout=10
        )
        thumb_req.raise_for_status()
        thumb_data = thumb_req.json()
        
        avatar = thumb_data["data"][0]["imageUrl"] if thumb_data.get("data") else None
        
        return {
            "username": username,
            "id": user_id,
            "avatar": avatar
        }
    except:
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/check_player', methods=['POST'])
def check_player():
    try:
        req_data = request.json
        username = req_data.get('username')
        
        if not username:
            return jsonify({"error": "الرجاء إدخال اسم اللاعب"}), 400
            
        user_info = get_roblox_user(username)
        if not user_info:
            return jsonify({"error": "اللاعب غير موجود"}), 404
            
        return jsonify({"success": True, "player": user_info})
    except:
        return jsonify({"error": "حدث خطأ في السيرفر"}), 500

@app.route('/api/activate', methods=['POST'])
def activate_player():
    try:
        req_data = request.json
        player_data = req_data.get('player')
        
        if not player_data or not player_data.get('id'):
            return jsonify({"error": "بيانات اللاعب غير صالحة"}), 400
            
        data = load_data()
        
        for p in data["activated"]:
            if p["id"] == player_data["id"]:
                return jsonify({"error": "اللاعب مفعل مسبقاً"}), 409
                
        data["activated"].append(player_data)
        save_data(data)
        
        return jsonify({"success": True})
    except:
        return jsonify({"error": "حدث خطأ في السيرفر"}), 500

@app.route('/api/deactivate', methods=['POST'])
def deactivate_player():
    try:
        req_data = request.json
        user_id = req_data.get('id')
        
        if not user_id:
            return jsonify({"error": "الرجاء إدخال ID اللاعب"}), 400
            
        data = load_data()
        data["activated"] = [p for p in data["activated"] if p["id"] != user_id]
        
        if user_id in data.get("banned_ids", []):
            data["banned"] = [p for p in data["banned"] if p["id"] != user_id]
        
        save_data(data)
        
        return jsonify({"success": True})
    except:
        return jsonify({"error": "حدث خطأ في السيرفر"}), 500

@app.route('/api/data', methods=['GET'])
def get_dashboard_data():
    try:
        data = load_data()
        return jsonify({
            "activated": data.get("activated", []),
            "online": data.get("online_players", []),
            "banned": data.get("banned", [])
        })
    except:
        return jsonify({"error": "حدث خطأ في السيرفر"}), 500

@app.route('/api/action', methods=['POST'])
def submit_action():
    try:
        req_data = request.json
        action_type = req_data.get('type')
        user_id = req_data.get('user_id')
        reason = req_data.get('reason', '')
        
        if not action_type or not user_id:
            return jsonify({"error": "بيانات غير صالحة"}), 400
            
        data = load_data()
        
        player_info = None
        for p in data["activated"]:
            if p["id"] == user_id:
                player_info = p
                break
        
        if not player_info:
            for p in data["online_players"]:
                if p["id"] == user_id:
                    player_info = p
                    break
        
        if action_type == 'ban' and player_info:
            if not any(p["id"] == user_id for p in data["banned"]):
                data["banned"].append(player_info)
                data["activated"] = [p for p in data["activated"] if p["id"] != user_id]
                
        if action_type == 'unban':
            data["banned"] = [p for p in data["banned"] if p["id"] != user_id]
        
        data["pending_actions"].append({
            "type": action_type,
            "user_id": user_id,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
        
        save_data(data)
        return jsonify({"success": True})
    except:
        return jsonify({"error": "حدث خطأ في السيرفر"}), 500

@app.route('/api/broadcast', methods=['POST'])
def broadcast_message():
    try:
        req_data = request.json
        message = req_data.get('message', '')
        
        if not message:
            return jsonify({"error": "الرجاء إدخال رسالة"}), 400
        
        data = load_data()
        data["pending_actions"].append({
            "type": "broadcast",
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        
        save_data(data)
        return jsonify({"success": True, "message": "تم إرسال الرسالة للجميع"})
    except:
        return jsonify({"error": "حدث خطأ في السيرفر"}), 500

@app.route('/roblox/sync', methods=['POST'])
def roblox_sync():
    try:
        req_data = request.json
        data = load_data()
        
        data["online_players"] = req_data.get("players", [])
        actions = data["pending_actions"]
        data["pending_actions"] = []
        
        save_data(data)
        
        return jsonify({
            "activated_ids": [p["id"] for p in data["activated"]],
            "banned_ids": [p["id"] for p in data["banned"]],
            "actions": actions
        })
    except:
        return jsonify({"error": "حدث خطأ في السيرفر"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
