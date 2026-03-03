import time
import Parser_and_handlers.parser as parser
import Auth_and_sessions.authentification_manager as authentification
import Auth_and_sessions.session_manager as session_manager
import Subscriptions.subscription as subscription
import Message_routing.message_router as message_router
import KA_and_LWT.keep_alive as keep_alive_manager
from Message_routing.message_router import handle_retained_messages_on_connect

connected_clients = {}

def handler(parsed_packet, client_socket=None):
    if parsed_packet is None:
        print("Invalid packet received")
        return None

    packet_type, flags, remaining_length, remaining_packet = parsed_packet

    client_id = connected_clients.get(client_socket) if client_socket else None

    match packet_type:
        case 1:
            result = connect_handler(remaining_packet, client_socket)
            if result and client_socket:
                connected_clients[client_socket] = result.get("client_id")
                client_id = result.get("client_id")
            return result
        case 14:
            disconnect_handler(remaining_packet, client_id)
            if client_socket and client_socket in connected_clients:
                client_id = connected_clients[client_socket]
                keep_alive_manager.unregister_client(client_id, graceful=True, reason="DISCONNECT packet")
                del connected_clients[client_socket]
        case 12:
            pingreq_handler(remaining_packet, client_id)
        case 8:
            result = subscribe_handler(remaining_packet, client_id)
            return result
        case 3:
            result = publish_handler(flags, remaining_packet, client_id)
            return result
        case _:
            print(f"Unhandled packet type: {packet_type}")

