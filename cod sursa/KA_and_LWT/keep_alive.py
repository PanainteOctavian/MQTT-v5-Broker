import threading
import time
import json
import os
import traceback
from datetime import datetime
import Parser_and_handlers.parser as parser
import Subscriptions.subscription as subscription
import Message_routing.message_router as message_router

KEEP_ALIVE_FILE = 'KA_and_LWT/keep_alive_db.json'

# dictionar global pentru conexiuni active
active_connections = {}
connections_lock = threading.Lock()

# thread de monitorizare Keep Alive
monitor_thread = None
monitor_running = False
monitor_stop_event = threading.Event()
monitor_started = False  # flag pentru a preveni pornirea multipla

def start_monitor():
    # porneste thread-ul de monitorizare Keep Alive
    global monitor_thread, monitor_running, monitor_started

    with connections_lock:
        if monitor_started:
            print("[Keep Alive Monitor] Already running (skipping)")
            return

        monitor_running = True
        monitor_started = True
        monitor_stop_event.clear()
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True, name="KeepAliveMonitor")
        monitor_thread.start()
        print("[Keep Alive Monitor] Started")

def register_client(client_id, client_socket, keep_alive, will_message=None):
    # inregistreaza un client nou cu Keep Alive interval
    # returneaza bool: True dacă inregistrarea a reusit, False daca clientul exista deja
    global active_connections

    with connections_lock:
        if client_id in active_connections:
            print(f"[Keep Alive Monitor] Client '{client_id}' already registered - updating")
            active_connections[client_id]['socket'] = client_socket
            active_connections[client_id]['keep_alive'] = keep_alive
            active_connections[client_id]['last_packet_time'] = time.time()
            active_connections[client_id]['will_message'] = will_message
            active_connections[client_id]['connected_at'] = datetime.now().isoformat()

            # recalc timeout-ul
            if keep_alive == 0:
                timeout = None
            else:
                timeout = keep_alive * 1.5
            active_connections[client_id]['timeout'] = timeout

            print(
                f"[Keep Alive Monitor] Updated client '{client_id}' with Keep Alive={keep_alive}s (timeout={timeout}s)")
            save_database()
            return True

        # timeout-ul = 1.5 x keep_alive
        if keep_alive == 0:
            timeout = None  # Keep alive NU exista
        else:
            timeout = keep_alive * 1.5

        active_connections[client_id] = {
            'socket': client_socket,
            'keep_alive': keep_alive,
            'timeout': timeout,
            'last_packet_time': time.time(),
            'will_message': will_message,
            'connected_at': datetime.now().isoformat(),
            'will_published': False,  # flag pentru LWT publicat
            'is_timeout_handled': False  # flag pentru a preveni tratarea multipla a timeout-ului
        }

        print(
            f"[Keep Alive Monitor] Registered client '{client_id}' with Keep Alive={keep_alive}s (timeout={timeout}s)")
        save_database()
        return True

def update_client_activity(client_id, packet_type="UNKNOWN"):
    # se apeleaza cand se trimite orice pachet
    global active_connections

    with connections_lock:
        if client_id in active_connections:
            active_connections[client_id]['last_packet_time'] = time.time()
            # reseteaza flag-ul de timeout handle daca clientul este activ
            active_connections[client_id]['is_timeout_handled'] = False

            if packet_type in ["PINGREQ", "PUBLISH", "SUBSCRIBE", "UNSUBSCRIBE"]:
                print(f"[Keep Alive Monitor] Updated activity for client '{client_id}' (packet: {packet_type})")
            return True
        else:
            print(f"[Keep Alive Monitor] Warning: Client '{client_id}' not found for activity update")
            return False


