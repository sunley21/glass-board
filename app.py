from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from functools import wraps
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'glass-board-secret-key-2024'

# Fix for Render.com - use /tmp directory for files
if os.environ.get('RENDER'):
    import tempfile
    TEMP_DIR = tempfile.gettempdir()
    USERS_FILE = os.path.join(TEMP_DIR, 'users.json')
    ARCHIVES_FILE = os.path.join(TEMP_DIR, 'archives.json')
    NOTIFICATIONS_FILE = os.path.join(TEMP_DIR, 'notifications.json')
else:
    USERS_FILE = 'users.json'
    ARCHIVES_FILE = 'archives.json'
    NOTIFICATIONS_FILE = 'notifications.json'

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def load_archives():
    if os.path.exists(ARCHIVES_FILE):
        with open(ARCHIVES_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_archives(archives):
    with open(ARCHIVES_FILE, 'w') as f:
        json.dump(archives, f, indent=2)

def load_notifications(user_email):
    if os.path.exists(NOTIFICATIONS_FILE):
        with open(NOTIFICATIONS_FILE, 'r') as f:
            all_notifications = json.load(f)
            return all_notifications.get(user_email, [])
    return []

def save_notification(user_email, message, type='info'):
    notifications = {}
    if os.path.exists(NOTIFICATIONS_FILE):
        with open(NOTIFICATIONS_FILE, 'r') as f:
            notifications = json.load(f)
    
    if user_email not in notifications:
        notifications[user_email] = []
    
    notifications[user_email].insert(0, {
        'message': message,
        'type': type,
        'time': datetime.now().strftime('%I:%M %p'),
        'date': datetime.now().strftime('%b %d, %Y'),
        'read': False
    })
    
    notifications[user_email] = notifications[user_email][:30]
    
    with open(NOTIFICATIONS_FILE, 'w') as f:
        json.dump(notifications, f, indent=2)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_id = request.form.get('username_id')
        password = request.form.get('password')
        
        users = load_users()
        
        if username_id in users and users[username_id]['password'] == password:
            session['user_id'] = username_id
            session['user_name'] = users[username_id]['name']
            save_notification(username_id, 'You logged in successfully', 'success')
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/signup', methods=['POST'])
def signup():
    username_id = request.form.get('username_id')
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')
    
    users = load_users()
    
    if username_id in users:
        return render_template('login.html', error='Username already exists')
    
    users[username_id] = {
        'name': name,
        'email': email,
        'username': username_id,
        'password': password,
        'school_id': ''
    }
    save_users(users)
    
    archives = load_archives()
    if username_id not in archives:
        archives[username_id] = {'main': [], 'trash': []}
        save_archives(archives)
    
    session['user_id'] = username_id
    session['user_name'] = name
    save_notification(username_id, 'Account created successfully', 'success')
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user_name=session.get('user_name'), user_id=session.get('user_id'))

@app.route('/get-user-info')
@login_required
def get_user_info():
    users = load_users()
    user_id = session['user_id']
    if user_id in users:
        return jsonify({
            'name': users[user_id].get('name', ''),
            'email': users[user_id].get('email', ''),
            'username': user_id,
            'school_id': users[user_id].get('school_id', '')
        })
    return jsonify({'error': 'User not found'}), 404

@app.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    try:
        data = request.get_json()
        users = load_users()
        user_id = session['user_id']
        
        if user_id in users:
            if 'name' in data and data['name']:
                users[user_id]['name'] = data['name']
                save_notification(user_id, f'Your name was updated to "{data["name"]}"', 'success')
            
            save_users(users)
            session['user_name'] = users[user_id]['name']
            return jsonify({'name': users[user_id]['name'], 'email': users[user_id]['email']})
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get-notifications')
@login_required
def get_notifications():
    notifications = load_notifications(session['user_id'])
    return jsonify(notifications)

@app.route('/mark-notifications-read', methods=['POST'])
@login_required
def mark_notifications_read():
    try:
        notifications = {}
        if os.path.exists(NOTIFICATIONS_FILE):
            with open(NOTIFICATIONS_FILE, 'r') as f:
                notifications = json.load(f)
        
        user_email = session['user_id']
        if user_email in notifications:
            for notif in notifications[user_email]:
                notif['read'] = True
        
        with open(NOTIFICATIONS_FILE, 'w') as f:
            json.dump(notifications, f, indent=2)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/clear-notifications', methods=['POST'])
@login_required
def clear_notifications():
    notifications = {}
    if os.path.exists(NOTIFICATIONS_FILE):
        with open(NOTIFICATIONS_FILE, 'r') as f:
            notifications = json.load(f)
    
    notifications[session['user_id']] = []
    
    with open(NOTIFICATIONS_FILE, 'w') as f:
        json.dump(notifications, f, indent=2)
    
    return jsonify({'success': True})

