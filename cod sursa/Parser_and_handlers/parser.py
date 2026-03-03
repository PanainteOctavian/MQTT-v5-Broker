def decode_vbi(bytes_list, start_index):
    # Decode Variable Byte Integer - pag 19 doc oficiala
    # primul bit e flag daca mai sunt valori, restu e val propiu zisa
    multiplier = 1
    value = 0
    num_bytes = 0
    current_index = start_index

    while True:
        if current_index >= len(bytes_list):
            return None, 0

        encoded_byte = bytes_list[current_index]
        current_index += 1
        num_bytes += 1

        value += (encoded_byte & 127) * multiplier
        multiplier *= 128

        if multiplier > 128 * 128 * 128:
            print("Malformed packet: Variable Byte Integer too long (over 4 bytes)")
            return None, 0

        if (encoded_byte & 128) == 0:
            break

    return value, num_bytes

def encode_vbi(value):
    # Codifica un intreg ca variable byte integer(MQTT format)
    encoded = bytearray()
    while value>0:
        encoded_byte = value%128 #se extrage octetul
        value = value // 128 #se trece la urmatorul
        if value>0:
            encoded_byte |= 128
        encoded.append(encoded_byte)

    if not encoded:
        encoded.append(0)
    return bytes(encoded)


def parse_byte(bytes_list, pos):
    if pos >= len(bytes_list):
        return None, 0
    return bytes_list[pos], 1


def parse_two_byte_int(bytes_list, pos):
    if pos + 1 >= len(bytes_list):
        return None, 0
    value = (bytes_list[pos] << 8) | bytes_list[pos + 1]
    return value, 2


def parse_four_byte_int(bytes_list, pos):
    if pos + 3 >= len(bytes_list):
        return None, 0
    value = (bytes_list[pos] << 24) | \
            (bytes_list[pos + 1] << 16) | \
            (bytes_list[pos + 2] << 8) | \
            bytes_list[pos + 3]
    return value, 4


def parse_utf8_string(bytes_list, pos):
    if pos + 1 >= len(bytes_list):
        return None, 0

    str_length = (bytes_list[pos] << 8) | bytes_list[pos + 1]
    start = pos + 2
    end = start + str_length

    if end > len(bytes_list):
        return None, 0

    string_bytes = bytes_list[start:end]
    string_value = ''.join([chr(byte) for byte in string_bytes])

    return string_value, 2 + str_length


def parse_binary_data(bytes_list, pos):
    if pos + 1 >= len(bytes_list):
        return None, 0

    data_length = (bytes_list[pos] << 8) | bytes_list[pos + 1]
    start = pos + 2
    end = start + data_length

    if end > len(bytes_list):
        return None, 0

    binary_data = bytes_list[start:end]

    return binary_data, 2 + data_length


def parse_utf8_string_pair(bytes_list, pos):
    # Parse key
    key, key_bytes = parse_utf8_string(bytes_list, pos)
    if key is None:
        return None, None, 0

    # Parse value
    value, value_bytes = parse_utf8_string(bytes_list, pos + key_bytes)
    if value is None:
        return None, None, 0

    return key, value, key_bytes + value_bytes


def packet_parser(packet):
    bytes_str = packet.split()
    bytes_list = [int(byte, 2) for byte in bytes_str]

    #print(f"Total bytes in packet: {len(bytes_list)}")

    fixed_header_byte = bytes_list.pop(0)
    packet_type = (fixed_header_byte >> 4) & 0x0F
    flags = fixed_header_byte & 0x0F

    remaining_length, length_bytes = decode_vbi(bytes_list, 0)

    #print(f"Remaining length from VBI: {remaining_length}")
    #print(f"VBI used {length_bytes} byte(s)")

    if remaining_length is None:
        print("Invalid Remaining Length encoding")
        return None

    # rem_packet = var header + payload
    remaining_packet = bytes_list[length_bytes:]

    #print(f"Actual remaining packet length: {len(remaining_packet)}")

    if remaining_length != len(remaining_packet):
        print("Invalid packet length")
        return None

    return packet_type, flags, remaining_length, remaining_packet
