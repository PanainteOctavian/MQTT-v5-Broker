'''
    Daca socket-ul TCP sau GUI-ul este inchis, nu mai poate functia programul cum s-a propus
    Cele 2 functioneaza concurent intr-un ThreadPoolExecutor
    Exceptia e necesara pt a inchide celalalt worker din program
'''
class WorkerClosedWhileRunningError(Exception):
    def __init__(self):
        print("[! Exception] TCP or GUI closed. Program is closing...")

'''
    Pt a evita repetitia secventei de program de mai sus, se poate folosi aceasta functie
    Se foloseste in cazul detectarii proprietatilor
    Are o formula generica ce merge pt orice pachet
'''
def value_is_None(value,property_id,packet_type):
    if value is None:
        print(f"{packet_type}: Property {hex(property_id)} too short")
        return True
    return False

'''
    Se va face verificarea pachetului in pub_reply_qos_handler,
    pt a evita gestionarea unui pachet ce nu are legatura cu
    raspunsul la publish in cazul QoS>0
'''
def packet_is_not_qos_related(packet_type):
    if packet_type not in ['PUBACK','PUBREC','PUBREL','PUBCOMP']:
        print('Packet unrecognized or cannot be used in pub_reply_qos_handler')
        return True
    return False

def packet_is_not_subscribe_related(packet_type):
    if packet_type not in ['SUBACK','UNSUBACK']:
        print('Packet cannot be used in suback_unsuback_handler')
        return True
    return False


'''In cazul in care o valoare nu este in range, '''
class ValueErr(Exception):
    def __init__(self,text):
        print(f'[! Exception] {text}')