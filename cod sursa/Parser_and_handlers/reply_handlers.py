import socket

from Parser_and_handlers.handlers import connected_clients
from Parser_and_handlers.parser import *
from Exceptions.program_related_except import (value_is_None, packet_is_not_qos_related,
                                               packet_is_not_subscribe_related)
from Parser_and_handlers.reason_code import reason_code_messages

'''Folosita pt a selecta lista de reason code potrivita cu pachetul'''
def select_reason_code_list(packet_type):
    match packet_type:
        case 'PUBACK' | 'PUBREC':
            return [0x00,0x10,0x80,0x83,0x87,0x90,0x91,0x97,0x99]
        case 'PUBREL' | 'PUBCOMP':
            return [0x00,0x92]
        case 'SUBACK':
            return [0x00,0x01,0x02,0x80,0x83,0x87,0x8F,0x91,0x97,0x9E,0xA1,0xA2]
        case 'UNSUBACK':
            return [0x00,0x11,0x80,0x83,0x87,0x8F,0x91]
        case _:
            print('Only PUBACK,PUBREC,PUBREL and PUBCOMP are accepted here')
            return None


def reply_handler(parsed_packet,client_socket = None):
    if parsed_packet is None:
        print("Invalid packet received")
        return None

    packet_type, flags, remaining_length, remaining_packet = parsed_packet

    client_id = connected_clients.get(client_socket) if client_socket else None

    return_data=None

    match packet_type:
        case 2: #CONNACK
            connack_handler(remaining_packet,client_id)
        case 4: #PUBACK
            pub_reply_qos_handler(remaining_packet,client_id,'PUBACK')
        case 5: #PUBREC
            return_data = pub_reply_qos_handler(remaining_packet, client_id, 'PUBREC')
        #case 6: #PUBREL
            #pub_reply_qos_handler(remaining_packet, client_id, 'PUBREL') - se ocupa client-ul de el
        case 7: #PUBCOMP
            pub_reply_qos_handler(remaining_packet, client_id, 'PUBCOMP')
        case 9: #SUBACK
            suback_unsuback_handler(remaining_packet,client_id,'SUBACK')
        case 11: #UNSUBACK
            suback_unsuback_handler(remaining_packet, client_id, 'UNSUBACK')
        case 13: #PINRESP
            pingresp_handler(remaining_packet)

    return return_data

def pingresp_handler(remaining_packet):
    #nu trebuie sa aiba payload
    if len(remaining_packet) != 0:
        print("PINGRESP: Malformed packet")
        return None

    print('PINGRESP PACKET SUMMARY')
    print('Ping request responded')
    print("=" * 60)

