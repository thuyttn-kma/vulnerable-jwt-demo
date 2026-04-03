from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import jwt
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

SECRET_KEY = "secret"
users_db = {}

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            request.user_id = payload['user_id']
            request.role = payload['role']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({'message': f'Invalid token: {str(e)}'}), 401
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.role != 'admin':
            return jsonify({'message': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Username and password required'}), 400
    username = data['username']
    password = data['password']
    if username in users_db:
        return jsonify({'message': 'User already exists'}), 409
    users_db[username] = {'password': password, 'role': 'user', 'created_at': datetime.utcnow().isoformat()}
    return jsonify({'message': 'User registered successfully', 'username': username}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Username and password required'}), 400
    username = data['username']
    password = data['password']
    if username not in users_db or users_db[username]['password'] != password:
        return jsonify({'message': 'Invalid credentials'}), 401
    user_role = users_db[username]['role']
    payload = {'user_id': username, 'role': user_role, 'exp': datetime.utcnow() + timedelta(hours=24), 'iat': datetime.utcnow()}
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return jsonify({'message': 'Login successful', 'token': token, 'role': user_role}), 200

@app.route('/api/user/profile', methods=['GET'])
@token_required
def get_user_profile():
    user_id = request.user_id
    if user_id not in users_db:
        return jsonify({'message': 'User not found'}), 404
    user_data = users_db[user_id].copy()
    user_data.pop('password', None)
    return jsonify({'message': 'User profile retrieved', 'username': user_id, 'role': request.role, 'user_data': user_data}), 200

@app.route('/api/admin/users', methods=['GET'])
@token_required
@admin_required
def get_all_users():
    users_list = []
    for username, user_data in users_db.items():
        user_copy = user_data.copy()
        user_copy.pop('password', None)
        users_list.append({'username': username, 'role': user_copy['role'], 'created_at': user_copy['created_at']})
    return jsonify({'message': 'All users retrieved', 'total_users': len(users_list), 'users': users_list}), 200

@app.route('/api/admin/users/<username>/role', methods=['PUT'])
@token_required
@admin_required
def update_user_role(username):
    data = request.get_json()
    if not data or not data.get('role'):
        return jsonify({'message': 'Role required'}), 400
    if username not in users_db:
        return jsonify({'message': 'User not found'}), 404
    new_role = data['role']
    if new_role not in ['user', 'admin']:
        return jsonify({'message': 'Invalid role'}), 400
    users_db[username]['role'] = new_role
    return jsonify({'message': f'User role updated to {new_role}', 'username': username, 'new_role': new_role}), 200

@app.route('/api/admin/protected-data', methods=['GET'])
@token_required
@admin_required
def get_protected_data():
    return jsonify({'message': 'Sensitive admin data retrieved', 'sensitive_data': {'system_config': 'Database connection string, API keys, etc.', 'total_users': len(users_db), 'security_tokens': ['token1', 'token2', 'token3']}}), 200

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({'message': 'Endpoint not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000
)