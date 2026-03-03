import socket
import Parser_and_handlers.handlers as handlers
import Parser_and_handlers.parser as parser
from Parser_and_handlers.parser import packet_parser
from Parser_and_handlers.reply_handlers import pub_reply_qos_handler
import packet_samples
import re

from Response_packet_build.CONNACK_packet_build import build_connack_packet
from Response_packet_build.common_use import server_properties
from Response_packet_build.SUBACK_packet_build import build_suback_packet
from Response_packet_build.PUBX_packet_build import *

import KA_and_LWT.keep_alive as keep_alive_manager

'''
    In aceasta functie se va face parsarea pacheteleor deja aflate in packet_samples
    Se va alege input-ul care corespunde cu pachetul
    In caz de nepotrivire, programul arunca o esceptie
'''


def parse_packet_type(input):
    match input:
        case 'CONNECT1':
            return packet_parser(packet_samples.CONNECT1)
        case 'CONNECT2':
            return packet_parser(packet_samples.CONNECT2)
        case 'CONNECT3':
            return packet_parser(packet_samples.CONNECT3)
        case 'SUBSCRIBE1':
            return packet_parser(packet_samples.SUBSCRIBE1)
        case 'SUBSCRIBE2':
            return packet_parser(packet_samples.SUBSCRIBE2)
        case 'DISCONNECT':
            return packet_parser(packet_samples.DISCONNECT)
        case 'PUBLISH1':
            return packet_parser(packet_samples.PUBLISH1)
        case 'PUBLISH2':
            return packet_parser(packet_samples.PUBLISH2)
        case 'PINGREQ':
            return packet_parser(packet_samples.PINGREQ)
        case None:
            print('[Server] Non-existent packet. Please verify the input or use the packets already created in binary')
            return -1


def bytes_to_bin(data):
    """
    Converteste bytes primiti in format string binar pentru parser.
    Exemplu: b'\x10\x06' -> "00010000 00000110"
    """
    return ' '.join(format(byte, '08b') for byte in data)


