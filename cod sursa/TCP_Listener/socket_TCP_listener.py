import socket
import threading

#from pydispatch import dispatcher
from threading import Thread

from TCP_Listener.connection_manager import handle_client

'''
    Port = 1883 => conexiune necriptata
    Port = 8883 => conexiune securizata(cu SSL/TLS, etc.)
    localhost <=> 127.0.0.1 (adresa de loopback)
'''
PORT = 1883
HOST = '127.0.0.1'

def socket_tcp_listener(host=HOST,port=PORT):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
    '''Aceasta setare permite refolosirea adresei serverului'''

    server.bind((host,port))
    server.listen(5)
    print(f'[Server] Broker MQTT started with address {host} and port {port}')

    try:
        while True:
            connection, address = server.accept()
            #client.setblocking(False)
            print(f'[Server] Client conected with address: {address}')
            try:
                threading.Thread(target=handle_client,args = (connection,address)).start()
            except:
                print('[Server] !  Error while starting the thread')
    except KeyboardInterrupt:
        print('[Server] Broker manually powered off')
        server.close()