def connect_handler(remaining_packet, client_socket=None):

    if len(remaining_packet) < 10:
        print("CONNECT: Packet too short")
        return None

    current_pos = 0

    # --------------------
    # VARIABLE HEADER
    # Protocol name
    protocol_name, bytes_read = parser.parse_utf8_string(remaining_packet, current_pos)
    if protocol_name is None:
        print("CONNECT: Invalid protocol name")
        return None

    if protocol_name != "MQTT":
        print(f"CONNECT: Invalid protocol: {protocol_name}")
        return None

    current_pos += bytes_read

    # Protocol version
    version, bytes_read = parser.parse_byte(remaining_packet, current_pos)
    if version is None:
        print("CONNECT: Missing protocol version")
        return None

    if version != 5:
        print(f"CONNECT: Invalid protocol version: {version}")
        return None

    current_pos += bytes_read

    # Connect flags
    flags, bytes_read = parser.parse_byte(remaining_packet, current_pos)
    if flags is None:
        print("CONNECT: Missing connect flags")
        return None

    user_flag = (flags >> 7) & 1
    pass_flag = (flags >> 6) & 1
    will_retain = (flags >> 5) & 1
    will_qos = ((flags >> 3) & 0x03)
    will_flag = (flags >> 2) & 1
    clean_start = (flags >> 1) & 1
    reserved = flags & 1

    if reserved != 0 or will_qos == 3:
        print("CONNECT: Malformed packet-flags")
        return None

    current_pos += bytes_read

    # Keep alive
    keep_alive, bytes_read = parser.parse_two_byte_int(remaining_packet, current_pos)
    if keep_alive is None:
        print("CONNECT: Missing keep alive")
        return None

    current_pos += bytes_read

    # Properties
    properties_length, length_bytes = parser.decode_vbi(remaining_packet, current_pos)
    if properties_length is None:
        print("CONNECT: Invalid properties length encoding")
        return None

    current_pos += length_bytes
    properties = {}
    properties_end = current_pos + properties_length

    if properties_end > len(remaining_packet):
        print("CONNECT: Invalid properties length (extends beyond packet end)")
        return None

    properties_bytes = remaining_packet[current_pos:properties_end]
    prop_current_pos = 0

    while prop_current_pos < properties_length:
        if prop_current_pos >= len(properties_bytes):
            print("CONNECT: Malformed properties section")
            return None

        property_id, _ = parser.parse_byte(properties_bytes, prop_current_pos)
        prop_current_pos += 1

        match property_id:
            case 0x11:  # Session Expiry Interval (4 bytes)
                value, bytes_read = parser.parse_four_byte_int(properties_bytes, prop_current_pos)
                if value is None:
                    print(f"CONNECT: Property {hex(property_id)} too short")
                    return None
                properties['Session Expiry Interval'] = value
                prop_current_pos += bytes_read

            case 0x21:  # Receive Maximum (2 bytes)
                value, bytes_read = parser.parse_two_byte_int(properties_bytes, prop_current_pos)
                if value is None:
                    print(f"CONNECT: Property {hex(property_id)} too short")
                    return None
                properties['Receive Maximum'] = value
                prop_current_pos += bytes_read

            case 0x27:  # Maximum Packet Size (4 bytes)
                value, bytes_read = parser.parse_four_byte_int(properties_bytes, prop_current_pos)
                if value is None:
                    print(f"CONNECT: Property {hex(property_id)} too short")
                    return None
                properties['Maximum Packet Size'] = value
                prop_current_pos += bytes_read

            case 0x22:  # Topic Alias Maximum (2 bytes)
                value, bytes_read = parser.parse_two_byte_int(properties_bytes, prop_current_pos)
                if value is None:
                    print(f"CONNECT: Property {hex(property_id)} too short")
                    return None
                properties['Topic Alias Maximum'] = value
                prop_current_pos += bytes_read

            case 0x19:  # Request Response Information (1 byte)
                value, bytes_read = parser.parse_byte(properties_bytes, prop_current_pos)
                if value is None:
                    print(f"CONNECT: Property {hex(property_id)} too short")
                    return None
                properties['Request Response Information'] = value
                prop_current_pos += bytes_read

            case 0x17:  # Request Problem Information (1 byte)
                value, bytes_read = parser.parse_byte(properties_bytes, prop_current_pos)
                if value is None:
                    print(f"CONNECT: Property {hex(property_id)} too short")
                    return None
                properties['Request Problem Information'] = value
                prop_current_pos += bytes_read

            case 0x26:  # User Property (UTF-8 String Pair)
                key, value, bytes_read = parser.parse_utf8_string_pair(properties_bytes, prop_current_pos)
                if key is None:
                    print(f"CONNECT: Property {hex(property_id)} malformed")
                    return None
                if 'User Property' not in properties:
                    properties['User Property'] = []
                properties['User Property'].append((key, value))
                prop_current_pos += bytes_read

            case 0x15:  # Authentication Method (UTF-8 String)
                value, bytes_read = parser.parse_utf8_string(properties_bytes, prop_current_pos)
                if value is None:
                    print(f"CONNECT: Property {hex(property_id)} malformed")
                    return None
                properties['Authentication Method'] = value
                prop_current_pos += bytes_read

            case 0x16:  # Authentication Data (Binary Data)
                value, bytes_read = parser.parse_binary_data(properties_bytes, prop_current_pos)
                if value is None:
                    print(f"CONNECT: Property {hex(property_id)} malformed")
                    return None
                properties['Authentication Data'] = value
                prop_current_pos += bytes_read

            case _:
                print(f"CONNECT: Unknown property ID: {hex(property_id)}")
                return None

    current_pos = properties_end

    # --------------------
    # PAYLOAD
    # Client ID
    client_id_str, bytes_read = parser.parse_utf8_string(remaining_packet, current_pos)
    if client_id_str is None:
        print("CONNECT: Invalid client ID")
        return None

    current_pos += bytes_read

    # Initialize payload data
    will_topic = None
    will_payload = None
    will_properties = {}
    username = None
    password = None

    # Will Properties and Will Message (only if will_flag is set)
    if will_flag:
        # Will Properties
        will_properties_length, length_bytes = parser.decode_vbi(remaining_packet, current_pos)
        if will_properties_length is None:
            print("CONNECT: Invalid will properties length encoding")
            return None

        current_pos += length_bytes

        will_properties_end = current_pos + will_properties_length

        if will_properties_end > len(remaining_packet):
            print("CONNECT: Invalid will properties length (extends beyond packet end)")
            return None

        will_properties_bytes = remaining_packet[current_pos:will_properties_end]
        will_prop_pos = 0

        while will_prop_pos < will_properties_length:
            if will_prop_pos >= len(will_properties_bytes):
                print("CONNECT: Malformed will properties section")
                return None

            property_id, _ = parser.parse_byte(will_properties_bytes, will_prop_pos)
            will_prop_pos += 1

            match property_id:
                case 0x18:  # Will Delay Interval (4 bytes)
                    value, bytes_read = parser.parse_four_byte_int(will_properties_bytes, will_prop_pos)
                    if value is None:
                        print(f"CONNECT: Will Property {hex(property_id)} too short")
                        return None
                    will_properties['Will Delay Interval'] = value
                    will_prop_pos += bytes_read

                case 0x01:  # Payload Format Indicator (1 byte)
                    value, bytes_read = parser.parse_byte(will_properties_bytes, will_prop_pos)
                    if value is None:
                        print(f"CONNECT: Will Property {hex(property_id)} too short")
                        return None
                    will_properties['Payload Format Indicator'] = value
                    will_prop_pos += bytes_read

                case 0x02:  # Message Expiry Interval (4 bytes)
                    value, bytes_read = parser.parse_four_byte_int(will_properties_bytes, will_prop_pos)
                    if value is None:
                        print(f"CONNECT: Will Property {hex(property_id)} too short")
                        return None
                    will_properties['Message Expiry Interval'] = value
                    will_prop_pos += bytes_read

                case 0x03:  # Content Type (UTF-8 String)
                    value, bytes_read = parser.parse_utf8_string(will_properties_bytes, will_prop_pos)
                    if value is None:
                        print(f"CONNECT: Will Property {hex(property_id)} malformed")
                        return None
                    will_properties['Content Type'] = value
                    will_prop_pos += bytes_read

                case 0x08:  # Response Topic (UTF-8 String)
                    value, bytes_read = parser.parse_utf8_string(will_properties_bytes, will_prop_pos)
                    if value is None:
                        print(f"CONNECT: Will Property {hex(property_id)} malformed")
                        return None
                    will_properties['Response Topic'] = value
                    will_prop_pos += bytes_read

                case 0x09:  # Correlation Data (Binary Data)
                    value, bytes_read = parser.parse_binary_data(will_properties_bytes, will_prop_pos)
                    if value is None:
                        print(f"CONNECT: Will Property {hex(property_id)} malformed")
                        return None
                    will_properties['Correlation Data'] = value
                    will_prop_pos += bytes_read

                case 0x26:  # User Property (UTF-8 String Pair)
                    key, value, bytes_read = parser.parse_utf8_string_pair(will_properties_bytes, will_prop_pos)
                    if key is None:
                        print(f"CONNECT: Will Property {hex(property_id)} malformed")
                        return None
                    if 'User Property' not in will_properties:
                        will_properties['User Property'] = []
                    will_properties['User Property'].append((key, value))
                    will_prop_pos += bytes_read

                case _:
                    print(f"CONNECT: Unknown will property ID: {hex(property_id)}")
                    return None

        current_pos = will_properties_end

        # Will Topic
        will_topic_str, bytes_read = parser.parse_utf8_string(remaining_packet, current_pos)
        if will_topic_str is None:
            print("CONNECT: Invalid will topic")
            return None

        will_topic = will_topic_str
        current_pos += bytes_read

        # Will Payload
        will_payload_str, bytes_read = parser.parse_utf8_string(remaining_packet, current_pos)
        if will_payload_str is None:
            print("CONNECT: Invalid will payload")
            return None

        will_payload = will_payload_str
        current_pos += bytes_read

    # UserName (if user_flag is set)
    if user_flag:
        username_str, bytes_read = parser.parse_utf8_string(remaining_packet, current_pos)
        if username_str is None:
            print("CONNECT: Invalid username")
            return None

        username = username_str
        current_pos += bytes_read

    # Password (if pass_flag is set)
    if pass_flag:
        password_str, bytes_read = parser.parse_utf8_string(remaining_packet, current_pos)
        if password_str is None:
            print("CONNECT: Invalid password")
            return None

        password = password_str
        current_pos += bytes_read

    will_data = {
        'topic': will_topic,
        'payload': will_payload,
        'qos': will_qos,
        'retain': bool(will_retain),
        'properties': will_properties if will_properties else None
    } if will_flag else None

    connect_data = {
        'packet_type': 'CONNECT',
        'protocol': protocol_name,
        'version': version,
        'connect_flags': {
            'clean_start': bool(clean_start),
            'will_flag': bool(will_flag),
            'will_qos': will_qos,
            'will_retain': bool(will_retain),
            'user_flag': bool(user_flag),
            'pass_flag': bool(pass_flag)
        },
        'keep_alive': keep_alive,
        'properties': properties if properties else None,
        'client_id': client_id_str,
        'will': will_data,
        'username': username,
        'password': password
    }

    auth_code = authentification.authentification_manager(connect_data)

    if auth_code != 0x00:
        print(f"CONNECT: Authentication failed with code 0x{auth_code:02X}")
        return None

    session_result = session_manager.session_manager(connect_data)

    clean_start = connect_data['connect_flags']['clean_start']

    if not clean_start and session_result.get('session_present'):
        handle_retained_messages_on_connect(client_id_str, client_socket, clean_start)

    result = {
        'client_id': client_id_str,
        'auth_code': auth_code,
        'session_result': session_result,
        'connect_data': connect_data
    }

    return result