@app.route('/get-archives')
@login_required
def get_archives():
    archives = load_archives()
    user_id = session['user_id']
    if user_id not in archives:
        archives[user_id] = {'main': [], 'trash': []}
        save_archives(archives)
    user_archives = archives.get(user_id, {'main': [], 'trash': []})
    return jsonify(user_archives)

@app.route('/save-archives', methods=['POST'])
@login_required
def save_archives_endpoint():
    try:
        data = request.get_json()
        archives = load_archives()
        user_id = session['user_id']
        archives[user_id] = data
        save_archives(archives)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/add-folder', methods=['POST'])
@login_required
def add_folder():
    try:
        data = request.get_json()
        folder_name = data.get('name')
        
        if not folder_name:
            return jsonify({'error': 'Folder name required'}), 400
        
        archives = load_archives()
        user_id = session['user_id']
        
        if user_id not in archives:
            archives[user_id] = {'main': [], 'trash': []}
        
        new_item = {
            'id': datetime.now().timestamp(),
            'name': folder_name,
            'date': datetime.now().strftime('%m/%d/%Y'),
            'isFolder': True,
            'children': []
        }
        
        archives[user_id]['main'].insert(0, new_item)
        save_archives(archives)
        save_notification(user_id, f'New folder "{folder_name}" created', 'success')
        
        return jsonify({'success': True, 'item': new_item})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/move-to-trash', methods=['POST'])
@login_required
def move_to_trash():
    try:
        data = request.get_json()
        item_id = data.get('id')
        
        archives = load_archives()
        user_id = session['user_id']
        
        if user_id in archives:
            def search_and_remove(arr):
                for i, item in enumerate(arr):
                    if item['id'] == item_id:
                        return arr.pop(i)
                    if 'children' in item and item['children']:
                        found = search_and_remove(item['children'])
                        if found:
                            return found
                return None
            
            item_to_move = search_and_remove(archives[user_id]['main'])
            
            if item_to_move:
                archives[user_id]['trash'].append(item_to_move)
                save_archives(archives)
                save_notification(user_id, f'"{item_to_move["name"]}" moved to Bin', 'info')
                return jsonify({'success': True})
        
        return jsonify({'error': 'Item not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/restore-from-trash', methods=['POST'])
@login_required
def restore_from_trash():
    try:
        data = request.get_json()
        item_id = data.get('id')
        
        archives = load_archives()
        user_id = session['user_id']
        
        if user_id in archives:
            trash_items = archives[user_id]['trash']
            item_to_restore = None
            
            for i, item in enumerate(trash_items):
                if item['id'] == item_id:
                    item_to_restore = trash_items.pop(i)
                    break
            
            if item_to_restore:
                archives[user_id]['main'].append(item_to_restore)
                save_archives(archives)
                save_notification(user_id, f'"{item_to_restore["name"]}" restored from Bin', 'success')
                return jsonify({'success': True})
        
        return jsonify({'error': 'Item not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete-permanently', methods=['POST'])
@login_required
def delete_permanently():
    try:
        data = request.get_json()
        item_id = data.get('id')
        
        archives = load_archives()
        user_id = session['user_id']
        
        if user_id in archives:
            trash_items = archives[user_id]['trash']
            deleted_item = None
            for i, item in enumerate(trash_items):
                if item['id'] == item_id:
                    deleted_item = trash_items.pop(i)
                    break
            archives[user_id]['trash'] = trash_items
            save_archives(archives)
            if deleted_item:
                save_notification(user_id, f'"{deleted_item["name"]}" permanently deleted', 'info')
            return jsonify({'success': True})
        
        return jsonify({'error': 'Item not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete-all-from-bin', methods=['POST'])
@login_required
def delete_all_from_bin():
    try:
        archives = load_archives()
        user_id = session['user_id']
        
        if user_id in archives:
            count = len(archives[user_id]['trash'])
            archives[user_id]['trash'] = []
            save_archives(archives)
            save_notification(user_id, f'{count} item(s) permanently deleted from Bin', 'info')
            return jsonify({'success': True})
        
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/save-photo', methods=['POST'])
@login_required
def save_photo():
    try:
        data = request.get_json()
        folder_id = data.get('folderId')
        image_data = data.get('imageData')
        path = data.get('path', [])
        
        archives = load_archives()
        user_id = session['user_id']
        
        target = archives[user_id]['main']
        for p in path:
            folder = next((item for item in target if item['id'] == p and item.get('isFolder')), None)
            if folder and 'children' in folder:
                target = folder['children']
        
        folder = next((item for item in target if item['id'] == folder_id and item.get('isFolder')), None)
        
        if folder:
            if 'photos' not in folder:
                folder['photos'] = []
            
            photo = {
                'id': datetime.now().timestamp(),
                'data': image_data,
                'date': datetime.now().strftime('%m/%d/%Y'),
                'time': datetime.now().strftime('%I:%M %p')
            }
            folder['photos'].append(photo)
            save_archives(archives)
            save_notification(user_id, 'Photo saved successfully', 'success')
            return jsonify({'success': True})
        
        return jsonify({'error': 'Folder not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)