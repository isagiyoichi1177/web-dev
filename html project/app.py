from flask import Flask, request, jsonify, send_from_directory, abort, make_response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
import bleach
import sqlite3
import os
import uuid
import json
from datetime import datetime

# Serve frontend static files from project root so you can open http://localhost:5000/
app = Flask(__name__, static_folder='.', static_url_path='')

# SECURITY: limit request size to 2MB
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

# Read environment config
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'changeme')
DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'

# CORS: configurable allowed origins via environment variable (comma-separated).
# By default allow localhost for dev. In production set ALLOWED_ORIGINS to a
# comma-separated list (e.g. https://example.com)
allowed = os.environ.get('ALLOWED_ORIGINS')
if allowed:
    origins = [o.strip() for o in allowed.split(',') if o.strip()]
else:
    origins = ["http://127.0.0.1:5000", "http://localhost:5000"]

CORS(app, resources={r"/api/*": {"origins": origins}})

# Rate limiter: protect POST endpoints
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])
limiter.init_app(app)

# Security headers and Content Security Policy. We avoid 'unsafe-inline' for
# scripts so that pages are protected against XSS; styles may allow inline
# for convenience. FORCE_HTTPS env var can force HTTPS in non-debug runs.
force_https = os.environ.get('FORCE_HTTPS', '1') == '1' if not DEBUG else False
csp = {
    'default-src': ["'self'"],
    'script-src': ["'self'"],
    'style-src': ["'self'", "'unsafe-inline'"],
    'img-src': ["'self'", 'data:'],
}

Talisman(app, content_security_policy=csp, force_https=force_https)

# Secure session cookie defaults
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
if force_https:
    app.config['SESSION_COOKIE_SECURE'] = True

# Database (SQLite) for persistence
DB_PATH = os.path.join(os.path.dirname(__file__), 'orders.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            items TEXT NOT NULL,
            total REAL NOT NULL,
            location_lat REAL,
            location_lng REAL,
            status TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    # carts table to store visitor carts (visitor_id primary key)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS carts (
            visitor_id TEXT PRIMARY KEY,
            cart_json TEXT,
            updated_at TEXT
        )
    ''')
    conn.close()

init_db()

# In-memory messages store (also persisted via other means if needed)
messages = []


@app.route('/api/contact', methods=['POST'])
def contact():
    data = request.get_json(silent=True)
    if not data or not all(key in data for key in ['name', 'email', 'message']):
        return jsonify({'error': 'Missing required fields'}), 400

    # Basic sanitization (strip HTML/JS)
    name = bleach.clean(data.get('name', ''), strip=True)
    email = bleach.clean(data.get('email', ''), strip=True)
    message_text = bleach.clean(data.get('message', ''), strip=True)

    # Very basic length checks
    if len(name) > 200 or len(email) > 200 or len(message_text) > 2000:
        return jsonify({'error': 'Input too long'}), 400

    # store in memory for now as well
    messages.append({
        'id': len(messages) + 1,
        'name': name,
        'email': email,
        'message': message_text,
        'timestamp': datetime.now().isoformat()
    })

    return jsonify({'success': True, 'message': 'Message received successfully'}), 201

@app.route('/api/orders', methods=['POST'])
@limiter.limit("10/minute")
def create_order():
    data = request.get_json(silent=True)
    required_fields = ['name', 'email', 'phone', 'address', 'items', 'total']
    if not data or not all(key in data for key in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    # sanitize inputs
    name = bleach.clean(str(data.get('name', '')), strip=True)
    email = bleach.clean(str(data.get('email', '')), strip=True)
    phone = bleach.clean(str(data.get('phone', '')), strip=True)
    address = bleach.clean(str(data.get('address', '')), strip=True)
    items = data.get('items', [])
    total = data.get('total', 0)

    # Basic validation
    if not name or not email or not phone or not address or not isinstance(items, list):
        return jsonify({'error': 'Invalid input'}), 400

    if len(name) > 200 or len(email) > 200 or len(address) > 2000:
        return jsonify({'error': 'Input too long'}), 400

    # Accept optional location
    location = data.get('location') or {}
    lat = None
    lng = None
    if isinstance(location, dict):
        try:
            lat = float(location.get('latitude')) if location.get('latitude') is not None else None
            lng = float(location.get('longitude')) if location.get('longitude') is not None else None
        except (ValueError, TypeError):
            lat = None; lng = None

    # Store order in SQLite using parameterized queries
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO orders (name,email,phone,address,items,total,location_lat,location_lng,status,timestamp) VALUES (?,?,?,?,?,?,?,?,?,?)',
        (name, email, phone, address, str(items), float(total), lat, lng, 'pending', datetime.now().isoformat())
    )
    conn.commit()
    order_id = cur.lastrowid
    conn.close()

    # return minimal info
    return jsonify({'success': True, 'message': 'Order placed successfully', 'orderId': order_id}), 201

@app.route('/api/orders', methods=['GET'])
def get_orders():
    # Admin-protected listing (simple token via ADMIN_TOKEN env var)
    token = request.headers.get('X-Admin-Token') or request.args.get('token')
    if not token or token != ADMIN_TOKEN:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM orders ORDER BY id DESC').fetchall()
    conn.close()

    orders_list = [dict(r) for r in rows]
    return jsonify(orders_list)

@app.route('/api/messages', methods=['GET'])
def get_messages():
    return jsonify(messages)


@app.route('/')
def index():
    # Serve the main HTML file; set a visitor cookie if missing so we can
    # associate carts with visitors when they opt-in to server-side storage.
    visitor_id = request.cookies.get('visitor_id')
    response = make_response(send_from_directory('.', 'index.html'))
    if not visitor_id:
        new_id = str(uuid.uuid4())
        # 1 year expiry
        max_age = 365 * 24 * 60 * 60
        secure_flag = True if force_https else False
        response.set_cookie('visitor_id', new_id, max_age=max_age, httponly=True, samesite='Lax', secure=secure_flag)
    return response


@app.route('/api/cart', methods=['GET'])
def get_cart():
    visitor_id = request.cookies.get('visitor_id')
    if not visitor_id:
        return jsonify({'error': 'No visitor cookie'}), 400
    conn = get_db_connection()
    row = conn.execute('SELECT cart_json FROM carts WHERE visitor_id = ?', (visitor_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'items': [], 'total': 0.0})
    try:
        cart = json.loads(row['cart_json'])
    except Exception:
        cart = {'items': [], 'total': 0.0}
    return jsonify(cart)


@app.route('/api/cart', methods=['POST'])
def save_cart():
    visitor_id = request.cookies.get('visitor_id')
    if not visitor_id:
        return jsonify({'error': 'No visitor cookie'}), 400
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'No cart data provided'}), 400
    try:
        cart_json = json.dumps(data)
    except Exception:
        return jsonify({'error': 'Invalid cart data'}), 400
    conn = get_db_connection()
    conn.execute('REPLACE INTO carts (visitor_id, cart_json, updated_at) VALUES (?,?,?)', (visitor_id, cart_json, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({'success': True}), 200

if __name__ == '__main__':
    # Control whether we listen on 0.0.0.0 via RUN_PUBLIC env var. In general
    # keep this off for local development and use a reverse proxy with TLS for
    # production.
    run_public = os.environ.get('RUN_PUBLIC', '0') == '1'
    host = '0.0.0.0' if run_public else '127.0.0.1'
    app.run(host=host, debug=DEBUG, port=int(os.environ.get('PORT', 5000)))