def disconnect_handler(remaining_packet, client_id):
    if len(remaining_packet) == 0:
        print("DISCONNECT PACKET SUMMARY")
        print("Normal disconnection (no reason code)")
        return 0

    current_pos = 0

    # ---------------
    # VARIABLE HEADER
    # Disconnect reason code
    disconnect_reason_code, bytes_read = parser.parse_byte(remaining_packet, current_pos)
    if disconnect_reason_code is None:
        print("DISCONNECT: Invalid disconnect reason code")
        return None

    current_pos += bytes_read

    # Properties
    properties = {}
    if current_pos < len(remaining_packet):
        properties_length, length_bytes = parser.decode_vbi(remaining_packet, current_pos)
        if properties_length is None:
            print("DISCONNECT: Invalid properties length encoding")
            return None

        current_pos += length_bytes
        properties_end = current_pos + properties_length

        if properties_end > len(remaining_packet):
            print("DISCONNECT: Invalid properties length (extends beyond packet end)")
            return None

        properties_bytes = remaining_packet[current_pos:properties_end]
        prop_current_pos = 0

        while prop_current_pos < properties_length:
            if prop_current_pos >= len(properties_bytes):
                print("DISCONNECT: Malformed properties section")
                return None

            property_id, _ = parser.parse_byte(properties_bytes, prop_current_pos)
            prop_current_pos += 1

            match property_id:
                case 0x11:  # Session Expiry Interval (4 bytes)
                    value, bytes_read = parser.parse_four_byte_int(properties_bytes, prop_current_pos)
                    if value is None:
                        print(f"DISCONNECT: Property {hex(property_id)} too short")
                        return None
                    properties['Session Expiry Interval'] = value
                    prop_current_pos += bytes_read

                case 0x1F:  # Reason String (UTF-8 String)
                    value, bytes_read = parser.parse_utf8_string(properties_bytes, prop_current_pos)
                    if value is None:
                        print(f"DISCONNECT: Property {hex(property_id)} malformed")
                        return None
                    properties['Reason String'] = value
                    prop_current_pos += bytes_read

                case 0X26:  # User Property (UTF-8 String Pair)
                    key, value, bytes_read = parser.parse_utf8_string_pair(properties_bytes, prop_current_pos)
                    if key is None:
                        print(f"DISCONNECT: Property {hex(property_id)} malformed")
                        return None
                    if 'User Property' not in properties:
                        properties['User Property'] = []
                    properties['User Property'].append((key, value))
                    prop_current_pos += bytes_read

                case 0x1C:  # Server Reference (UTF-8 String)
                    value, bytes_read = parser.parse_utf8_string(properties_bytes, prop_current_pos)
                    if value is None:
                        print(f"DISCONNECT: Property {hex(property_id)} malformed")
                        return None
                    properties['Server Reference'] = value
                    prop_current_pos += bytes_read

                case _:
                    print(f"DISCONNECT: Unknown property ID: {hex(property_id)}")
                    return None

        current_pos = properties_end

    # PAYLOAD - NU ARE
    if current_pos < len(remaining_packet):
        print("DISCONNECT: Malformed packet - unexpected data after properties")
        return None

    print("DISCONNECT PACKET SUMMARY")
    print(f"Reason Code: 0x{disconnect_reason_code:02X}")

    if properties:
        print("Properties:")
        for key, value in properties.items():
            if key == 'User Properties':
                print(f"  {key}:")
                for k, v in value:
                    print(f"    {k} = {v}")
            else:
                print(f"  {key}: {value}")
    else:
        print("No properties")

    print("=" * 60)