def unregister_client(client_id, graceful=True, reason=""):
    # sterge clientul cu id=client_id
    # returneaza LWT daca graceful=false, altfel None
    global active_connections

    with connections_lock:
        if client_id not in active_connections:
            print(f"[Keep Alive Monitor] Client '{client_id}' not found for unregister")
            return None

        connection_info = active_connections[client_id]
        will_message = None

        # verif daca LWT a fost deja publicat ca sa nu l publice de 2 ori
        if connection_info.get('will_published'):
            print(f"[Keep Alive Monitor] LWT already published for client '{client_id}'")
            will_message = None
        elif not graceful and connection_info.get('will_message'):
            will_message = connection_info['will_message']
            reason_text = f" - {reason}" if reason else ""
            print(f"[Keep Alive Monitor] Client '{client_id}' disconnected ungracefully{reason_text} - triggering LWT")
            connection_info['will_published'] = True
        else:
            reason_text = f" ({reason})" if reason else ""
            print(f"[Keep Alive Monitor] Client '{client_id}' disconnected gracefully{reason_text}")

        # salveaza informatiile
        saved_info = connection_info.copy()

        del active_connections[client_id]
        save_database()

        if will_message:
            return {'will_message': will_message, 'connection_info': saved_info}

        return None

def cleanup_all_connections():
    # clean up conexiuni la shutdown
    global active_connections

    with connections_lock:
        count = len(active_connections)
        for client_id in list(active_connections.keys()):
            connection_info = active_connections[client_id]

            # inchide socket-ul
            try:
                if connection_info['socket']:
                    connection_info['socket'].close()
            except:
                pass

            del active_connections[client_id]

        print(f"[Keep Alive Monitor] Cleaned up {count} connections")
        save_database()

def get_client_info(client_id):
    global active_connections

    with connections_lock:
        if client_id not in active_connections:
            return None

        info = active_connections[client_id].copy()
        info['inactive_time'] = time.time() - info['last_packet_time']
        info['status'] = 'active'
        if info['timeout'] and info['inactive_time'] > info['timeout']:
            info['status'] = 'timeout'

        if 'socket' in info:
            del info['socket']

        return info

def monitor_loop():
    # loop principal de monitorizare
    global monitor_running, active_connections

    CHECK_INTERVAL = 1  # check din secunda in secunda
    last_save_time = time.time()
    SAVE_INTERVAL = 30  # salvare la 30 de secunde

    print(f"[Keep Alive Monitor] Monitor loop started, check interval: {CHECK_INTERVAL}s")

    while not monitor_stop_event.is_set():
        try:
            current_time = time.time()
            clients_with_timeout = []

            with connections_lock:
                for client_id, info in active_connections.items():
                    # daca K.A.=0 dau skip
                    if info['timeout'] is None:
                        continue

                    inactive_time = current_time - info['last_packet_time']

                    # verif daca a expirat timeout-ul si nu a fost deja tratat
                    if inactive_time > info['timeout'] and not info.get('is_timeout_handled', False):
                        print(f"[Keep Alive Monitor] TIMEOUT detected for client '{client_id}' "
                              f"(inactive for {inactive_time:.1f}s, timeout={info['timeout']}s)")
                        # timeout-ul = detectat
                        active_connections[client_id]['is_timeout_handled'] = True
                        clients_with_timeout.append(client_id)

            for client_id in clients_with_timeout:
                handle_client_timeout(client_id)

            if current_time - last_save_time > SAVE_INTERVAL:
                save_database()
                last_save_time = current_time

            # sleep cu verif pentru stop rapid
            monitor_stop_event.wait(CHECK_INTERVAL)

        except Exception as e:
            print(f"[Keep Alive Monitor] Error in monitor loop: {e}")
            traceback.print_exc()
            # in caz de eroare, asteapta
            time.sleep(5)

def handle_client_timeout(client_id):
    global active_connections

    print(f"[Keep Alive Monitor] Handling timeout for client '{client_id}'")

    with connections_lock:
        if client_id not in active_connections:
            print(f"[Keep Alive Monitor] Client '{client_id}' not found for timeout handling")
            return

        connection_info = active_connections[client_id].copy()
        client_socket = connection_info.get('socket')

    if client_socket:
        try:
            print(f"[Keep Alive Monitor] Closing socket for client '{client_id}'")
            client_socket.close()
        except Exception as e:
            print(f"[Keep Alive Monitor] Error closing socket for '{client_id}': {e}")
    else:
        print(f"[Keep Alive Monitor] No socket to close for client '{client_id}'")

    result = unregister_client(client_id, graceful=False, reason="Keep Alive timeout")

    if result and 'will_message' in result:
        will_message = result['will_message']
        print(f"[Keep Alive Monitor] Publishing LWT for client '{client_id}'")
        publish_lwt(client_id, will_message)
    else:
        print(f"[Keep Alive Monitor] No LWT to publish for client '{client_id}'")

    print(f"[Keep Alive Monitor] Client '{client_id}' removed due to Keep Alive timeout")