def connack_handler(remaining_packet,client_id:socket.socket):
    if len(remaining_packet)<2:
        print('CONNACK packet is too short')
        return None

    current_pos=0

    '''Variable Header'''
    # Connect Acknowledge Flags (1 byte)
    connack_flags, bytes_read = parse_byte(remaining_packet,current_pos)
    if connack_flags is None:
        print('CONNACK: Missing connect acknowledge flags')

    #Extragere flag-uri
    session_present = connack_flags & 1
    reserved_bits = (connack_flags>>1) & 0x7F

    #reserved_bits neaparat trebuie sa fie 0
    if reserved_bits!=0:
        print('CONNACK: Reserved bits not zero')
        return None

    current_pos+=bytes_read #mai inaintam o pozitie

    # Reason Code (1 byte)
    reason_code, bytes_read = parse_byte(remaining_packet,current_pos)
    if reason_code is None:
        print('CONNACK: Missing reason code')
        return None

    #reason code-uri valabile pt CONNACK
    valid_reason_code = [0x00,0x80,0x81,0x82,0x83,0x84,0x85,0x86,0x87,0x88,0x89,
                         0x8A,0x8C,0x90,0x95,0x97,0x99,0x9A,0x9B,0x9C,0x9D,0x9F]

    if reason_code not in valid_reason_code:
        print('CONNACK: Invalid reason code')
        return None
    current_pos+=bytes_read

    '''Properties'''
    properties={}
    if current_pos< len(remaining_packet):
        properties_length, length_bytes = decode_vbi(remaining_packet,current_pos)
        if properties_length is None:
            print('CONNACK: Invalid properties length encoding')
            return None

        current_pos+=length_bytes #avans in pozitie
        properties_end = current_pos + properties_length #capatul drept al proprietatilor

        if properties_end>len(remaining_packet):
            print('CONNACK: Invalid properties length')
            return None

        if properties_length>0:
            properties_bytes = remaining_packet[current_pos:properties_end]
            property_current_pos = 0

            while property_current_pos<properties_length:
                if property_current_pos>=len(properties_bytes):
                    print('CONNACK: Malformed properties')
                    return None

                property_id,_ = parse_byte(properties_bytes,property_current_pos)
                property_current_pos+=1

                match property_id:
                    case 0x11: #Session Expiry Interval(4 bytes)
                        value, bytes_read = parse_four_byte_int(properties_bytes,property_current_pos)
                        if value_is_None(value,property_id,'CONNACK'):
                            return None
                        properties['Session Expiry Interval'] = value
                        property_current_pos+= bytes_read #avans

                    case 0x21: #Receive Maximum (2 bytes)
                        value, bytes_read = parse_two_byte_int(properties_bytes,property_current_pos)
                        if value_is_None(value,property_id,'CONNACK'):
                            return None
                        properties['Receive Maximum'] = value
                        property_current_pos+= bytes_read

                    case 0x24: #Maximum QoS (1 byte)
                        value, bytes_read = parse_byte(properties_bytes,property_current_pos)
                        if value_is_None(value,property_id,'CONNACK'):
                            return None
                        if value not in [0,1]:
                            print('CONNACK: Invalid maximum QoS available')
                            return None
                        properties['Maximum QoS'] = value
                        property_current_pos += bytes_read

                    case 0x25: #Retain Available (1 byte)
                        value, bytes_read = parse_byte(properties_bytes, property_current_pos)
                        if value_is_None(value, property_id, 'CONNACK'):
                            return None
                        if value not in [0, 1]:
                            print('CONNACK: Invalid Retain Value')
                            return None
                        properties['Retain Available'] = value
                        property_current_pos += bytes_read

                    case 0x27: #Maximum packet size(4 bytes)
                        value, bytes_read = parse_four_byte_int(properties_bytes,property_current_pos)
                        if value_is_None(value, property_id, 'CONNACK') or value==0:
                            return None
                        properties['Maximum Packet Size'] = value
                        property_current_pos += bytes_read

                    case 0x12: #Assigned Client Identifier( UTF-8 string)
                        value,bytes_read = parse_utf8_string(properties_bytes,property_current_pos)
                        if value_is_None(value, property_id, 'CONNACK'):
                            return None
                        properties['Assigned Client Identifier'] = value
                        property_current_pos += bytes_read

                    case 0x22: #Topic Alias Maximum(2 bytes)
                        value, bytes_read = parse_two_byte_int(properties_bytes,property_current_pos)
                        if value_is_None(value, property_id, 'CONNACK'):
                            return None
                        properties['Topic Alias Maximum'] = value
                        property_current_pos += bytes_read

                    case 0x1f: #Reason String(UTF-8 string)
                        value, bytes_read = parse_utf8_string(properties_bytes,property_current_pos)
                        if value_is_None(value, property_id, 'CONNACK'):
                            return None
                        properties['Reason String'] = '[Redacted]' # nu se parseaza de catre client
                        property_current_pos+= bytes_read

                    case 0x26: #User property(UTF-8 string pair)
                        key, value, bytes_read = parse_utf8_string_pair(properties_bytes, property_current_pos)
                        if value_is_None(key,property_id,'CONNACK'):
                            return None
                        if 'User Property' not in properties:
                            properties['User Property']=[]
                        properties['User Property'].append((key,value)) #se creeaza un hash map (cheie, valoare)
                        property_current_pos += bytes_read

                    case 0x28: #Wildcard subscription available(1 byte) - daca serverul il suporta sau nu
                        value, bytes_read = parse_byte(properties_bytes,property_current_pos)
                        if value_is_None(value,property_id,'CONNACK'):
                            return None
                        if value not in [0,1]:
                            print('CONNACK: Invalid Wildcard Subscription value')
                            return None
                        properties['Wildcard Subscription Available'] = value
                        property_current_pos += bytes_read

                    case 0x29: #Subscription Identifiers available(1 byte) - daca serverul il suporta sau nu
                        value, bytes_read = parse_byte(properties_bytes, property_current_pos)
                        if value_is_None(value, property_id, 'CONNACK'):
                            return None
                        if value not in [0, 1]:
                            print('CONNACK: Invalid Wildcard Subscription value')
                            return None
                        properties['Subscription Identifiers Available'] = value
                        property_current_pos += bytes_read

                    case 0x2a: #Shared Subscription available(1 byte)
                        value, bytes_read = parse_byte(properties_bytes, property_current_pos)
                        if value_is_None(value, property_id, 'CONNACK'):
                            return None
                        if value not in [0, 1]:
                            print('CONNACK: Invalid Wildcard Subscription value')
                            return None
                        properties['Shared Subscription Available'] = value
                        property_current_pos += bytes_read

                    case 0x13: #server keep alive(2 bytes)
                        value, bytes_read = parse_two_byte_int(properties_bytes,property_current_pos)
                        if value_is_None(value, property_id, 'CONNACK'):
                            return None
                        properties['Keep Alive'] = value
                        property_current_pos += bytes_read

                    case 0x1A: #Response information(UTF-8 string)
                        value,bytes_read = parse_utf8_string(properties_bytes,property_current_pos)
                        if value_is_None(value, property_id, 'CONNACK'):
                            return None
                        properties['Response Information'] = value
                        property_current_pos += bytes_read

                    case 0x1c: #Server reference(UTF-8 string)
                        value, bytes_read = parse_utf8_string(properties_bytes, property_current_pos)
                        if value_is_None(value, property_id, 'CONNACK'):
                            return None
                        properties['Server Reference'] = value
                        property_current_pos += bytes_read

                    case 0x15: #Authentification method(UTF-8 string)
                        value, bytes_read = parse_utf8_string(properties_bytes, property_current_pos)
                        if value_is_None(value, property_id, 'CONNACK'):
                            return None
                        properties['Authentification Method'] = value
                        property_current_pos += bytes_read

                    case 0x16: #Authentification data(Binary Data)
                        value, bytes_read = parse_binary_data(properties_bytes,property_current_pos)
                        if value_is_None(value, property_id, 'CONNACK'):
                            return None
                        properties['Authentification Data'] = value
                        property_current_pos += bytes_read

                    case _: #cand nu este niciun match
                        print('CONNACK: Unknown property ID')

            current_pos = properties_end

    '''Nu exista Payload'''
    if current_pos<len(remaining_packet):
        print('CONNACK: Malformed packet - CONNACK does not have Payload')
        return None

    connack_data={
        'packet_type': 'CONNACK',
        'session_present': bool(session_present),
        'reason_code': reason_code,
        'properties': properties if properties else None,
        'client_id': client_id
    }

    print("CONNACK PACKET SUMMARY")
    print(f"Session Present: {bool(session_present)}")
    print(f"Reason Code: 0x{reason_code:02X}")

    reason_message = reason_code_messages.get(reason_code,'Unknown reason code')
    if reason_code==0x00:
        print(f"Reason message: {reason_message[0]}")
    else:
        print(f"Reason message: {reason_message}")

    if properties:
        print('Properties')
        for key,value in properties.items():
            if key=='User Property':
                print(f"    {key}:")
                for k,v in value:
                    print(f"        {k} = {v}")
            else:
                print(f'    {key}: {value}')
    else:
        print('No properties')

    print('='*60)
    return connack_data

