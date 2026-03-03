import os
import atexit
import glob
from GUI.main_GUI import launch_gui
import Parser_and_handlers.parser
import Parser_and_handlers.handlers
from TCP_Listener.socket_TCP_listener import socket_tcp_listener
from concurrent.futures import ThreadPoolExecutor
from Exceptions.program_related_except import *
import KA_and_LWT.keep_alive as keep_alive_manager

'''
    Dev note: Toate pachetele au fost bagate ca variabile in packet_samples.py
    In connection_manager.py, serverul preia de la client inputul cu tipul de pachet(ex. CONNECT)
    Si parseaza corespunzator in functie de ce s-a primit la input
    Alte detalii in connection_manager.py
'''

def cleanup_json_files():
    # sterge bazele de date JSON
    print("[Cleanup] Delete JSON files")

    json_paths = [
        'Auth_and_sessions/userDB.json',
        'Auth_and_sessions/sessionsDB.json',
        'Subscriptions/subscriptionsDB.json',
        'Message_routing/messagesDB.json',
        'Message_routing/retainDB.json',
        'KA_and_LWT/keep_alive_db.json'
    ]

    deleted_count = 0
    for json_path in json_paths:
        try:
            if os.path.exists(json_path):
                os.remove(json_path)
                deleted_count += 1
                print(f"[Cleanup] Deleted: {json_path}")
        except Exception as e:
            print(f"[Cleanup] Error while deleting {json_path}: {e}")

    try:
        tmp_files = glob.glob('**/*.tmp', recursive=True)
        for tmp_file in tmp_files:
            os.remove(tmp_file)
            deleted_count += 1
    except Exception as e:
        print(f"[Cleanup] Error while deleting .tmp files: {e}")

    print(f"[Cleanup] Total {deleted_count} deleted files")

def startup():
    print("[Startup] Initializing MQTT broker...")

    # porneste monitorizarea Keep Alive
    keep_alive_manager.start_monitor()

    # incarca ultima stare a bazei de date
    keep_alive_manager.load_database()

    print("[Startup] MQTT Broker started")


def shutdown():
    print("[Shutdown] Starting broker shutdown...")

    # cleanup
    keep_alive_manager.cleanup_all_connections()

    cleanup_json_files()

    print("[Shutdown] MQTT Broker turned off")


if __name__ == '__main__':
    # functie de shutdown care se exec la terminare
    atexit.register(shutdown)

    startup()

    with ThreadPoolExecutor(max_workers=2) as executor:
        worker1 = executor.submit(socket_tcp_listener)
        worker2 = executor.submit(launch_gui)
        try:
            while True:
                if not worker1.running() or not worker2.running():
                    raise WorkerClosedWhileRunningError
        except WorkerClosedWhileRunningError as e:
            '''In caz de exceptie se inchide programul'''
            print(f'{e}')

            shutdown()

            executor.shutdown(wait=False, cancel_futures=True)  # oprim workerii activi
            os._exit(1)  # inchidem fortat programul