def publish_lwt(client_id, will_message):
    try:
        # Will Delay Interval
        will_delay = will_message.get('properties', {}).get('Will Delay Interval', 0)
        if will_delay > 0:
            print(f"[Keep Alive Monitor] Waiting {will_delay}s before publishing LWT for '{client_id}'")
            time.sleep(will_delay)

        message_data = {
            'topic': will_message['topic'],
            'payload': will_message['payload'],
            'qos': will_message['qos'],
            'retain': will_message['retain'],
            'properties': will_message.get('properties', {}),
            'client_id': client_id,
            'dup': False,
            'packet_id': None,  # LWT NU are packet_id
            'timestamp': datetime.now().isoformat(),
            'is_lwt': True  # flag pt a identifica mesajele LWT
        }

        print(f"[Keep Alive Monitor] Publishing LWT for client '{client_id}': "
              f"topic='{will_message['topic']}', payload='{will_message['payload']}', "
              f"QoS={will_message['qos']}, retain={will_message['retain']}")

        # toti subscriberii pentru topic-ul LWT
        subscribers = subscription.get_subscribers_for_topic(will_message['topic'])

        if subscribers:
            print(f"[Keep Alive Monitor] Found {len(subscribers)} subscribers for LWT topic '{will_message['topic']}'")

            # stocheaza LWT
            num_stored = message_router.store_message_for_subscribers(will_message['topic'], message_data)

            print(f"[Keep Alive Monitor] LWT stored for {num_stored} subscribers")

            # retain LWT(daca e cazul)
            if will_message['retain']:
                message_router.store_retain_message(will_message['topic'], message_data)
                print(f"[Keep Alive Monitor] LWT stored as retain message for topic '{will_message['topic']}'")

            # trimitere mesaj direct prin socket
            with connections_lock:
                for sub in subscribers:
                    subscriber_id = sub['client_id']
                    if subscriber_id in active_connections:
                        subscriber_info = active_connections[subscriber_id]
                        try:
                            publish_packet = build_lwt_publish_packet(
                                will_message['topic'],
                                will_message['payload'],
                                will_message['qos'],
                                will_message['retain'],
                                sub['qos']
                            )

                            subscriber_info['socket'].send(publish_packet)
                            print(f"[Keep Alive Monitor] LWT sent to active subscriber '{subscriber_id}'")

                        except Exception as e:
                            print(f"[Keep Alive Monitor] Error sending LWT to subscriber '{subscriber_id}': {e}")
        else:
            print(f"[Keep Alive Monitor] No subscribers for LWT topic '{will_message['topic']}'")

            # retain LWT chiar daca NU exista subscriberi
            if will_message['retain']:
                message_router.store_retain_message(will_message['topic'], message_data)
                print(f"[Keep Alive Monitor] LWT stored as retain message (no active subscribers)")

    except ImportError as e:
        print(f"[Keep Alive Monitor] Error importing required modules: {e}")
    except Exception as e:
        print(f"[Keep Alive Monitor] Error publishing LWT for '{client_id}': {e}")
        traceback.print_exc()

