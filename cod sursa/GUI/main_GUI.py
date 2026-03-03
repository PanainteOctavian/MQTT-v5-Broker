import tkinter
from tkinter import *

from GUI.button_functions import vis_topic_history, vis_last_messages, vis_topics, vis_messages_stored


def launch_gui():
    #setari initiale GUI
    gui = Tk()
    gui.title('Broker MQTT')
    gui.geometry("710x370+100+100")  #panel cu dimensiune 700x700 cu coltul din stanga-sus la (100,100)
    gui.resizable(False,False) #nu se permite reajustarea dimensiunii pe nicio axa

    #widget-ul de vizualizare al textului
    text_widget = Text(gui,height=200,width=100)
    text_widget.place(x=10,y=50,width=500,height=300)
    #text_widget.insert(tkinter.END,'Text')

    #textul intuitiv deasupra widget-ului
    text_label = Label(gui,fg='blue',font=('Arial',14,'bold'),height=3,width=20,
                       text='Ecran de vizualizare operatii')
    text_label.place(x=125,y=10,width=270,height=20)

    #buton de vizualizare a istoricului topic-urilor
    vis_topic_history_btn = Button(gui,fg='green',height=3,width=20,font=('Arial',10,'bold'),
                                   text='Istoric topic-uri',
                                   command=lambda : vis_topic_history(text_widget))
    vis_topic_history_btn.place(x=550,y=50,width=100,height=20)

    #buton pt ultimele 10 mesaje publicate/topic
    vis_last_messages_btn = Button(gui,fg='green',height=3,width=20,font=('Arial',10,'bold'),
                                   text='Ultimele 10 mesaje publicate',
                                   command=lambda : vis_last_messages(text_widget))
    vis_last_messages_btn.place(x=510,y=100,width=200,height=20)

    #buton de vizualizare a topic-urilor cu clientii abonati
    vis_topics_btn = Button(gui,fg='green',height=3,width=20,font=('Arial',10,'bold'),
                                   text='Vizualizare topic-uri',
                            command=lambda : vis_topics(text_widget))
    vis_topics_btn.place(x=530,y=150,width=140,height=20)

    #buton de vizualizare a mesajelor stocate cu QoS 1 sau 2
    vis_messages_btn = Button(gui,fg='green',height=3,width=20,font=('Arial',10,'bold'),
                                   text='Vizualizare mesaje',
                              command=lambda : vis_messages_stored(text_widget))
    vis_messages_btn.place(x=535,y=200,width=130,height=20)

    gui.mainloop()

'''Se decomenteaza pt a testa separat GUI-ul'''
if __name__=='__main__':
    launch_gui()