def pingreq_handler(remaining_packet, client_id):
    if len(remaining_packet) != 0:
        print("PINGREQ: Malformed packet")
        return None

    print("PINGREQ PACKET SUMMARY")
    print("Ping request received")
    print("Response: PINGRESP")
    print("=" * 60)

    # actualizeaza activitatea pentru Keep Alive
    if client_id:
        keep_alive_manager.update_client_activity(client_id, "PINGREQ")

    return True

def subscribe_handler(remaining_packet, client_id):
    if len(remaining_packet) < 3:
        print("SUBSCRIBE: Packet too short")
        return None

    current_pos = 0

    # --------------------
    # VARIABLE HEADER
    # Packet id
    packet_id, bytes_read = parser.parse_two_byte_int(remaining_packet, current_pos)
    if packet_id is None:
        print("SUBSCRIBE: Missing packet id")
        return None

    current_pos += bytes_read

    properties_length, length_bytes = parser.decode_vbi(remaining_packet, current_pos)
    if properties_length is None:
        print("SUBSCRIBE: Invalid properties length encoding")
        return None

    current_pos += length_bytes
    properties = {}
    properties_end = current_pos + properties_length

    if properties_end > len(remaining_packet):
        print("SUBSCRIBE: Invalid properties length (extends beyond packet end)")
        return None

    properties_bytes = remaining_packet[current_pos:properties_end]
    prop_current_pos = 0

    while prop_current_pos < properties_length:
        if prop_current_pos >= len(properties_bytes):
            print("SUBSCRIBE: Malformed properties section")
            return None

        property_id, _ = parser.parse_byte(properties_bytes, prop_current_pos)
        prop_current_pos += 1

        match property_id:
            case 0x0B:  # Subscription Identifier (vbi)
                subscription_id, bytes_read = parser.decode_vbi(properties_bytes, prop_current_pos)
                if subscription_id is None:
                    print("SUBSCRIBE: Invalid subscription_id encoding")
                    return None
                properties['Subscription Identifier'] = subscription_id
                prop_current_pos += bytes_read
            case 0x26:  # User Property (UTF-8 String Pair)
                key, value, bytes_read = parser.parse_utf8_string_pair(properties_bytes, prop_current_pos)
                if key is None:
                    print(f"SUBSCRIBE: Property {hex(property_id)} malformed")
                    return None
                if 'User Property' not in properties:
                    properties['User Property'] = []
                properties['User Property'].append((key, value))
                prop_current_pos += bytes_read
            case _:
                print(f"SUBSCRIBE: Unknown property ID: {hex(property_id)}")
                return None

    current_pos = properties_end

    # PAYLOAD
    topic_filters = []

    while current_pos < len(remaining_packet):
        # Parse topic filter
        topic_filter, bytes_read = parser.parse_utf8_string(remaining_packet, current_pos)
        if topic_filter is None:
            print("SUBSCRIBE: Invalid topic filter")
            return None

        current_pos += bytes_read

        # Parse subscription options (1 byte)
        if current_pos >= len(remaining_packet):
            print("SUBSCRIBE: Missing subscription options")
            return None

        subscription_options = remaining_packet[current_pos]
        current_pos += 1

        # Extract options bits
        retain_handling = (subscription_options >> 4) & 0x03
        retain_as_published = (subscription_options >> 3) & 0x01
        no_local = (subscription_options >> 2) & 0x01
        qos = subscription_options & 0x03

        # Validate QoS
        if qos == 3:
            print("SUBSCRIBE: Invalid QoS value (3)")
            return None

        topic_filters.append({
            'topic': topic_filter,
            'qos': qos,
            'no_local': bool(no_local),
            'retain_as_published': bool(retain_as_published),
            'retain_handling': retain_handling
        })

    if not topic_filters:
        print("SUBSCRIBE: No topic filters in payload")
        return None

    subscription_results = []
    for tf in topic_filters:
        subscription_data = {
            'client_id': client_id,
            'packet_id': packet_id,
            'topic': tf['topic'],
            'qos': tf['qos'],
            'no_local': tf['no_local'],
            'retain_as_published': tf['retain_as_published'],
            'retain_handling': tf['retain_handling'],
            'properties': properties  # Include subscription properties
        }

        # Store subscription in the subscription manager
        subscription.subscription_manager(subscription_data)

        # Record result for SUBACK response
        subscription_results.append({
            'topic': tf['topic'],
            'qos': tf['qos'],
            'success': True  # Assuming successful subscription
        })

    print(f"SUBSCRIBE: Client '{client_id}' subscribed to {len(topic_filters)} topics")
    for tf in topic_filters:
        print(f"  - Topic: {tf['topic']}, QoS: {tf['qos']}")

    return {
        'packet_id': packet_id,
        'properties': properties,
        'topic_filters': topic_filters,
        'client_id': client_id,
        'subscription_results': subscription_results
    }