def build_lwt_publish_packet(topic, payload, publisher_qos, retain, subscriber_qos):
    # QoS efectiv
    effective_qos = min(publisher_qos, subscriber_qos)

    # Fixed header
    fixed_header = 0x30  # PUBLISH
    fixed_header |= (effective_qos << 1)
    if retain:
        fixed_header |= 0x01

    # Variable header
    variable_header = bytearray()

    # Topic name (UTF-8 string)
    topic_bytes = topic.encode('utf-8')
    variable_header.extend(len(topic_bytes).to_bytes(2, 'big'))
    variable_header.extend(topic_bytes)

    # Packet ID (doar pentru QoS 1 sau 2)
    packet_id = 0
    if effective_qos > 0:
        # Generăm un packet_id unic pentru LWT
        packet_id = int(time.time() * 1000) % 65535
        variable_header.extend(packet_id.to_bytes(2, 'big'))

    # Properties
    properties = bytearray()
    # codul de proprietate pentru LWT (0x99 pentru "LWT flag")
    properties.append(0x99)
    properties.append(0x01)
    properties.append(0x01)

    # VBI pt props
    prop_length_bytes = parser.encode_vbi(len(properties))
    variable_header.extend(prop_length_bytes)
    variable_header.extend(properties)

    # Payload
    if isinstance(payload, str):
        payload_bytes = payload.encode('utf-8')
    elif payload is None:
        payload_bytes = b''
    else:
        payload_bytes = payload

    # remaining length
    remaining_length = len(variable_header) + len(payload_bytes)
    remaining_length_bytes = parser.encode_vbi(remaining_length)

    packet = bytearray()
    packet.append(fixed_header)
    packet.extend(remaining_length_bytes)
    packet.extend(variable_header)
    packet.extend(payload_bytes)

    return bytes(packet)

def save_database():
    global active_connections

    try:
        os.makedirs(os.path.dirname(KEEP_ALIVE_FILE), exist_ok=True)

        # pregatire date pt serializare
        serializable_data = {}
        current_time = time.time()

        for client_id, info in active_connections.items():
            serializable_data[client_id] = {
                'keep_alive': info['keep_alive'],
                'timeout': info['timeout'],
                'last_packet_time': info['last_packet_time'],
                'connected_at': info['connected_at'],
                'has_will': bool(info.get('will_message')),
                'will_published': info.get('will_published', False),
                'inactive_time': current_time - info['last_packet_time'],
                'is_timeout_handled': info.get('is_timeout_handled', False),
                'save_timestamp': current_time
            }

        # fisier temporar pt evitarea erorilor
        temp_file = KEEP_ALIVE_FILE + '.tmp'
        with open(temp_file, 'w') as f:
            json.dump(serializable_data, f, indent=2, default=str)

        # inlocuire fisier vechi
        if os.path.exists(KEEP_ALIVE_FILE):
            os.replace(temp_file, KEEP_ALIVE_FILE)
        else:
            os.rename(temp_file, KEEP_ALIVE_FILE)

    except Exception as e:
        print(f"[Keep Alive Monitor] Error saving database: {e}")

        try:
            if 'temp_file' in locals() and os.path.exists(temp_file):
                os.remove(temp_file)
        except:
            pass

def load_database():
    # funcția NU restaureaza socket-ul
    global active_connections

    try:
        if not os.path.exists(KEEP_ALIVE_FILE):
            print("[Keep Alive Monitor] No database file found")
            return {}

        with open(KEEP_ALIVE_FILE, 'r') as f:
            data = json.load(f)

        print(f"[Keep Alive Monitor] Loaded {len(data)} client records from database")
        return data

    except Exception as e:
        print(f"[Keep Alive Monitor] Error loading database: {e}")
        return {}

def get_stats():
    # fct pt statistici
    global active_connections

    with connections_lock:
        stats = {
            'total_clients': len(active_connections),
            'clients_with_keep_alive': 0,
            'clients_with_will': 0,
            'clients_timed_out': 0,
            'clients_active': 0,
            'clients_list': []
        }

        current_time = time.time()

        for client_id, info in active_connections.items():
            if info['keep_alive'] > 0:
                stats['clients_with_keep_alive'] += 1

            if info.get('will_message'):
                stats['clients_with_will'] += 1

            if info.get('is_timeout_handled', False):
                stats['clients_timed_out'] += 1
            else:
                stats['clients_active'] += 1

            inactive_time = current_time - info['last_packet_time']

            client_entry = {
                'client_id': client_id,
                'keep_alive': info['keep_alive'],
                'inactive_time': inactive_time,
                'has_will': bool(info.get('will_message')),
                'status': 'timeout' if info.get('is_timeout_handled', False) else 'active'
            }

            if info['timeout']:
                client_entry['timeout_remaining'] = max(0, info['timeout'] - inactive_time)

            stats['clients_list'].append(client_entry)

        return stats