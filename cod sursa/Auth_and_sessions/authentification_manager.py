import json
import os

USERS_FILE = 'Auth_and_sessions/userDB.json'

def authentification_manager(connect_packet):
    print("AUTHENTIFICATION MODULE")

    username = connect_packet.get('username')
    password = connect_packet.get('password')
    client_id = connect_packet.get('client_id')
    user_flag = connect_packet.get('connect_flags', {}).get('user_flag')
    pass_flag = connect_packet.get('connect_flags', {}).get('pass_flag')

    # user and pass
    if user_flag and pass_flag:
        users_db = load_users_database()

        if username in users_db:
            # user existent
            stored_password = users_db[username]['password']

            if stored_password == password:
                print(f"AUTHENTIFICATION: User '{username}' authenticated")
                return 0x00
            else:
                print(f"AUTHENTIFICATION: Wrong password for '{username}'")
                return 0x86
        else:
            # user nou
            users_db[username] = {
                'password': password,
                'client_ids': client_id
            }
            save_users_database(users_db)

            print(f"AUTHENTIFICATION: New user '{username}' registered")
            return 0x00

    # anonymous
    allow_anonymous = True
    if allow_anonymous:
        register_anonymous_client(client_id)
        return 0x00

    return 0x87

def load_users_database():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("WARNING: Corrupted users file, creating new one")
            return {}
    return {}

def save_users_database(users_db):
    with open(USERS_FILE, 'w') as f:
        json.dump(users_db, f, indent=2)
    print(f"DATABASE: Saved {len(users_db)} users to {USERS_FILE}")

def register_anonymous_client(client_id):
    print(f"DATABASE: Anonymous client '{client_id}' allowed")
    return True
