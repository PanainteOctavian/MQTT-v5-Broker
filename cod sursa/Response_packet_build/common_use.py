server_properties={
    "Session Expiry Interval" : 3600, #3600 de secunde, adica o ora
    "Receive Maximum": 65535, #nr maxim de publicari de mesaje cu QoS>0
    "Maximum QoS": 1, #permite QoS2
    "Retain Available": 1, #suporta mesaje Retain
    #"Maximum Packet Size": 268435455, #dimensiunea maxima a unui pachet pe care Serverul o accepta
    # ^ are probleme, dar fara el conectarea merge corect
    "Topic Alias Maximum": 65535, #valoarea maxim accepta de server ca Topic Alias
    "Reason String": "Connection accepted", #mesaj al reason code(doar pt teste)
    "User Property": [("version", "1.0"), ("region", "eu"), ("country", "ro")], #proprietati de stiut pt user
    "Wildcard Subscription Available": 0,
    "Subscription Identifiers Available": 1,
    "Shared Subscription Available": 0,
    "Server Keep Alive": 60  # Valoarea default de keep alive oferită de server
    # Eliminat: "Keep Alive Supported": 1  # Această proprietate nu există în MQTT 5.0
}

'''Construim proprietatile oricarui pachet in afara de CONNACK(ce are o functie separata)'''
def build_packet_properties(properties):
    properties_bytes = bytearray()

    for prop_id,value in properties.items():
        if prop_id == "Reason String":  # 0x1F
            # UTF-8 string cu lungime pe 2 bytes
            properties_bytes.append(0x1F)
            str_bytes = value.encode('utf-8')
            properties_bytes.extend(len(str_bytes).to_bytes(2, 'big'))
            properties_bytes.extend(str_bytes)

        elif prop_id == "User Property":  #0x26
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
                        if isinstance(val,int):
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
        elif prop_id == "Server Keep Alive":  # 0x13
            # Server Keep Alive (0x13) - 2 bytes
            properties_bytes.append(0x13)
            properties_bytes.extend(value.to_bytes(2, 'big'))
        else:
            # Doar warning pentru proprietățile necunoscute, dar continuă procesarea
            print(f'[Warning] {prop_id}:{value} nu este o proprietate valabila in acest context, se va ignora')

    return bytes(properties_bytes)