def handle_client(connection: socket.socket, address):
    """
    Gestioneaza comunicatia cu un client MQTT conectat.
    """
    client_id = None

    try:
        while True:
            # Primeste date de la client
            data = connection.recv(4096)

            if not data:
                print(f'[Server] Disconnected client: {address}')
                if client_id:
                    # Dezregistrează clientul dacă socket-ul este închis
                    keep_alive_manager.unregister_client(client_id, graceful=True, reason="Socket closed")
                break

            '''Daca textul decodat este o comanda de pachet, atunci se executa pachetul corespunzator
                    Daca e format raw sau manual, se va merge pe else'''
            if re.match('[A-Z]+', data.decode().strip()):
                parsed_packet = parse_packet_type(data.decode().strip())
            else:
                # Incearca sa decodeze ca text (pentru teste manuale)
                try:
                    packet_string = data.decode('utf-8').strip()
                    print(f'[Server] Text packet received from {address}')
                    parsed_packet = parser.packet_parser(packet_string)

                except UnicodeDecodeError:
                    # Daca decodarea esueaza, trateaza ca bytes raw (client MQTT real)
                    print(f'[Server] Raw packet received from {address}: {len(data)} bytes')
                    packet_string = bytes_to_bin(data)
                    print(f'[Server] Converted in: {packet_string[:50]}...')
                    parsed_packet = parser.packet_parser(packet_string)

                except ValueError:
                    packet_string = bytes_to_bin(data)
                    print(f'[Server] Converted in: {packet_string[:50]}...')
                    parsed_packet = parser.packet_parser(packet_string)

                if parsed_packet is None:
                    print(f'[Server] Invalid packet from: {address}')
                    continue

            # Proceseaza pachetul
            packet_type = parsed_packet[0]

            # Actualizează activitatea pentru Keep Alive pentru majoritatea pachetelor
            if client_id and packet_type in [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]:
                # Actualizează activitatea pentru toate pachetele MQTT (exceptând CONNECT și DISCONNECT)
                packet_type_name = {
                    3: "PUBLISH", 4: "PUBACK", 5: "PUBREC", 6: "PUBREL",
                    7: "PUBCOMP", 8: "SUBSCRIBE", 9: "SUBACK", 10: "UNSUBSCRIBE",
                    11: "UNSUBACK", 12: "PINGREQ", 13: "PINGRESP"
                }.get(packet_type, "UNKNOWN")
                keep_alive_manager.update_client_activity(client_id, packet_type_name)

            if packet_type == 6:
                _, _, _, remaining_packet = parsed_packet
                client_id = handlers.connected_clients.get(connection) if connection else None
                result = pub_reply_qos_handler(remaining_packet, client_id, 'PUBREL')
            else:
                result = handlers.handler(parsed_packet, connection)

            # Extrage client_id din pachetul CONNECT pentru tracking
            if packet_type == 1 and result:
                client_id = result.get('client_id')
                print(f'[Server] Client connected succcessfully: {address}, ID: {client_id}')

                # Înregistrează clientul în dicționarul handlers.py
                if connection and client_id:
                    handlers.connected_clients[connection] = client_id

                # Înregistrează clientul pentru Keep Alive
                connect_data = result.get('connect_data', {})
                keep_alive = connect_data.get('keep_alive', 0)
                will_message = connect_data.get('will', None)

                # Înregistrează clientul în sistemul de Keep Alive
                success = keep_alive_manager.register_client(
                    client_id=client_id,
                    client_socket=connection,
                    keep_alive=keep_alive,
                    will_message=will_message
                )

                if success:
                    # Actualizează activitatea pentru CONNECT
                    keep_alive_manager.update_client_activity(client_id, "CONNECT")
                else:
                    print(f'[Server] Warning: Failed to register client {client_id} in Keep Alive system')

            # Trimitere raspuns corespunzator
            match packet_type:
                case 1:  # CONNECT -> CONNACK
                    """Se preia din result[session_result] reason_code si session_present"""
                    session_result = result['session_result']
                    connack_packet = build_connack_packet(
                        session_present=session_result['session_present'],
                        reason_code=session_result['reason_code'],
                        properties=server_properties
                    )
                    connection.send(connack_packet)

                case 3:  # PUBLISH -> PUBACK/PUBREC/PUBREL/PUBCOMP
                    qos = result['qos']
                    packet_id = result.get('packet_id')

                    # Determinare pachet de raspuns
                    response_packet = None

                    if qos == 1:
                        response_packet = build_puback_packet(
                            packet_id=packet_id,
                            reason_code=0x00,
                            properties=None
                        )
                    elif qos == 2:
                        response_packet = build_pubrec_packet(
                            packet_id=packet_id,
                            reason_code=0x00,
                            properties=None
                        )

                    if response_packet:
                        connection.send(response_packet)
                        print(f'[PUBLISH] Reply sent for packet_id={packet_id}, QoS={qos}')

                case 6:  # vezi legenda de mai sus la PUBLISH. Este PUBREL->PUBCOMP
                    packet_id = result['packet_id']

                    pubcomp_packet = build_pubcomp_packet(
                        packet_id=packet_id,
                        reason_code=0x00
                    )

                    connection.send(pubcomp_packet)

                case 8:  # SUBSCRIBE -> SUBACK
                    packet_id = result['packet_id']
                    subscription_results = result['subscription_results']

                    reason_codes = []

                    for results in subscription_results:
                        if results['success']:
                            reason_codes.append(results['qos'])
                        else:
                            reason_codes.append(0x80)

                    suback_packet = build_suback_packet(packet_id=packet_id, reason_codes=reason_codes)
                    connection.send(suback_packet)

                #case 10:  # UNSUBSCRIBE -> UNSUBACK
                    #connection.send(b'ACK')

                case 12:  # PINGREQ -> PINGRESP
                    if client_id:
                        keep_alive_manager.update_client_activity(client_id, "PINGREQ")
                    connection.send(b'\xD0\x00')  # PINGRESP packet

                case 14:  # DISCONNECT -> mesaj OK
                    if client_id:
                        # Dezregistrează clientul din sistemul Keep Alive
                        keep_alive_manager.unregister_client(client_id, graceful=True, reason="DISCONNECT packet")
                    connection.send(b'DISCONNECT')
                    # Ieșire din bucla pentru acest client
                    break

                case 13:  # PINGRESP
                    if client_id:
                        keep_alive_manager.update_client_activity(client_id, "PINGRESP")

    except socket.error as e:
        print(f'[Server] Socket errot from client {address}: {e}')
        if client_id:
            keep_alive_manager.unregister_client(client_id, graceful=False, reason=f"Socket error: {e}")

    except ConnectionResetError:
        print(f'[Server] Connection reset by client: {address}')
        if client_id:
            keep_alive_manager.unregister_client(client_id, graceful=False, reason="Connection reset")

    except Exception as e:
        print(f'[Server] Error in processing client {address}: {e}')
        import traceback
        traceback.print_exc()
        if client_id:
            keep_alive_manager.unregister_client(client_id, graceful=False, reason=f"Exception: {e}")

    finally:
        print(f'[Server] Connection closed: {address}')

        # Curăță toate resursele
        if client_id:
            # Verifică dacă clientul mai există în Keep Alive (nu a fost deja șters)
            client_info = keep_alive_manager.get_client_info(client_id)
            if client_info:
                keep_alive_manager.unregister_client(client_id, graceful=True, reason="Connection closed finally")

            # Șterge din dicționarul de clienți conectați
            if connection in handlers.connected_clients:
                del handlers.connected_clients[connection]

        try:
            connection.close()
        except:
            pass