'''
Dev note:
    Se poate observa ca PUBACK,PUBCOMP,PUBREL si PUBREC au pachete similare ca constructie
    Cu ajutorul unei generalizari, se poate economisi memorie in program
    Din start se verifica ca packet_type sa fie din cele de mai sus pt a nu gestiona pachete incompatibile
'''
def pub_reply_qos_handler(remaining_packet,client_id: socket.socket, packet_type):
    if packet_is_not_qos_related(packet_type):
        return None

    if len(remaining_packet)<2:
        print(f'{packet_type}: Packet too short')
        return None

    current_position = 0

    '''Variable Header'''
    #Packet Identifier(2 bytes)
    packet_id, bytes_read = parse_two_byte_int(remaining_packet,current_position)
    if packet_id is None:
        print(f'{packet_type}: Missing packet identifier')
        return None

    if packet_id==0:
        print(f'{packet_type}: Invalid Packet Identifier (cannot be 0)')
        return None
    current_position+=bytes_read

    #Reason Code(1 byte)
    reason_code = 0x00 #by default; when we don't have reason code
    if current_position<len(remaining_packet): #we still have bytes to read
        reason_code_val, bytes_read = parse_byte(remaining_packet, current_position)
        if reason_code_val is None:
            print(f'{packet_type}: Invalid reason code; non-existent')
            return None

        valid_reason_codes = select_reason_code_list(packet_type)
        if reason_code_val not in valid_reason_codes:
            print(f'{packet_type}: Invalid reason code; not in PUBACK reason code list')
            return None

        reason_code = reason_code_val
        current_position+= bytes_read

    #Properties
    properties = {}
    if current_position<len(remaining_packet):
        #Properties length(variable byte integer)
        properties_length, length_bytes = decode_vbi(remaining_packet, current_position)
        if properties_length is None:
            print(f'{packet_type}: Invalid properties length encoding')
            return None

        current_position+=length_bytes
        properties_end = current_position+properties_length

        if properties_end>len(remaining_packet):
            print(f'{packet_type}: Invalid properties length(extends beyond the packet end)')
            return None

        if properties_length>0:
            properties_bytes = remaining_packet[current_position:properties_end]
            prop_current_pos = 0

            while prop_current_pos<properties_length:
                if prop_current_pos>=len(properties_bytes):
                    print(f'{packet_type}: Malformed properties section')
                    return None

                property_id, _ = parse_byte(properties_bytes,prop_current_pos)
                prop_current_pos+=1

                match property_id:
                    case 0x1F: #Reason String(UTF-8 string)
                        value, bytes_read = parse_utf8_string(properties_bytes,prop_current_pos)
                        if value_is_None(value,property_id,packet_type):
                            return None
                        properties['Reason String'] = value
                        prop_current_pos += bytes_read

                    case 0x26: #User Property(UTF-8 String Pair)
                        key, value, bytes_read = parse_utf8_string_pair(properties_bytes,prop_current_pos)
                        if value_is_None(key,property_id,packet_type):
                            return None
                        if 'User Property' not in properties:
                            properties['User Property'] = []
                        properties['User Property'].append((key,value))
                        prop_current_pos += bytes_read

                    case _: #nicio proprietate a pachetelor de reply la PUBLISH in QoS>0
                        print(f'{packet_type}: Unknown property ID')
                        return None

            current_position = properties_end

    '''No Payload'''
    if current_position<len(remaining_packet):
        print(f'{packet_type}: Malformed packet - {packet_type} does not have payload')
        return None

    '''Continutul extras din pachetul trimis'''
    reply_data={
        'packet_type': packet_type,
        'packet_id': packet_id,
        'reason_code': reason_code,
        'properties': properties if properties else None,
        'client_id': client_id
    }

    print(f'{packet_type} PACKET SUMMARY')
    print(f"Packet ID: {packet_id}")
    print(f"Reason Code: 0x{reason_code:02X}")

    reason_message = reason_code_messages.get(reason_code,'Unknown reason code')
    if reason_code==0x00:
        print(f'Reason message: {reason_message[0]}')
    else:
        print(f'Reason message: {reason_message}')

    if properties:
        print('Properties')
        for key,value in properties.items():
            if key=='User Property':
                print(f"    {key}:")
                for k,v in value:
                    print(f"        {k} = {v}")
            else:
                print(f'    {key}: {value}')
    else:
        print('No properties')

    print('='*60)

    return reply_data #returnam datele obtinute

