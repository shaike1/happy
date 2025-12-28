#!/usr/bin/env python3
"""
Happy Server Push Notification Service
Monitors Happy server activity and sends push notifications
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import time
import os
import json

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'happy-postgres'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'happy'),
    'user': os.getenv('DB_USER', 'happy'),
    'password': os.getenv('DB_PASSWORD', 'changeme')
}

STATE_FILE = '/app/notifier-state.json'

def get_db_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def load_state():
    """Load state from file"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "last_check": 0,
        "notified_sessions": [],
        "notified_ips": [],
        "last_message_count": 0
    }

def save_state(state):
    """Save state to file"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        print(f"Error saving state: {e}")

def get_push_tokens():
    """Get all registered push tokens"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT token, "accountId", a.username
            FROM "AccountPushToken" pt
            LEFT JOIN "Account" a ON pt."accountId" = a.id
            ORDER BY pt."updatedAt" DESC
        """)
        tokens = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(t) for t in tokens]
    except Exception as e:
        print(f"Error getting push tokens: {e}")
        return []

def send_push_notification(tokens, title, body, data=None):
    """Send push notification via Expo"""
    if not tokens:
        return
    
    messages = []
    for token in tokens:
        message = {
            "to": token,
            "sound": "default",
            "title": title,
            "body": body,
            "priority": "high"
        }
        if data:
            message["data"] = data
        messages.append(message)
    
    try:
        response = requests.post(
            "https://exp.host/--/api/v2/push/send",
            json=messages,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        print(f"Sent notification: {title} - Status: {response.status_code}")
        return response.json()
    except Exception as e:
        print(f"Error sending notification: {e}")
        return None

def get_active_sessions():
    """Get active sessions"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, "accountId", tag, "lastActiveAt"
            FROM "Session"
            WHERE active = true AND "lastActiveAt" > NOW() - INTERVAL '5 minutes'
            ORDER BY "lastActiveAt" DESC
        """)
        sessions = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(s) for s in sessions]
    except Exception as e:
        print(f"Error getting sessions: {e}")
        return []

def get_message_count():
    """Get total message count"""
    conn = get_db_connection()
    if not conn:
        return 0
    
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM "SessionMessage"')
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except Exception as e:
        print(f"Error getting message count: {e}")
        return 0

def get_client_ips():
    """Read client IPs from file"""
    ips = []
    try:
        with open("/app/client-ips.txt", "r") as f:
            for line in f:
                if line.strip():
                    parts = line.strip().split("|")
                    if len(parts) >= 1:
                        ips.append(parts[0])
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Error reading client IPs: {e}")
    return list(set(ips))

def check_and_notify():
    """Check for changes and send notifications"""
    state = load_state()
    
    # Get push tokens
    token_data = get_push_tokens()
    tokens = [t['token'] for t in token_data]
    
    if not tokens:
        print("No push tokens registered")
        return
    
    print(f"Checking activity... ({len(tokens)} tokens registered)")
    
    notifications_sent = False
    
    # Check for new sessions
    sessions = get_active_sessions()
    session_ids = [s['id'] for s in sessions]
    
    new_sessions = [sid for sid in session_ids if sid not in state["notified_sessions"]]
    
    # Only notify if truly new (not first run)
    if new_sessions and state["last_check"] > 0:
        truly_new = new_sessions
        count = len(truly_new)
        send_push_notification(
            tokens,
            f"🔔 {count} New Happy Session{'s' if count > 1 else ''}",
            f"{count} new client session{'s' if count > 1 else ''} connected to your Happy server",
            {"type": "new_session", "count": count}
        )
        state["notified_sessions"].extend(truly_new)
        # Keep only last 50 session IDs
        state["notified_sessions"] = state["notified_sessions"][-50:]
        notifications_sent = True
    
    # Check for message activity
    message_count = get_message_count()
    if state["last_message_count"] > 0:
        new_messages = message_count - state["last_message_count"]
        if new_messages >= 10:  # Only notify if significant activity
            send_push_notification(
                tokens,
                "📬 High Activity on Happy Server",
                f"{new_messages} new messages in active sessions",
                {"type": "high_activity", "count": new_messages}
            )
            notifications_sent = True
    
    state["last_message_count"] = message_count
    
    # Check for new client IPs
    client_ips = get_client_ips()
    new_ips = [ip for ip in client_ips if ip not in state["notified_ips"]]
    
    if new_ips and state["last_check"] > 0:
        count = len(new_ips)
        send_push_notification(
            tokens,
            f"🌍 {count} New Client IP{'s' if count > 1 else ''}",
            f"New connections from: {', '.join(new_ips[:3])}{'...' if count > 3 else ''}",
            {"type": "new_ip", "ips": new_ips}
        )
        state["notified_ips"].extend(new_ips)
        # Keep only last 20 IPs
        state["notified_ips"] = state["notified_ips"][-20:]
        notifications_sent = True
    
    # Update state
    state["last_check"] = int(time.time())
    save_state(state)
    
    if notifications_sent:
        print("✅ Notifications sent")
    else:
        print(f"⏳ No changes - {len(sessions)} active sessions, {len(client_ips)} client IPs")

def main():
    """Main loop"""
    print("=" * 60)
    print("Happy Server Push Notification Service")
    print("=" * 60)
    print("Monitoring for activity changes...")
    print()
    
    while True:
        try:
            check_and_notify()
        except Exception as e:
            print(f"Error in monitoring loop: {e}")
        
        time.sleep(60)  # Check every minute

if __name__ == '__main__':
    main()
