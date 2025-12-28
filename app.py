#!/usr/bin/env python3
"""
Happy Server Admin Dashboard API
Flask backend with PostgreSQL integration
"""

from flask import Flask, jsonify, request, send_file, Response
from flask_cors import CORS
from functools import wraps
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json

app = Flask(__name__)
CORS(app)

# Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'happy-postgres'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'happy'),
    'user': os.getenv('DB_USER', 'happy'),
    'password': os.getenv('DB_PASSWORD', 'changeme')
}

# Basic Auth credentials
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'happy-admin-2025')

def check_auth(username, password):
    """Check if username/password combination is valid"""
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def authenticate():
    """Send 401 response that enables basic auth"""
    return Response(
        'Authentication required\n'
        'Please login with your credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Happy Admin Dashboard"'}
    )

def requires_auth(f):
    """Decorator for routes that require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

def get_db_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

@app.route('/')
@requires_auth
def index():
    """Serve the dashboard HTML"""
    return send_file('/app/index.html')

@app.route('/api/health')
def health():
    """Health check endpoint (no auth required)"""
    return jsonify({'status': 'ok', 'service': 'happy-admin-api'})

@app.route('/api/stats')
@requires_auth
def get_stats():
    """Get overall statistics"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM "Account") as total_accounts,
                (SELECT COUNT(*) FROM "Machine" WHERE active = true) as active_machines,
                (SELECT COUNT(*) FROM "Session") as total_sessions,
                (SELECT COUNT(*) FROM "SessionMessage") as total_messages,
                (SELECT COUNT(*) FROM "Session" WHERE "updatedAt" > NOW() - INTERVAL '1 hour') as active_sessions_1h
        """)

        stats = cursor.fetchone()
        cursor.close()
        conn.close()

        return jsonify(dict(stats))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/accounts')
@requires_auth
def get_accounts():
    """Get all accounts with statistics"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                a.id,
                COALESCE(a.username, '(not set)') as username,
                a."firstName" as first_name,
                a."lastName" as last_name,
                a."createdAt" as created_at,
                a."updatedAt" as updated_at,
                COUNT(DISTINCT s.id) as session_count,
                COUNT(sm.id) as message_count,
                MAX(s."updatedAt") as last_active
            FROM "Account" a
            LEFT JOIN "Session" s ON a.id = s."accountId"
            LEFT JOIN "SessionMessage" sm ON s.id = sm."sessionId"
            GROUP BY a.id, a.username, a."firstName", a."lastName", a."createdAt", a."updatedAt"
            ORDER BY last_active DESC NULLS LAST
        """)

        accounts = cursor.fetchall()
        cursor.close()
        conn.close()

        # Convert datetime objects to strings
        result = []
        for acc in accounts:
            item = dict(acc)
            for key in ['created_at', 'updated_at', 'last_active']:
                if item[key]:
                    item[key] = item[key].isoformat()
            result.append(item)

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/machines')
@requires_auth
def get_machines():
    """Get all machines/devices"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                m.id,
                m."accountId" as account_id,
                m.active,
                m."createdAt" as created_at,
                m."lastActiveAt" as last_active_at,
                a.username
            FROM "Machine" m
            LEFT JOIN "Account" a ON m."accountId" = a.id
            ORDER BY m."lastActiveAt" DESC
        """)

        machines = cursor.fetchall()
        cursor.close()
        conn.close()

        result = []
        for machine in machines:
            item = dict(machine)
            for key in ['created_at', 'last_active_at']:
                if item[key]:
                    item[key] = item[key].isoformat()
            result.append(item)

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions')
@requires_auth
def get_sessions():
    """Get active sessions"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get hours parameter (default 24)
        hours = request.args.get('hours', 24, type=int)

        cursor.execute("""
            SELECT
                s.id,
                s."accountId" as account_id,
                COUNT(sm.id) as message_count,
                s."createdAt" as created_at,
                s."updatedAt" as updated_at,
                a.username
            FROM "Session" s
            LEFT JOIN "SessionMessage" sm ON s.id = sm."sessionId"
            LEFT JOIN "Account" a ON s."accountId" = a.id
            WHERE s."updatedAt" > NOW() - INTERVAL '%s hours'
            GROUP BY s.id, s."accountId", s."createdAt", s."updatedAt", a.username
            ORDER BY s."updatedAt" DESC
            LIMIT 50
        """ % hours)

        sessions = cursor.fetchall()
        cursor.close()
        conn.close()

        result = []
        for session in sessions:
            item = dict(session)
            for key in ['created_at', 'updated_at']:
                if item[key]:
                    item[key] = item[key].isoformat()
            result.append(item)

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/activity')
@requires_auth
def get_activity():
    """Get hourly activity statistics"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                DATE_TRUNC('hour', "createdAt") as hour,
                COUNT(*) as message_count,
                COUNT(DISTINCT "sessionId") as active_sessions
            FROM "SessionMessage"
            WHERE "createdAt" > NOW() - INTERVAL '24 hours'
            GROUP BY DATE_TRUNC('hour', "createdAt")
            ORDER BY hour DESC
        """)

        activity = cursor.fetchall()
        cursor.close()
        conn.close()

        result = []
        for item in activity:
            row = dict(item)
            if row['hour']:
                row['hour'] = row['hour'].isoformat()
            result.append(row)

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/push-tokens')
@requires_auth
def get_push_tokens():
    """Get mobile push tokens"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                pt.token,
                pt."accountId" as account_id,
                pt."createdAt" as created_at,
                pt."updatedAt" as updated_at,
                a.username
            FROM "AccountPushToken" pt
            LEFT JOIN "Account" a ON pt."accountId" = a.id
            ORDER BY pt."updatedAt" DESC
        """)

        tokens = cursor.fetchall()
        cursor.close()
        conn.close()

        result = []
        for token in tokens:
            item = dict(token)
            for key in ['created_at', 'updated_at']:
                if item[key]:
                    item[key] = item[key].isoformat()
            result.append(item)

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/usage-reports')
@requires_auth
def get_usage_reports():
    """Get recent usage reports"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                ur.id,
                ur.key,
                ur."accountId" as account_id,
                ur."sessionId" as session_id,
                ur.data,
                ur."createdAt" as created_at,
                ur."updatedAt" as updated_at,
                a.username
            FROM "UsageReport" ur
            LEFT JOIN "Account" a ON ur."accountId" = a.id
            ORDER BY ur."updatedAt" DESC
            LIMIT 20
        """)

        reports = cursor.fetchall()
        cursor.close()
        conn.close()

        result = []
        for report in reports:
            item = dict(report)
            for key in ['created_at', 'updated_at']:
                if item[key]:
                    item[key] = item[key].isoformat()
            result.append(item)

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/connections')
@requires_auth
def get_connections():
    """Get active Happy server sessions and machine connections"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed', 'connections': [], 'unique_ips': [], 'total_connections': 0}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get active sessions from last 5 minutes (indicating active connections)
        cursor.execute("""
            SELECT
                s.id as session_id,
                s."accountId" as account_id,
                s.tag as session_tag,
                s."lastActiveAt" as last_active,
                s."createdAt" as created_at,
                a.username,
                a."firstName" as first_name,
                a."lastName" as last_name,
                COUNT(DISTINCT sm.id) as message_count,
                EXTRACT(EPOCH FROM (NOW() - s."lastActiveAt")) as seconds_inactive
            FROM "Session" s
            LEFT JOIN "Account" a ON s."accountId" = a.id
            LEFT JOIN "SessionMessage" sm ON s.id = sm."sessionId"
            WHERE s.active = true
              AND s."lastActiveAt" > NOW() - INTERVAL '5 minutes'
            GROUP BY s.id, s."accountId", s.tag, s."lastActiveAt", s."createdAt",
                     a.username, a."firstName", a."lastName"
            ORDER BY s."lastActiveAt" DESC
            LIMIT 50
        """)

        sessions = cursor.fetchall()
        cursor.close()
        conn.close()

        connections = []
        for session in sessions:
            item = dict(session)
            # Convert timestamps
            if item['last_active']:
                item['last_active'] = item['last_active'].isoformat()
            if item['created_at']:
                item['created_at'] = item['created_at'].isoformat()

            # Create a display name
            if item.get('username'):
                display_name = item['username']
            elif item.get('first_name') or item.get('last_name'):
                display_name = f"{item.get('first_name', '')} {item.get('last_name', '')}".strip()
            else:
                display_name = "Anonymous"

            connections.append({
                "session_id": item['session_id'][:12] + "...",  # Shortened for display
                "account": display_name,
                "session_tag": item['session_tag'],
                "last_active": item['last_active'],
                "created_at": item['created_at'],
                "messages": item['message_count'],
                "inactive_seconds": int(item['seconds_inactive']),
                "status": "ACTIVE" if item['seconds_inactive'] < 60 else "IDLE"
            })

        # Read client IPs from file (captured from netstat on port 443)
        client_ips = []
        try:
            with open("/app/client-ips.txt", "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    parts = line.strip().split("|")
                    if len(parts) >= 4:
                        client_ips.append({
                            "ip": parts[0],
                            "port": parts[1],
                            "client_port": parts[2],
                            "timestamp": int(parts[3])
                        })
        except FileNotFoundError:
            pass
        except Exception:
            pass

        return jsonify({
            "connections": connections,
            "total_connections": len(connections),
            "unique_accounts": len(set([c["account"] for c in connections])),
            "client_ips": client_ips,
            "unique_client_ips": len(set([ip["ip"] for ip in client_ips]))
        })
    except Exception as e:
        return jsonify({"error": str(e), "connections": [], "total_connections": 0}), 500

@app.route('/api/ip-info/<ip>')
@requires_auth
def get_ip_info(ip):
    """Get geolocation info for an IP address"""
    import subprocess

    try:
        # Try to get info using curl to ipapi.co
        result = subprocess.run(
            ["curl", "-s", f"https://ipapi.co/{ip}/json/"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            return jsonify({
                "ip": data.get("ip"),
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country_name"),
                "org": data.get("org"),
                "timezone": data.get("timezone")
            })
        else:
            return jsonify({"error": "Could not fetch IP info"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("Happy Server Admin Dashboard API")
    print("=" * 60)
    print(f"Admin Username: {ADMIN_USERNAME}")
    print(f"Admin Password: {ADMIN_PASSWORD}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)