'''Ultimele 2 pachete au proprietati similare, dar payload cu reason code diferit'''
def suback_unsuback_handler(remaining_packet,client_id: socket.socket, packet_type):
    if packet_is_not_subscribe_related(packet_type):
        return None

    if len(remaining_packet)<2:
        print(f'{packet_type}: Packet too short')
        return None

    current_position = 0

    '''Variable Header'''
    #Packet Identifier(2 bytes)
    packet_id, bytes_read = parse_two_byte_int(remaining_packet,current_position)
    if packet_id is None:
        print(f'{packet_type}: Missing packet identifier')
        return None

    if packet_id==0:
        print(f'{packet_type}: Invalid Packet Identifier (cannot be 0)')
        return None
    current_position+=bytes_read

    # Properties
    properties = {}
    if current_position < len(remaining_packet):
        # Properties length(variable byte integer)
        properties_length, length_bytes = decode_vbi(remaining_packet, current_position)
        if properties_length is None:
            print(f'{packet_type}: Invalid properties length encoding')
            return None

        current_position += length_bytes
        properties_end = current_position + properties_length

        if properties_end > len(remaining_packet):
            print(f'{packet_type}: Invalid properties length(extends beyond the packet end)')
            return None

        if properties_length > 0:
            properties_bytes = remaining_packet[current_position:properties_end]
            prop_current_pos = 0

            while prop_current_pos < properties_length:
                if prop_current_pos >= len(properties_bytes):
                    print(f'{packet_type}: Malformed properties section')
                    return None

                property_id, _ = parse_byte(properties_bytes, prop_current_pos)
                prop_current_pos += 1

                match property_id:
                    case 0x1F:  # Reason String(UTF-8 string)
                        value, bytes_read = parse_utf8_string(properties_bytes, prop_current_pos)
                        if value_is_None(value, property_id, packet_type):
                            return None
                        properties['Reason String'] = value
                        prop_current_pos += bytes_read

                    case 0x26:  # User Property(UTF-8 String Pair)
                        key, value, bytes_read = parse_utf8_string_pair(properties_bytes, prop_current_pos)
                        if value_is_None(key, property_id, packet_type):
                            return None
                        if 'User Property' not in properties:
                            properties['User Property'] = []
                        properties['User Property'].append((key, value))
                        prop_current_pos += bytes_read

                    case _:  # nicio proprietate a pachetelor de reply la PUBLISH in QoS>0
                        print(f'{packet_type}: Unknown property ID')
                        return None

            current_position = properties_end

    '''Payload'''
    reason_codes = []
    if current_position==len(remaining_packet):
        print(f'{packet_type}: Malformed packet - {packet_type} requires payload')
        return None

    #Parsing all reason codes from payload
    while current_position< len(remaining_packet):
        reason_code, bytes_read = parse_byte(remaining_packet,current_position)
        if reason_code is None:
            print(f'{packet_type}: Invalid reason code: {reason_code}')
            return None

        if reason_code not in select_reason_code_list(packet_type):
            print(f'{packet_type}: Invalid reason code 0x{reason_code:02X}')
            return None

        reason_codes.append(reason_code)
        current_position += bytes_read

    result = {
        'packet_id': packet_id,
        'properties': properties if properties else None,
        'reason_codes': reason_codes,
        'client_id': client_id
    }

    print(f"{packet_type} PACKET SUMMARY")
    print(f"Packet ID: {packet_id}")
    print(f"Number of reason codes: {len(reason_codes)}")
    for code in reason_codes:
        reason_message = reason_code_messages.get(code,"Unknown reason code")
        if packet_type=='SUBACK' and code==0x00:
            print(f'Code {code}: {reason_message[2]}')
        elif packet_type=='UNSUBACK' and code==0x00:
            print(f'Code {code}: {reason_message[0]}')
        else:
            print(f'Code {code}: {reason_message}')

    if properties:
        print('Properties')
        for key,value in properties.items():
            if key=='User Property':
                print(f"    {key}:")
                for k,v in value:
                    print(f"        {k} = {v}")
            else:
                print(f'    {key}: {value}')
    else:
        print('No properties')

    print('='*60)
    return result

