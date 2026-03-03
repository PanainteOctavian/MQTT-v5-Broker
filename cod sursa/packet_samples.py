'''
    Aici sunt definite variabilele ce contin pachetele de test
    Se foloseste parser-ul si handler-ul pt a identifica pachetul
'''

# SUBSCRIBER 1
CONNECT1=(# FIXED HEADER
        "00010000 "  # connect (type=1, flags=0)
        "00100101 "  # remaining length = 16 + 21 = 37
        # VARIABLE HEADER
        "00000000 00000100 "  # protocol name length (4)
        "01001101 01010001 01010100 01010100 "  # "MQTT"
        "00000101 "  # protocol version (5)
        "11000010 "  # user = 1; pass = 1; will retain = 0; will qos = 00 = 0; will flag = 0; clean start = 0; reserved = 0;
        "00000000 00000100 "  # keep alive (60) !!! 8
        "00000101 "  # properties length (5)
        "00010001 "  # Session Expiry Interval identifier (17)
        "00000000 00000000 00000000 00001010 "  # Session Expiry Interval (10)
        # pana aici 16 bytes
        # PAYLOAD
        "00000000 00000111 "  # client ID length (7)
        "01100011 01101100 01101001 01100101 01101110 01110100 00110001 "  # "client1"
        "00000000 00000100 "  # username length (4)
        "01110101 01110011 01100101 01110010 "  # "user"
        "00000000 00000100 "  # password length (4)
        "01110000 01100001 01110011 01110011 "  # "pass"
)

# SUBSCRIBER 2
CONNECT2=(# FIXED HEADER
        "00010000 "  # connect (type=1, flags=0)
        "00100101 "  # remaining length = 16 + 21 = 37
        # VARIABLE HEADER
        "00000000 00000100 "  # protocol name length (4)
        "01001101 01010001 01010100 01010100 "  # "MQTT"
        "00000101 "  # protocol version (5)
        "11000000 "  # user = 1; pass = 1; will retain = 0; will qos = 00 = 0; will flag = 0; clean start = 0; reserved = 0;
        "00000000 00111100 "  # keep alive (60)
        "00000101 "  # properties length (5)
        "00010001 "  # Session Expiry Interval identifier (17)
        "00000000 00000000 00000000 00001010 "  # Session Expiry Interval (10)
        # pana aici 16 bytes
        # PAYLOAD
        "00000000 00000111 "  # client ID length (7)
        "01100011 01101100 01101001 01100101 01101110 01110100 00110010 "  # "client2"
        "00000000 00000100 "  # username length (4)
        "01110011 01110011 01110011 01110011 "  # "ssss"
        "00000000 00000100 "  # password length (4)
        "01110000 01110000 01110000 01110000 "  # "pppp"
)

# PUBLISHER
CONNECT3=(
    # FIXED HEADER
    "00010000 "  # Type: CONNECT (1)
    "00111100 "  # Remaining Length: 60 (zecimal)
    # VARIABLE HEADER
    "00000000 00000100 "  # Protocol Name Length (4)
    "01001101 01010001 01010100 01010100 "  # "MQTT"
    "00000101 "  # Version 5
    "11110110 "  # Flags: User=1, Pass=1, Retain=1, QoS=2, Will=1, Clean=1
    "00000000 01111000 "  # Keep Alive (120) !!! 01111000
    "00000101 "  # Prop Length (5)
    "00010001 00000000 00000000 00000000 00001010 " # Session Expiry (ID 17, Value 10)
    # PAYLOAD
    "00000000 00000111 " # Client ID Len (7)
    "01100011 01101100 01101001 01100101 01101110 01110100 00110011 " # "client3"
    "00000101 " # Will Properties Length (5)
    "00011000 00000000 00000000 00000000 00001010 " # Will Delay (ID 24, Value 10)
    "00000000 00000110 " # Will Topic Len (6)
    "01110111 01101001 01101100 01101100 00101111 01110100 " # "will/t"
    "00000000 00000111 " # Will Message Len (7)
    "01110111 01101001 01101100 01101100 01001101 01110011 01100111 " # "willMsg"
    "00000000 00000100 " # User Len (4)
    "01110010 01100101 01110011 01110101 " # "resu"
    "00000000 00000100 " # Pass Len (4)
    "01110011 01110011 01100001 01110000 " # "ssap"
)

