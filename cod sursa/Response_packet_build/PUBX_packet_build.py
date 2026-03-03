from Parser_and_handlers.parser import encode_vbi
from Response_packet_build.common_use import build_packet_properties


def build_pubx_packet(packet_type, packet_id, reason_code=None, properties=None, flags=0):
    '''packet_type: 0x40 (PUBACK), 0x50 (PUBREC), 0x60 (PUBREL), 0x70 (PUBCOMP)'''

    # Fixed header
    fixed_header = packet_type | flags  # Pentru PUBREL, flags=0x02

    # Variable Header
    variable_header = packet_id.to_bytes(2, 'big')

    # Properties
    if properties is None:
        properties = {}

    properties_bytes = build_packet_properties(properties)
    prop_length = len(properties_bytes)
    prop_length_vbi = encode_vbi(prop_length)

    variable_header += prop_length_vbi + properties_bytes

    #Payload: Reason Code
    payload = b''
    if reason_code is not None:
        payload = bytes([reason_code])

    #Remaining length
    remaining_length = len(variable_header) + len(payload)
    remaining_length_vbi = encode_vbi(remaining_length)

    #Asamblare pachet
    packet = bytearray()
    packet.append(fixed_header)
    packet.extend(remaining_length_vbi)
    packet.extend(variable_header)
    packet.extend(payload)

    return bytes(packet)

def build_puback_packet(packet_id, reason_code=None, properties=None):
    return build_pubx_packet(0x40, packet_id, reason_code, properties)

def build_pubrec_packet(packet_id, reason_code=None, properties=None):
    return build_pubx_packet(0x50, packet_id, reason_code, properties)

def build_pubrel_packet(packet_id, reason_code=None, properties=None):
    return build_pubx_packet(0x60, packet_id, reason_code, properties, flags=0x02)

def build_pubcomp_packet(packet_id, reason_code=None, properties=None):
    return build_pubx_packet(0x70, packet_id, reason_code, properties)