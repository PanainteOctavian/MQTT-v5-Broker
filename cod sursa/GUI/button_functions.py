from tkinter import *
import json
import os
from datetime import datetime

def load_data(filename):
    if not os.path.exists(filename):
        return {}
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except Exception as e:
        return {}

def format_timestamp(timestamp):
    """Convertește timestamp UNIX în format lizibil String."""
    try:
        return datetime.fromtimestamp(float(timestamp)).strftime('%d-%m-%Y %H:%M:%S')
    except:
        return "N/A"

def clear_text(text_widget:Text):
    old_text = text_widget.get("1.0","end-1c")
    if old_text.strip(): #daca textul e gol sau doar cu spatii
        text_widget.delete(1.0,END)

'''Functii de vizualizare a datelor'''

#Vizualizare istoric topic-uri
def vis_topic_history(text_widget:Text):
    clear_text(text_widget) #verificarile se fac in functie
    text_widget.insert(END, '=== Istoric Topic-uri Utilizate ===\n\n')
    topics = set() #datele se iau numai o singura data cu ajutorul set-ului

    msgs_data = load_data('Message_routing/messagesDB.json')
    for client_msgs in msgs_data.values():
        for msg in client_msgs:
            if 'topic' in msg:
                topics.add(msg['topic'])

    retain_data = load_data('Message_routing/retainDB.json')
    for topic in retain_data.keys():
        topics.add(topic)

    #sunt luate in considerare si topic-urile fara niciun mesaj
    subs_data = load_data('Subscriptions/subscriptionsDB.json')
    for client_data in subs_data.values():
        for sub in client_data.get("subscriptions", []):
            topics.add(sub["topic"])

    if not topics:
        text_widget.insert(END, "Nu au fost gasite topic-uri.")
    else:
        for t in sorted(list(topics)):
            text_widget.insert(END,f" -> {t}\n")


#Vizualizare istoric pentru ultimele 10 mesaje publicate/topic
def vis_last_messages(text_widget:Text):
    clear_text(text_widget)
    text_widget.insert(END, '=== Ultimele 10 mesaje (per Topic) ===\n')

    msgs_data = load_data('Message_routing/messagesDB.json')

    topic_map = {}

    # Colectăm toate mesajele din cozile tuturor clienților
    for client_id, msgs_list in msgs_data.items():
        for msg in msgs_list:
            t = msg.get('topic')
            if t:
                if t not in topic_map:
                    topic_map[t] = []
                # Adăugăm mesajul în listă
                topic_map[t].append(msg)

    if not topic_map:
        text_widget.insert(END, "\nNu există istoric de mesaje.\n")
    else:
        #procesam fiecare topic
        for topic, msgs in topic_map.items():
            text_widget.insert(END, f"\nTopic: {topic}\n" + "-" * 40 + "\n")

            #sortam descrescator dupa timestamp
            msgs.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

            #fiind sortate descrescator, se iau doar ultimele 10 mesaje
            last_10 = msgs[:10]

            for m in last_10:
                ts = format_timestamp(m.get('timestamp', 0))
                payload = m.get('payload', '')
                pub = m.get('publisher', 'Unknown')
                qos = m.get('qos', 0)
                text_widget.insert(END, f"[{ts}] Pub: {pub} | QoS: {qos} | Msg: {payload}\n")

'''Vizualizare topicuri cu clienți abonați'''
def vis_topics(text_widget:Text):
    clear_text(text_widget)

    text_widget.insert(END, '=== Topic-uri și Clienți Abonați ===\n\n')

    subscription_data = load_data('Subscriptions/subscriptionsDB.json')

    topic_subscribers = {}

    for client_id, data in subscription_data.items():
        subscriptions = data.get("subscriptions", [])
        for sub in subscriptions:
            t = sub["topic"]
            q = sub["qos"]
            if t not in topic_subscribers:
                topic_subscribers[t] = []
            topic_subscribers[t].append(f"{client_id} (QoS = {q})")

    if not topic_subscribers:
        text_widget.insert(END, "Nu există abonamente active.")
    else:
        for topic, clients in topic_subscribers.items():
            text_widget.insert(END, f"Topic: {topic}\n")
            for c in clients:
                text_widget.insert(END, f"  -> {c}\n")
            text_widget.insert(END, "\n")

'''Vizualizare mesaje stocate cu QoS1 sau QoS2'''
'''Se pot vizualiza atat mesajele retained(retinute de server) si cele in asteptare(pending)'''
def vis_messages_stored(text_widget:Text):
    clear_text(text_widget)

    text_widget.insert(END, '=== Mesaje Stocate (QoS 1 sau 2) ===\n\n')

    found_any = False #Flag cu care se verifica daca avem orice tip de mesaj

    #mesaje retained
    retain_data = load_data('Message_routing/retainDB.json')
    text_widget.insert(END, "[ RETAINED MESSAGES ]\n")

    has_retained = False # Flag cu care se verifica daca avem mesaje retinute
    for topic, info in retain_data.items():
        if info.get('qos', 0) >= 1:
            has_retained = True
            found_any = True
            ts = format_timestamp(info.get('timestamp', 0))
            text_widget.insert(END, f"Topic: {topic}\n")
            text_widget.insert(END, f"  Mesaj: {info.get('payload')}\n")
            text_widget.insert(END, f"  QoS: {info.get('qos')} | Time: {ts}\n")
            text_widget.insert(END, "-" * 20 + "\n")

    if not has_retained:
        text_widget.insert(END, "  (Nu există mesaje retained cu QoS >= 1)\n")
    text_widget.insert(END, "\n")

    #mesaje pending
    msgs_data = load_data('Message_routing/messagesDB.json')
    text_widget.insert(END, "[ PENDING MESSAGES ]\n")

    has_pending = False
    for client_id, msgs_list in msgs_data.items():
        for msg in msgs_list:
            if msg.get('qos',0) >=1 and msg.get('status') == 'pending':
                has_pending = True
                found_any = True
                ts = format_timestamp(msg.get('timestamp', 0))
                text_widget.insert(END, f"Destinatar: {client_id}\n")
                text_widget.insert(END, f"  Topic: {msg.get('topic')}\n")
                text_widget.insert(END, f"  Mesaj: {msg.get('payload')}\n")
                text_widget.insert(END, f"  QoS: {msg.get('qos')} | Publisher: {msg.get('publisher')}\n")
                text_widget.insert(END, "-" * 20 + "\n")

    if not has_pending:
        text_widget.insert(END, "  (Nu există mesaje pending cu QoS >= 1)\n")

    if not found_any:
        text_widget.insert(END, "\nNu au fost găsite mesaje stocate critice (QoS 1/2).")
