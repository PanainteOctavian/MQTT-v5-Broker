import json
import os

SUBS_FILE = 'Subscriptions/subscriptionsDB.json'

def subscription_manager(subscribe_data):
    print("SUBSCRIPTION MANAGER")

    client_id = subscribe_data.get('client_id')
    topic = subscribe_data.get('topic')
    qos = subscribe_data.get('qos', 0)
    packet_id = subscribe_data.get('packet_id')
    properties = subscribe_data.get('properties', {})

    if not client_id or not topic:
        print("SUBSCRIPTION MANAGER: Missing client_id or topic")
        return False

    subscriptions_db = load_subscriptions_database()

    # init client daca nu exista in subscriptions_db
    if client_id not in subscriptions_db:
        subscriptions_db[client_id] = {
            'subscriptions': [],
            'packet_ids': []
        }

    # verif daca exista subscriptia
    existing_sub = None
    for sub in subscriptions_db[client_id]['subscriptions']:
        if sub['topic'] == topic:
            existing_sub = sub
            break

    if existing_sub:
        # modif subscriptia existenta
        existing_sub['qos'] = qos
        existing_sub['no_local'] = subscribe_data.get('no_local', False)
        existing_sub['retain_as_published'] = subscribe_data.get('retain_as_published', False)
        existing_sub['retain_handling'] = subscribe_data.get('retain_handling', 0)
        existing_sub['properties'] = properties
        print(f"SUBSCRIPTION MANAGER: Updated subscription for client '{client_id}' to topic '{topic}' with QoS {qos}")
    else:
        # adauga subscriptia noua
        new_subscription = {
            'topic': topic,
            'qos': qos,
            'no_local': subscribe_data.get('no_local', False),
            'retain_as_published': subscribe_data.get('retain_as_published', False),
            'retain_handling': subscribe_data.get('retain_handling', 0),
            'properties': properties,
            'timestamp': os.path.getmtime(SUBS_FILE) if os.path.exists(SUBS_FILE) else 0
        }
        subscriptions_db[client_id]['subscriptions'].append(new_subscription)
        print(
            f"SUBSCRIPTION MANAGER: Added new subscription for client '{client_id}' to topic '{topic}' with QoS {qos}")

    if packet_id and packet_id not in subscriptions_db[client_id]['packet_ids']:
        subscriptions_db[client_id]['packet_ids'].append(packet_id)

    save_subscriptions_database(subscriptions_db)

    return True

def load_subscriptions_database():
    if os.path.exists(SUBS_FILE):
        try:
            with open(SUBS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("WARNING: Corrupted subscriptions file, creating new one")
            return {}
    return {}

def save_subscriptions_database(subscriptions_db):
    with open(SUBS_FILE, 'w') as f:
        json.dump(subscriptions_db, f, indent=2)
    print(f"SUBSCRIPTION MANAGER: Saved {len(subscriptions_db)} clients' subscriptions to {SUBS_FILE}")

def get_subscribers_for_topic(topic):
    subscriptions_db = load_subscriptions_database()
    subscribers = []

    for client_id, client_data in subscriptions_db.items():
        for subscription in client_data.get('subscriptions', []):
            if subscription['topic'] == topic:
                subscribers.append({
                    'client_id': client_id,
                    'qos': subscription['qos'],
                    'subscription': subscription
                })

    return subscribers

def topics_match(topic_filter, topic_name):
    if topic_filter == topic_name:
        return True

    filter_parts = topic_filter.split('/')
    name_parts = topic_name.split('/')

    if '#' in filter_parts:
        if filter_parts[-1] != '#':
            return False

        for i in range(len(filter_parts) - 1):
            if i >= len(name_parts):
                return False
            if filter_parts[i] != '+' and filter_parts[i] != name_parts[i]:
                return False

        return True

    if len(filter_parts) != len(name_parts):
        return False

    for filter_part, name_part in zip(filter_parts, name_parts):
        if filter_part != '+' and filter_part != name_part:
            return False

    return True

def get_subscription_count(client_id):
    try:
        subscriptions_db = load_subscriptions_database()

        if client_id not in subscriptions_db:
            return 0

        subscriptions_list = subscriptions_db[client_id].get('subscriptions', [])
        return len(subscriptions_list)

    except Exception as e:
        print(f"SESSION MANAGER: Error getting subscription count: {e}")
        return 0