DISCONNECT=(
    # FIXED HEADER
    "11100000 "  # DISCONNECT (type=14, flags=0)
    "00011001 "  # remaining length = 25 !!!
    # VARIABLE HEADER
    "10000000 "  # disconnect reason code = 128
    "00010111 "  # properties length = 23 !!!
    "00011111 "  # reason string id (31) utf string
    "00000000 00000010 " # reason msb si lsb
    "01100100 01100100 "  # reason string propiu zis: "dd"
    "00100110 "  # user property id (38) utf pair
    "00000000 00000010 "  # user property key len (2 bytes)
    "01100001 01100001 "  # user property key: "aa" (2 bytes)
    "00000000 00000010 "  # user property value len (2 bytes)
    "01100010 01100010 "  # user property value: "bb" (2 bytes)
    "00011100 "  # server reference id (28) utf string
    "00000000 00000110 "  # server reference msb si lsb
    "01110011 01100101 01110010 01110110 01100101 01110010 "  # server reference propriu zis: "server"
)

# SUBSCRIBER 1
SUBSCRIBE1=(
    # FIXED HEADER
    "10000000 "  # SUBSCRIBE (type = 8)
    "00011110 "  # rem length = 15(var header) + 15(payload) = 30
    # VARIABLE HEADER
    "00000000 00000010 "  # packet_id = 2
    "00001100 "  # properties length = 12
    "00001011 "  # Subscription id (11)
    "10000011 00000001 "  # subscription_id value = 3*128^0 + 1*128^1 = 131
    "00100110 "  # User Property (38)
    "00000000 00000010 "  # user property key len (2 bytes)
    "01100001 01100001 "  # user property key: "aa" (2 bytes)
    "00000000 00000010 "  # user property value len (2 bytes)
    "01100010 01100010 "  # user property value: "bb" (2 bytes)
    # PAYLOAD
    "00000000 00000011 "  # topic 1 de lg 3
    "01100001 00101111 01100010 "  # topic 1 = "a/b"
    "00000001 "  # optiuni topic 1 -> qos = 1
    "00000000 00000110 "  # topic 2 de lg 6
    "01110111 01101001 01101100 01101100 00101111 01110100 "  # topic 2 = "will/t"
    "00000010 "  # optiuni topic 2 -> qos = 2
)

# SUBSCRIBER 2
SUBSCRIBE2=(
    # FIXED HEADER
    "10000000 "  # SUBSCRIBE (type = 8)
    "00010110 "  # rem length = 15(var header) + 7(payload) = 30
    # VARIABLE HEADER
    "00000000 00000010 "  # packet_id = 2
    "00001100 "  # properties length = 12
    "00001011 "  # Subscription id (11)
    "10000100 00000001 "  # subscription_id value = 4*128^0 + 1*128^1 = 132
    "00100110 "  # User Property (38)
    "00000000 00000010 "  # user property key len (2 bytes)
    "01100001 01100001 "  # user property key: "aa" (2 bytes)
    "00000000 00000010 "  # user property value len (2 bytes)
    "01100010 01100010 "  # user property value: "bb" (2 bytes)
    # PAYLOAD
    "00000000 00000100 "  # topic 1 de lg 4
    "01100001 00101111 01100010 01100010 "  # topic 1 = "a/bb"
    "00000000 "  # optiuni topic 1 -> qos = 0
)

PUBLISH1=(
    # FIXED HEADER
    "00111101 " # PUBLISH (type = 3), flags = 1 10 1
    "00001110 " # remaining length = var header + payload = 12 + 2 = 14
    # VARIABLE HEADER
    "00000000 00000011 " # topic name msb si lsb = 3
    "01100001 00101111 01100010 " # topic name = "a/b"
    "00000000 00001010 " # packet_id = 10
    "00000100 " # properties length = 4
    "00000011 "  # Content Type (3) (utf string)
    "00000000 00000001 "  # Content Type msb si lsb = 1
    "01110011 "  # Content Type = "s"
    # PAYLOAD
    "01110010 01100011" #"rc"
)

PUBLISH2=(
    # FIXED HEADER
    "00111101 " # PUBLISH (type = 3), flags = 1 10 1
    "00001111 " # remaining length = var header + payload = 13 + 2 = 15
    # VARIABLE HEADER
    "00000000 00000100 " # topic name msb si lsb = 4
    "01100001 00101111 01100010 01100010 " # topic name = "a/bb"
    "00000000 00001011 " # packet_id = 11
    "00000100 " # properties length = 4
    "00000011 "  # Content Type (3) (utf string)
    "00000000 00000001 "  # Content Type msb si lsb = 1
    "01110011 "  # Content Type = "s" de la string
    # PAYLOAD
    "01100011 01110010 " #"cr"
)

PINGREQ=(
    # FIXED HEADER
    "11000000 " # PINGREQ (type = 12)
    "00000000 " # remaining length = 0
)