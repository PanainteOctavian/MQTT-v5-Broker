import json
import os
import Subscriptions.subscription as subscription
SESSIONS_FILE = 'Auth_and_sessions/sessionsDB.json'

def session_manager(connect_packet):
    print("SESSION MANAGER")

    client_id = connect_packet.get('client_id')
    clean_start = connect_packet.get('connect_flags', {}).get('clean_start')

    sessions_db = load_sessions_database()

    if clean_start == 0:

        if client_id in sessions_db:
            print(f"SESSION MANAGER: Restoring existing session for '{client_id}'")
            sessions_db[client_id]['connect_packet'] = connect_packet
            save_sessions_database(sessions_db)

            subscription_count = subscription.get_subscription_count(client_id)
            print(f"SESSION MANAGER: Session restored with {subscription_count} subscription(s)")

            return {
                'reason_code': 0x00,
                'session_present': 1
            }
        else:
            print(f"SESSION MANAGER: No existing session found for '{client_id}', creating new one")
            sessions_db[client_id] = create_new_session(connect_packet)
            save_sessions_database(sessions_db)
            return {
                'reason_code': 0x00,
                'session_present': 0
            }
    else:
        if client_id in sessions_db:
            print(f"SESSION MANAGER: Deleting old session for '{client_id}'")
            del sessions_db[client_id]

        print(f"SESSION MANAGER: Creating new session for '{client_id}'")
        sessions_db[client_id] = create_new_session(connect_packet)
        save_sessions_database(sessions_db)
        return {
            'reason_code': 0x00,
            'session_present': 0
        }

def load_sessions_database():
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("WARNING: Corrupted sessions file, creating new one")
            return {}
    return {}

def save_sessions_database(sessions_db):
    with open(SESSIONS_FILE, 'w') as f:
        json.dump(sessions_db, f, indent=2)
    print(f"DATABASE: Saved {len(sessions_db)} sessions to {SESSIONS_FILE}")

def create_new_session(connect_packet):
    return {
        'connect_packet': connect_packet,
        'subscriptions': [],  # abonari
        'pending_messages': [],  # msj cu qos > 0 neconfirmate
        'session_expiry': connect_packet.get('properties', {}).get('Session Expiry Interval', 0)
    }
