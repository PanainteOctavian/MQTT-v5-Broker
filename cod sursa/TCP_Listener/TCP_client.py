import os
import re
import sys
import socket
import time
import threading

# Add parent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from Response_packet_build.PUBX_packet_build import build_pubrel_packet
from Parser_and_handlers.parser import packet_parser
from Parser_and_handlers.reply_handlers import reply_handler
from TCP_Listener.connection_manager import bytes_to_bin

SERVER_ADDR = '127.0.0.1'
SERVER_PORT = 1883
KEEP_ALIVE_INTERVAL = 10  # Trebuie să fie același cu cel din CONNECT packet



def ping_thread(client_socket, keep_alive, stop_event):
    """Thread separat pentru trimiterea automată a PINGREQ"""
    # Trimite PING la fiecare keep_alive/2 secunde pentru siguranță
    ping_interval = keep_alive / 2

    while not stop_event.is_set():
        time.sleep(ping_interval)
        if stop_event.is_set():
            break

        try:
            # PINGREQ packet: 0xC0 0x00
            client_socket.send(b'\xC0\x00')
            print('[Client] PINGREQ sent automatically')
        except Exception as e:
            print(f'[Client] Error while sending PINGREQ: {e}')
            break


def generate_client():
    waiting_for_response = False
    ping_stop_event = threading.Event()
    ping_thread_obj = None

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        try:
            client.connect((SERVER_ADDR, SERVER_PORT))
            while True:
                if not waiting_for_response:
                    packet = input('Packet: ')
                    try:
                        client.send(packet.encode())
                        waiting_for_response = True
                    except Exception:
                        print('[! Error] Broker closed. Client will get closed...')
                        ping_stop_event.set()
                        os._exit(1)

                data = client.recv(512)
                if not data:
                    break

                # Handle text-based DISCONNECT acknowledgment
                try:
                    decoded = data.decode().strip()
                    if re.match(r'^[A-Z]+$', decoded):
                        print('DISCONNECT: Acknowledged')
                        if decoded == 'DISCONNECT':
                            break
                        # Reset waiting flag and continue to next input
                        waiting_for_response = False
                        continue
                except UnicodeDecodeError:  # facem bypass la eroare pt ca nu produce probleme mai departe
                    pass

                # Parse binary packet
                try:
                    # print(f'[Client] S-a receptionat de la server: {data.decode()}')
                    parsed_packet = packet_parser(data.decode().strip())
                except UnicodeDecodeError:
                    packet_string = bytes_to_bin(data)
                    parsed_packet = packet_parser(packet_string)
                except ValueError:
                    packet_string = bytes_to_bin(data)
                    parsed_packet = packet_parser(packet_string)

                if not parsed_packet:
                    waiting_for_response = False
                    continue

                packet_type, _, _, _ = parsed_packet

                return_data = reply_handler(parsed_packet)

                # După CONNACK, pornește thread-ul de ping
                if packet_type == 2 and return_data:  # CONNACK
                    if ping_thread_obj is None:
                        ping_thread_obj = threading.Thread(
                            target=ping_thread,
                            args=(client, KEEP_ALIVE_INTERVAL, ping_stop_event),
                            daemon=True
                        )
                        ping_thread_obj.start()
                        print(f'[Client] PINGREQ thread started (interval: {KEEP_ALIVE_INTERVAL / 2}s)')

                # Special handling for QoS 2: PUBREC -> send PUBREL
                if packet_type == 5 and return_data:
                    pubrel_packet = build_pubrel_packet(
                        packet_id=return_data['packet_id'],
                        reason_code=0x00,
                        properties=None
                    )
                    client.send(pubrel_packet)
                    # Stay in waiting mode to receive PUBCOMP
                    continue

                # For QoS 2: PUBCOMP completes the flow
                if packet_type == 7:  # PUBCOMP
                    waiting_for_response = False
                    continue

                # PINGRESP - doar confirmă, nu cere input nou
                if packet_type == 13:  # PINGRESP
                    waiting_for_response = False
                    continue

                # For other packet types (CONNACK, PUBACK, SUBACK, etc.)
                waiting_for_response = False
                time.sleep(1)

            client.close()
        except KeyboardInterrupt:
            print('Client closed by CTRL+C')
            ping_stop_event.set()
            try:
                client.send('[Client]: Client disconnected by CTRL+C'.encode())
            except:
                pass
            client.close()
        except ConnectionRefusedError:
            print('[! Error]: Broken denied the connection or closed it')
        finally:
            ping_stop_event.set()


if __name__ == '__main__':
    generate_client()