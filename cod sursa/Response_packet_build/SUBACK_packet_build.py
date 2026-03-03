import random

from Parser_and_handlers.parser import encode_vbi
from Response_packet_build.common_use import build_packet_properties

def build_suback_packet(packet_id, reason_codes, properties=None):
    # Fixed header(tip pachet=9, flag-uri=0)
    fixed_header = 0x90

    #Variable header
    variable_header = packet_id.to_bytes(2, 'big') #PACKET_ID

    #Properties
    if properties is None:
        #definim un properties by default
        properties = {
            "User Property": [('subscription_id',int(random.random()*100))]
            #se adauga un subscription_id aleator
        }

    properties_bytes = build_packet_properties(properties)
    prop_length = len(properties_bytes)
    prop_length_vbi = encode_vbi(prop_length)

    variable_header += prop_length_vbi + properties_bytes

    #Payload
    payload=b''
    for code in reason_codes:
        payload+= bytes([code])

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