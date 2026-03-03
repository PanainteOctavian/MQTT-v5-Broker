import os
import json
import time
import traceback
import Subscriptions.subscription as subscription
import Parser_and_handlers.parser as parser

MESSAGES_FILE = 'Message_routing/messagesDB.json'
RETAIN_FILE = 'Message_routing/retainDB.json'

def store_message_for_subscribers(topic, message_data):
    subscribers = subscription.get_subscribers_for_topic(topic)
    messages_db = load_messages_database()

    for subscriber in subscribers:
        client_id = subscriber['client_id']
        requested_qos = subscriber['qos']
        actual_qos = min(requested_qos, message_data['qos'])

        if client_id not in messages_db:
            messages_db[client_id] = []

        message_entry = {
            'topic': topic,
            'payload': message_data['payload'],
            'qos': actual_qos,
            'packet_id': message_data.get('packet_id'),
            'retain': message_data.get('retain', False),
            'dup': message_data.get('dup', False),
            'properties': message_data.get('properties', {}),
            'timestamp': time.time(),
            'status': 'pending',  # pending, delivered, acknowledged
            'publisher': message_data.get('client_id')
        }

        messages_db[client_id].append(message_entry)

    save_messages_database(messages_db)
    return len(subscribers)

def load_messages_database():
    if os.path.exists(MESSAGES_FILE):
        try:
            with open(MESSAGES_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("WARNING: Corrupted messages file, creating new one")
            return {}
    return {}

def save_messages_database(messages_db):
    with open(MESSAGES_FILE, 'w') as f:
        json.dump(messages_db, f, indent=2)

def store_retain_message(topic, message_data):
    retain_db = load_retain_database()

    if message_data['payload']:
        retain_db[topic] = {
            'payload': message_data['payload'],
            'qos': message_data['qos'],
            'properties': message_data.get('properties', {}),
            'timestamp': time.time(),
            'retain': True
        }
    else:
        retain_db.pop(topic, None)

    save_retain_database(retain_db)

def get_retain_message(topic):
    retain_db = load_retain_database()
    return retain_db.get(topic)

def load_retain_database():
    if os.path.exists(RETAIN_FILE):
        try:
            with open(RETAIN_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_retain_database(retain_db):
    with open(RETAIN_FILE, 'w') as f:
        json.dump(retain_db, f, indent=2)

def build_publish_packet(topic, payload, qos=0, retain=False, dup=False,
                         packet_id=None, properties=None):
    # FIXED HEADER
    fixed_header = 0x30

    # flaguri
    if dup:
        fixed_header |= 0x08  # DUP flag
    fixed_header |= (qos << 1)  # QoS
    if retain:
        fixed_header |= 0x01  # RETAIN

    # VARIABLE HEADER
    variable_header = bytearray()

    # Topic Name (utf-8 string)
    topic_bytes = topic.encode('utf-8')
    variable_header.extend(len(topic_bytes).to_bytes(2, 'big'))
    variable_header.extend(topic_bytes)

    # Packet Id (pt QoS 1 si 2)
    if qos > 0:
        if packet_id is None:
            raise ValueError("packet_id required for QoS > 0")
        variable_header.extend(packet_id.to_bytes(2, 'big'))

    # Properties
    if properties is None:
        properties = {}

    properties_bytes = build_publish_properties(properties)
    properties_length = len(properties_bytes)

    # proprietati
    variable_header.extend(parser.encode_vbi(properties_length))
    variable_header.extend(properties_bytes)

    # PAYLOAD
    if isinstance(payload, str):
        payload_bytes = payload.encode('utf-8')
    elif isinstance(payload, bytes):
        payload_bytes = payload
    elif payload is None:
        payload_bytes = b''
    else:
        payload_bytes = str(payload).encode('utf-8')

    # remaining length
    remaining_length = len(variable_header) + len(payload_bytes)
    remaining_length_bytes = parser.encode_vbi(remaining_length)

    packet = bytearray()
    packet.append(fixed_header)
    packet.extend(remaining_length_bytes)
    packet.extend(variable_header)
    packet.extend(payload_bytes)

    return bytes(packet)

def build_publish_properties(properties):
    properties_bytes = bytearray()

    for prop_id, value in properties.items():
        if prop_id == "Payload Format Indicator" or prop_id == 0x01:
            properties_bytes.append(0x01)
            properties_bytes.append(value)

        elif prop_id == "Message Expiry Interval" or prop_id == 0x02:
            properties_bytes.append(0x02)
            properties_bytes.extend(value.to_bytes(4, 'big'))

        elif prop_id == "Topic Alias" or prop_id == 0x23:
            properties_bytes.append(0x23)
            properties_bytes.extend(value.to_bytes(2, 'big'))

        elif prop_id == "Response Topic" or prop_id == 0x08:
            properties_bytes.append(0x08)
            str_bytes = value.encode('utf-8')
            properties_bytes.extend(len(str_bytes).to_bytes(2, 'big'))
            properties_bytes.extend(str_bytes)

        elif prop_id == "Correlation Data" or prop_id == 0x09:
            properties_bytes.append(0x09)
            if isinstance(value, bytes):
                properties_bytes.extend(len(value).to_bytes(2, 'big'))
                properties_bytes.extend(value)
            else:
                data = str(value).encode('utf-8')
                properties_bytes.extend(len(data).to_bytes(2, 'big'))
                properties_bytes.extend(data)

        elif prop_id == "User Property" or prop_id == 0x26:
            if isinstance(value, list):
                for key_val_pair in value:
                    if isinstance(key_val_pair, tuple) and len(key_val_pair) == 2:
                        key, val = key_val_pair
                        properties_bytes.append(0x26)

                        key_bytes = key.encode('utf-8')
                        properties_bytes.extend(len(key_bytes).to_bytes(2, 'big'))
                        properties_bytes.extend(key_bytes)

                        val_bytes = str(val).encode('utf-8')
                        properties_bytes.extend(len(val_bytes).to_bytes(2, 'big'))
                        properties_bytes.extend(val_bytes)
            elif isinstance(value, tuple) and len(value) == 2:
                key, val = value
                properties_bytes.append(0x26)

                key_bytes = key.encode('utf-8')
                properties_bytes.extend(len(key_bytes).to_bytes(2, 'big'))
                properties_bytes.extend(key_bytes)

                val_bytes = str(val).encode('utf-8')
                properties_bytes.extend(len(val_bytes).to_bytes(2, 'big'))
                properties_bytes.extend(val_bytes)

        elif prop_id == "Subscription Identifier" or prop_id == 0x0B:
            properties_bytes.append(0x0B)
            properties_bytes.extend(parser.encode_vbi(value))

        elif prop_id == "Content Type" or prop_id == 0x03:
            properties_bytes.append(0x03)
            str_bytes = value.encode('utf-8')
            properties_bytes.extend(len(str_bytes).to_bytes(2, 'big'))
            properties_bytes.extend(str_bytes)

        else:
            print(f"[Warning] Unknown PUBLISH property: {prop_id}")

    return bytes(properties_bytes)

def send_message_to_client(client_socket, client_id, message_data):
    # returneaza bool: True daca mesajul a fost trimis cu succes, False altfel
    try:
        topic = message_data.get('topic', '')
        payload = message_data.get('payload', '')
        qos = message_data.get('qos', 0)
        retain = message_data.get('retain', False)
        dup = message_data.get('dup', False)
        packet_id = message_data.get('packet_id')
        properties = message_data.get('properties', {})

        # validare QoS si packet_id
        if qos > 0 and packet_id is None:
            print(f"[Message Router] Error: QoS {qos} requires packet_id for client {client_id}")
            return False

        publish_packet = build_publish_packet(
            topic=topic,
            payload=payload,
            qos=qos,
            retain=retain,
            dup=dup,
            packet_id=packet_id,
            properties=properties
        )

        client_socket.send(publish_packet)

        print(f"[Message Router] Sent PUBLISH to client {client_id}: "
              f"topic='{topic}', QoS={qos}, retain={retain}, "
              f"payload_len={len(payload) if payload else 0}")

        return True

    except Exception as e:
        print(f"[Message Router] Error sending message to client {client_id}: {e}")
        traceback.print_exc()
        return False

def handle_retained_messages_on_connect(client_id, client_socket, clean_start):
    if clean_start:
        print(f"[Retained Messages] Client '{client_id}' connected with clean_start=1, skipping retained messages")
        return

    subscriptions_db = subscription.load_subscriptions_database()

    if client_id not in subscriptions_db:
        print(f"[Retained Messages] No subscriptions found for client '{client_id}'")
        return

    client_subscriptions = subscriptions_db[client_id].get('subscriptions', [])

    if not client_subscriptions:
        print(f"[Retained Messages] Client '{client_id}' has no active subscriptions")
        return

    print(f"[Retained Messages] Client '{client_id}' has {len(client_subscriptions)} subscription(s)")

    retain_db = load_retain_database()

    if not retain_db:
        print(f"[Retained Messages] No retained messages in database")
        return

    messages_sent = 0

    for sub in client_subscriptions:
        topic_filter = sub['topic']
        subscriber_qos = sub['qos']
        retain_handling = sub.get('retain_handling', 0)

        if retain_handling == 2:
            print(f"[Retained Messages] Skipping retained messages for topic '{topic_filter}' (retain_handling=2)")
            continue

        for retain_topic, retain_msg in retain_db.items():
            if subscription.topics_match(topic_filter, retain_topic):
                publisher_qos = retain_msg.get('qos', 0)
                effective_qos = min(publisher_qos, subscriber_qos)

                delivery_packet_id = None
                if effective_qos > 0:
                    delivery_packet_id = int(time.time() * 1000) % 65535

                delivery_message = {
                    'topic': retain_topic,
                    'payload': retain_msg.get('payload', ''),
                    'qos': effective_qos,
                    'retain': True,
                    'dup': False,
                    'packet_id': delivery_packet_id,
                    'properties': retain_msg.get('properties', {})
                }

                success = send_message_to_client(
                    client_socket,
                    client_id,
                    delivery_message
                )

                if success:
                    messages_sent += 1
                    print(f"[Retained Messages] Sent retained message to '{client_id}': "
                          f"topic='{retain_topic}', QoS={effective_qos}")
                else:
                    print(f"[Retained Messages] Failed to send retained message to '{client_id}': "
                          f"topic='{retain_topic}'")

    print(f"[Retained Messages] Sent {messages_sent} retained message(s) to client '{client_id}'")