def publish_handler(flags, remaining_packet, client_id):
    dup_flag = (flags >> 3) & 1
    qos = (flags >> 1) & 0b11
    retain = flags & 0b1
    if dup_flag != 0 and qos == 0:
        print("PUBLISH: dup_flag != 0 for qos = 0")
        return None
    if qos == 3:
        print("PUBLISH: qos flag = 3")
        return None # => disconnect cu reason code 0x81

    current_pos = 0

    # VARIABLE HEADER
    # Topic name
    topic_name, bytes_read = parser.parse_utf8_string(remaining_packet, current_pos)
    if topic_name is None:
        print("PUBLISH: Invalid topic name")
        return None

    if '*' in topic_name:
        print("PUBLISH: Topic name contains '*'")
        return None

    current_pos += bytes_read

    # Packet id
    packet_id = None
    if qos > 0:
        packet_id, bytes_read = parser.parse_two_byte_int(remaining_packet, current_pos)
        if packet_id is None:
            print("PUBLISH: Missing packet_id for QoS > 0")
            return None
        current_pos += bytes_read

    # Properties
    properties_length, length_bytes = parser.decode_vbi(remaining_packet, current_pos)
    if properties_length is None:
        print("PUBLISH: Invalid properties length encoding")
        return None

    current_pos += length_bytes
    properties = {}
    properties_end = current_pos + properties_length

    if properties_end > len(remaining_packet):
        print("PUBLISH: Invalid properties length (extends beyond packet end)")
        return None

    properties_bytes = remaining_packet[current_pos:properties_end]
    prop_current_pos = 0

    while prop_current_pos < properties_length:
        if prop_current_pos >= len(properties_bytes):
            print("SUBSCRIBE: Malformed properties section")
            return None

        property_id, _ = parser.parse_byte(properties_bytes, prop_current_pos)
        prop_current_pos += 1

        match property_id:
            case 0x01: # Payload Format Indicator (1 byte)
                value, bytes_read = parser.parse_byte(properties_bytes, prop_current_pos)
                if value is None:
                    print(f"PUBLISH: Will Property {hex(property_id)} too short")
                    return None
                properties['Payload Format Indicator'] = value
                prop_current_pos += bytes_read
            case 0x02:  # Message Expiry Interval` (4 byte)
                value, bytes_read = parser.parse_four_byte_int(properties_bytes, prop_current_pos)
                if value is None:
                    print(f"PUBLISH: Property {hex(property_id)} too short")
                    return None
                properties['Message Expiry Interval'] = value
                prop_current_pos += bytes_read
            case 0x23: # Topic Alias (2 byte)
                value, bytes_read = parser.parse_two_byte_int(properties_bytes, prop_current_pos)
                if value is None:
                    print(f"PUBLISH: Property {hex(property_id)} too short")
                    return None
                properties['Topic Alias'] = value
                prop_current_pos += bytes_read
            case 0x08: # Response Topic (utf string)
                value, bytes_read = parser.parse_utf8_string(properties_bytes, prop_current_pos)
                if value is None:
                    print(f"PUBLISH: Property {hex(property_id)} malformed")
                    return None
                properties['Response Topic'] = value
                prop_current_pos += bytes_read
            case 0x09: # Correlation Data (binary data)
                value, bytes_read = parser.parse_binary_data(properties_bytes, prop_current_pos)
                if value is None:
                    print(f"PUBLISH: Property {hex(property_id)} malformed")
                    return None
                properties['Correlation Data'] = value
                prop_current_pos += bytes_read
            case 0x26: # User Property (utf string pair)
                key, value, bytes_read = parser.parse_utf8_string_pair(properties_bytes, prop_current_pos)
                if key is None:
                    print(f"PUBLISH: Property {hex(property_id)} malformed")
                    return None
                if 'User Property' not in properties:
                    properties['User Property'] = []
                properties['User Property'].append((key, value))
                prop_current_pos += bytes_read
            case 0x0B: # Subscription Identifier (vbi)
                subscription_id, bytes_read = parser.decode_vbi(properties_bytes, prop_current_pos)
                if subscription_id is None:
                    print("PUBLISH: Invalid subscription_id encoding")
                    return None
                properties['Subscription Identifier'] = subscription_id
                prop_current_pos += bytes_read
            case 0x03: # Content Type (utf string)
                value, bytes_read = parser.parse_utf8_string(properties_bytes, prop_current_pos)
                if value is None:
                    print(f"PUBLISH: Property {hex(property_id)} malformed")
                    return None
                properties['Content Type'] = value
                prop_current_pos += bytes_read
            case _:
                print(f"SUBSCRIBE: Unknown property ID: {hex(property_id)}")
                return None

    current_pos = properties_end

    # PAYLOAD - format text
    payload_bytes = remaining_packet[current_pos:]
    if payload_bytes:
        payload = ''.join([chr(byte) for byte in payload_bytes])
    else:
        payload = ""

    '''
    print("PUBLISH PACKET SUMMARY")
    print(f"Topic: {topic_name}")
    print(f"QoS: {qos}")
    print(f"Retain: {bool(retain)}")
    print(f"DUP: {bool(dup_flag)}")
    if packet_id is not None:
        print(f"Packet ID: {packet_id}")

    if properties:
        print("Properties:")
        for key, value in properties.items():
            if key == 'User Property':
                print(f"  {key}:")
                for k, v in value:
                    print(f"    {k} = {v}")
            else:
                print(f"  {key}: {value}")

    print(f"Payload Length: {len(payload_bytes)} bytes")
    if payload:
        print(f"Payload: {payload}")
    else:
        print("Payload: (empty)")

    print("=" * 60)
    '''

    message_data = {
        'topic': topic_name,
        'qos': qos,
        'packet_id': packet_id,
        'payload': payload,
        'properties': properties,
        'client_id': client_id,
        'retain': bool(retain),
        'dup': bool(dup_flag)
    }

    is_lwt = False
    if properties and 0x99 in properties.values():
        is_lwt = True
    elif 'is_lwt' in locals():
        is_lwt = True

    message_data['is_lwt'] = is_lwt

    subscribers = subscription.get_subscribers_for_topic(topic_name)

    if retain:
        print(f"PUBLISH: Storing retain message for topic '{topic_name}'")
        message_router.store_retain_message(topic_name, message_data)

    if subscribers:
        print(f"PUBLISH: Found {len(subscribers)} subscribers for topic '{topic_name}'")

        num_stored = message_router.store_message_for_subscribers(topic_name, message_data)
        print(f"PUBLISH: Stored message for {num_stored} subscribers")

        # trimiterea propiu zisa a pachetelor
        for sub in subscribers:
            subscriber_id = sub['client_id']
            subscriber_qos = sub['qos']

            print(f"  - Client: {subscriber_id}, QoS: {subscriber_qos}")

            subscriber_socket = None
            for sock, sock_client_id in connected_clients.items():
                if sock_client_id == subscriber_id:
                    subscriber_socket = sock
                    break

            if subscriber_socket:
                # client online - trimitere imediata
                # negociere QoS= min(publisher_qos, subscriber_qos)
                effective_qos = min(qos, subscriber_qos)

                # generare packet_id daca QoS > 0
                delivery_packet_id = None
                if effective_qos > 0:
                    delivery_packet_id = int(time.time() * 1000) % 65535

                delivery_message = {
                    'topic': topic_name,
                    'payload': payload,
                    'qos': effective_qos,
                    'retain': bool(retain),
                    'dup': False,
                    'packet_id': delivery_packet_id,
                    'properties': properties
                }

                success = message_router.send_message_to_client(
                    subscriber_socket,
                    subscriber_id,
                    delivery_message
                )

                if success:
                    print(f"[DELIVERED] Message sent to online subscriber '{subscriber_id}'")
                else:
                    print(f"[FAILED] Could not send to subscriber '{subscriber_id}'")
            else:
                print(f"[OFFLINE] Subscriber '{subscriber_id}' is offline - message stored")

            # retain messages
            if retain:
                retain_msg = message_router.get_retain_message(topic_name)
                if retain_msg:
                    print(f"Retain message available for topic '{topic_name}'")

    else:
        print(f"PUBLISH: No subscribers for topic '{topic_name}'")
        if retain:
            print(f"PUBLISH: Stored retain message (no active subscribers)")

    return {
        'topic': topic_name,
        'qos': qos,
        'packet_id': packet_id,
        'payload': payload,
        'properties': properties,
        'client_id': client_id,
        'retain': bool(retain),
        'dup': bool(dup_flag),
        'subscribers': subscribers,
        'stored_count': len(subscribers) if subscribers else 0
    }