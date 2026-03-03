from collections.abc import Sized

from Parser_and_handlers.parser import encode_vbi
from Exceptions.program_related_except import ValueErr

def build_connack_packet(session_present=False, reason_code=0x00, properties=None):
    #Fixed header
    fixed_header = bytearray()
    fixed_header.append(0x20)

    #Variable header
    variable_header = bytearray()

    connack_flag = 0x01 if session_present else 0x00
    variable_header.append(connack_flag)

    variable_header.append(reason_code)

    try:
        if properties:
            #Se codifica proprietatile si lungimea acestora
            properties_bytes = build_connack_properties(properties)
            properties_length = len(properties_bytes)

            #Se face codificare VBI pt lungimea proprietatilor
            vbi_bytes = encode_vbi(properties_length)
            variable_header.extend(vbi_bytes)
            variable_header.extend(properties_bytes)
        else:
            variable_header.append(0x00)
    except ValueErr:
        '''In caz de ValueErr, avem Protocol Error(0x82), si schimbam reason code-ul din pachet
            Fiind CONNACK, in caz de eroare se inchide conexiunea clientului
        '''
        variable_header[1] = 0x82

    #calcul remaining length
    remaining_length = len(variable_header)
    remaining_length_bytes = encode_vbi(remaining_length)

    #pachet final
    packet = bytearray()
    packet.append(0x20)
    packet.extend(remaining_length_bytes)
    packet.extend(variable_header)

    return bytes(packet)


def build_connack_properties(properties):
    properties_bytes = bytearray()

    for prop_id, value in properties.items():
        match prop_id:
            case "Session Expiry Interval":
                properties_bytes.append(0x11)
                properties_bytes.extend(value.to_bytes(4,'big'))

            case "Receive Maximum":
                properties_bytes.append(0x21)
                if value==0:
                    raise ValueErr('Receive Maximum cannnot be 0')
                properties_bytes.extend(value.to_bytes(2,'big'))

            case "Maximum QoS":
                properties_bytes.append(0x24)
                if value not in [0, 1]:
                    raise ValueErr("Maximum QoS must be 0 or 1")
                properties_bytes.append(value)

            case "Retain Available":
                properties_bytes.append(0x25)
                if value not in [0, 1]:
                    raise ValueErr("Retain Available must be 0 or 1")
                properties_bytes.append(value)

            case "Maximum Packet Size":
                properties_bytes.append(0x27)
                if value == 0:
                    raise ValueErr("Maximum Packet Size cannot be 0")
                properties_bytes.append(value.to_bytes(4,'big'))

            case "Assigned Client Identifier":
                properties_bytes.append(0x12)
                str_bytes = value.encode('utf-8')
                properties_bytes.extend(len(str_bytes).to_bytes(2,'big'))
                properties_bytes.extend(str_bytes)

            case "Topic Alias Maximum":
                properties_bytes.append(0x22)
                properties_bytes.extend(value.to_bytes(2, 'big'))

            case "Reason String":
                properties_bytes.append(0x1F)
                str_bytes = value.encode('utf-8')
                properties_bytes.extend(len(str_bytes).to_bytes(2, 'big'))
                properties_bytes.extend(str_bytes)

            case "User Property":
                if isinstance(value, list):
                    for key_val_pair in value:
                        if isinstance(key_val_pair, tuple) and len(key_val_pair) == 2:
                            key, val = key_val_pair
                            properties_bytes.append(0x26)

                            # Encodare cheie
                            key_bytes = key.encode('utf-8')
                            properties_bytes.extend(len(key_bytes).to_bytes(2, 'big'))
                            properties_bytes.extend(key_bytes)

                            # Encodare valoare
                            if isinstance(val, int):
                                val1 = str(val)
                                val_bytes = val1.encode('utf-8')
                            else:
                                val_bytes = val.encode('utf-8')
                            properties_bytes.extend(len(val_bytes).to_bytes(2, 'big'))
                            properties_bytes.extend(val_bytes)
                elif isinstance(value, tuple) and len(value) == 2:
                    # Single user property pair
                    key, val = value
                    properties_bytes.append(0x26)

                    key_bytes = key.encode('utf-8')
                    properties_bytes.extend(len(key_bytes).to_bytes(2, 'big'))
                    properties_bytes.extend(key_bytes)

                    if isinstance(val, int):
                        val1 = str(val)
                        val_bytes = val1.encode('utf-8')
                    else:
                        val_bytes = val.encode('utf-8')
                    properties_bytes.extend(len(val_bytes).to_bytes(2, 'big'))
                    properties_bytes.extend(val_bytes)

            case "Wildcard Subscription Available":
                properties_bytes.append(0x28)
                if value not in [0, 1]:
                    raise ValueError("Wildcard Subscription Available must be 0 or 1")
                properties_bytes.append(value)

            case "Subscription Identifiers Available":
                properties_bytes.append(0x29)
                if value not in [0, 1]:
                    raise ValueError("Subscription Identifiers Available must be 0 or 1")
                properties_bytes.append(value)

            case "Shared Subscription Available":
                properties_bytes.append(0x2A)
                if value not in [0, 1]:
                    raise ValueError("Shared Subscription Available must be 0 or 1")
                properties_bytes.append(value)

            case "Server Keep Alive":
                properties_bytes.append(0x13)
                properties_bytes.extend(value.to_bytes(2, 'big'))

            case "Response Information":
                properties_bytes.append(0x1A)
                str_bytes = value.encode('utf-8')
                properties_bytes.extend(len(str_bytes).to_bytes(2, 'big'))
                properties_bytes.extend(str_bytes)

            case "Server Reference":
                properties_bytes.append(0x1C)
                str_bytes = value.encode('utf-8')
                properties_bytes.extend(len(str_bytes).to_bytes(2, 'big'))
                properties_bytes.extend(str_bytes)

            case "Authentification Method":
                properties_bytes.append(0x15)
                str_bytes = value.encode('utf-8')
                properties_bytes.extend(len(str_bytes).to_bytes(2, 'big'))
                properties_bytes.extend(str_bytes)

            case "Authentification Data":
                properties_bytes.append(0x16)
                # Value should be bytes for binary data
                if isinstance(value, bytes):
                    properties_bytes.extend(len(value).to_bytes(2, 'big'))
                    properties_bytes.extend(value)
                else:
                    print("Authentification Data must be bytes")

            case _:
                # Ignoră proprietățile necunoscute fără a ridica excepție
                print(f"Warning: Unknown property ID: {prop_id}, value: {value} - se va ignora")

    return bytes(properties_bytes)