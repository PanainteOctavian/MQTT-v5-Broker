## 1. Introducere

MQTT (Message Queuing Telemetry Transport) este un protocol de mesagerie lightweight bazat pe arhitectura publish/subscribe, proiectat special pentru dispozitive cu resurse limitate si retele cu latenta mare. Protocolul foloseste un format binar pentru mesaje, ceea ce minimizeaza overhead-ul si face comunicarea extrem de eficienta.

## 2. Componentele Sistemului MQTT

**2.1 MQTT Client**

* Orice dispozitiv care ruleaza o librarie MQTT si se conecteaza la un broker
* Poate fi publisher (trimite mesaje) sau subscriber (primeste mesaje) sau ambele

**2.2 MQTT Broker**

* Intermediar intre clienti
* Primeste toate mesajele de la publisheri
* Filtreaza si ruteaza mesajele catre subscriberi
* Gestioneaza autentificarea si autorizarea
* Pastreaza sesiunile clientilor

<img width="611" height="282" alt="image" src="https://github.com/user-attachments/assets/89f03194-4660-4d8e-8707-b4e86f1b3afa" />

## 3. Tipuri de pachete MQTT
MQTT defineste 15 tipuri de pachete de control:
1. CONNECT - Clientul initiaza conexiunea
2. CONNACK - Brokerul confirma conexiunea
3. PUBLISH – Clientul publica un mesaj
4. PUBACK – Confirmarea publicarii pachetului PUBLISH de catre broker (QoS 1)
5. PUBREC – Confirmarea primirii pachetului PUBLISH de catre broker (QoS 2 partea 1)
6. PUBREL – Pachet trimis de client astfel incat brokerul sa transmita mesajul mai departe la clientii abonati si sa stearga pachetul din memoria interna a brokerului (QoS 2 partea 2)
7. PUBCOMP - Pachet trimis de broker astfel incat clientul sa stie ca mesajul sau a fost livrat exact o data (QoS 2 partea 3)
8. SUBSCRIBE - Clientul se aboneaza la topicuri
9. SUBACK - Brokerul confirma abonarea
10. UNSUBSCRIBE - Clientul se dezaboneaza
11. UNSUBACK - Brokerul confirma dezabonarea
12. PINGREQ - Client verifica conexiunea
13. PINGRESP - Broker raspunde la PING
14. DISCONNECT - Client initiaza deconectarea voluntara
15. AUTH - Autentificare (doar pentru MQTT v5)

## 4. Structura Generala a Pachetelor MQTT
<img width="644" height="94" alt="image" src="https://github.com/user-attachments/assets/eeca77f5-aa4c-410d-8b49-5c506a2880ee" />

Fiecare pachet MQTT contine:

**4.1 Fixed Header (Header Fix)**
* Prezent in toate pachetele
	* Dimensiune: minim 2 bytes
	* Structura:
	  * Byte 1:
		  1. Biti 7-4: Tipul mesajului (CONNECT, PUBLISH, etc)
		  2. Bit 3: DUP flag (duplicate) pentru PUBLISH, 0 pentru restul pachetelor
		  3. Biti 2-1: QoS level pentru PUBLISH
		  4. Bit 1: Setat pe 1 pentru SUBSCRIBE si UNSUBSCRIBE
		  5. Bit 0: RETAIN flag pentru PUBLISH
	  * Byte 2: Remaining Length (lungimea restului pachetului: lungime Variable Header plus lungime Payload)

**4.2 Variable Header (Header Variabil)**
- Prezent in unele pachete
	- Contine Id-ul pachetului (folosit pentru pachetele publicate)
		* tabelul 2-3 pag. 23 mqtt-v5.0-os
	- Contine proprietati specifice tipului de pachet:
		* Lungimea pachetului de proprietati in octeti
		* Proprietatile, aflate in ordine secventiala, codate in hexazecimal 
		* tabelul 2-4 pag. 25 mqtt-v5.0-os

**4.3 Payload (mesajul propiu-zis al pachetului)**
- Prezenta in unele pachete
	- Datele utile ale mesajului (in pachetul PUBLISH este mesajul publicat)
	- Dimensiune maxima: 256MB

**4.4 Reason code (cod numeric care reprezinta rezultatul unei operatii)**
- Daca acest cod este mai mic de 0x80 = 128, operatia este reusita (operatie care poate face parte sau nu dintr-un ansamblu de operatii). Altfel, operatia a esuat.
	- Reason code poate aparea in sectiunea de Header Variabil sau in sectiunea de Payload.
	- tabelul 2-6 pag. 27 mqtt-v5.0-os


### Exemplu decodificare pachet AUTH:
<img width="644" height="59" alt="image" src="https://github.com/user-attachments/assets/088f7f5c-fb51-4c23-9292-30b5a37dbbda" />

FIXED HEADER:
* Tip pachet: 0xF0 = 15 => AUTH
* Lungimea restului pachetului: 0x10 = 16 octeti

VARIABLE HEADER: 
* Reason Code: 0x18 => Continue authentification 
* Proprietati:	
  * Lungime proprietati: 0x0F = 15 octeti
  * Proprietate 1: 
    * Id: 0x15 => Authentification Method
    * Lungime String: 0X06 => 6 octeti are authentification method
    * StringUTF-8: 4F 41 55 54 48 32 = "OAUTH2"
  * Proprietate 2:
    * Id: 0x16 => Authentification Data
    * Lungime Date Binare: 0X05=> 5 octeti are authentification data
    * Date binare: 74 6F 6B 65 6E

## 5. Detalii pachete principale

**5.1 Pachetul CONNECT**

<img width="370" height="213" alt="image" src="https://github.com/user-attachments/assets/d8b430b0-199e-4691-9f4e-f23f0a88d154" />

Clientul trimite acest pachet pentru a stabili conexiunea cu brokerul.

Variable Header contine:
- Protocol Name: "MQTT"
- Protocol Level: 5 (pentru MQTT 5)
- Connect Flags: 1 byte cu urmatoarele biti:
  - Bit 7: Username Flag
  - Bit 6: Password Flag
  - Bit 5: Will Retain
  - Bit 4-3: Will QoS
  - Bit 2: Will Flag
  - Bit 1: Clean Session (MQTT 3.1.1) sau Clean Start (MQTT 5)
  - Bit 0: Reserved
- Keep Alive: 2 bytes (interval in secunde)

Payload contine:
- Client ID (obligatoriu)
- Will Topic (optional)
- Will Message (optional)
- Username (optional)
- Password (optional)

**5.2 Pachetul CONNACK**

<img width="363" height="183" alt="image" src="https://github.com/user-attachments/assets/ab245fa4-23b4-4cb3-83a7-54d4160bc7d0" />

Brokerul raspunde cu CONNACK pentru a confirma conexiunea.

Variable Header contine:
- Session Present Flag: 1 byte
 	 - 0: Nu exista sesiune anterioara
  	 - 1: Exista sesiune anterioara
- Return Code: 1 byte

Return Codes:
- 0: Connection Accepted
- 1: Connection Refused - unacceptable protocol version
- 2: Connection Refused - identifier rejected
- 3: Connection Refused - server unavailable
- 4: Connection Refused - bad username or password
- 5: Connection Refused - not authorized

Nu are Payload.

**5.3 Pachetul PUBLISH**

<img width="359" height="165" alt="image" src="https://github.com/user-attachments/assets/093617b3-19a7-4839-a36e-562cbac1b740" />

Folosit pentru a publica mesaje pe un topic.

Variable Header contine:
- Topic Name: String UTF-8
- Packet Identifier: 2 bytes (doar pentru QoS > 0)

In MQTT 5, mai contine:
- Payload Format Indicator
- Message Expiry Interval
- Topic Alias
- Response Topic
- Correlation Data
- User Properties
- Content Type

Payload:
- Date binare (mesajul efectiv)
- Poate fi orice: text, JSON, XML, binar, etc.
- Dimensiune: 0 - 256MB

Flags in Fixed Header:
- DUP: Indica daca e mesaj duplicat
- QoS: Nivelul de calitate (0, 1, sau 2)
- RETAIN: Daca brokerul trebuie sa pastreze mesajul

**5.4 Pachetele PUBACK, PUBREC, PUBREL, PUBCOMP**
<p><img style="text-align: left" width="306" height="157" alt="image" src="https://github.com/user-attachments/assets/e159e56e-13d3-4825-8131-f6ee75f90887" />
<img style="text-align: right" width="295" height="142" alt="image" src="https://github.com/user-attachments/assets/cb25ac26-2227-42a8-84c3-7dc05ba4436e" /></p>
<p><img style="text-align: left" width="304" height="145" alt="image" src="https://github.com/user-attachments/assets/350db7d6-3d76-47f6-9760-21b5d4cb24c4" />
<img style="text-align: right" width="309" height="160" alt="image" src="https://github.com/user-attachments/assets/cddfb82d-010f-4432-be52-249a3dc515f4" /></p>

Aceste pachete sunt folosite in fluxulurile QoS 1 si 2 pentru confirmarea trasmiterii pachetului PUBLISH.

Variable Header contine:
- Packet Identifier: 2 bytes

PUBACK:
- Confirmare pentru QoS 1
- Nu are payload

PUBREC:
- Prima confirmare pentru QoS 2
- Nu are payload

PUBREL:
- Eliberare pentru QoS 2
- Nu are payload

PUBCOMP
- Confirmare finala pentru QoS 2
- Nu are payload

**5.5 Pachetul SUBSCRIBE**

<img width="331" height="155" alt="image" src="https://github.com/user-attachments/assets/97f4caf2-7207-4baa-afb5-31e8ae4b8452" />

Clientul foloseste acest pachet pentru a se abona la topicuri.

Variable Header contine:  
- Packet Identifier: 2 bytes

Payload contine:  
- Lista de perechi Topic Filter + QoS:
- Topic Filter: String UTF-8 (poate contine wildcards)
- QoS: 1 byte (0, 1, sau 2)

Exemple de topic filters:  
* "home/livingroom/temperature" - topic exact
* "home/+/temperature" - wildcard single level
* "home/#" - wildcard multi level

**5.6 Pachetul SUBACK**

<img width="335" height="160" alt="image" src="https://github.com/user-attachments/assets/48030cbd-3bd6-4e94-a330-8a64eb32c3a1" />

Brokerul confirma abonarea cu SUBACK.

  Variable Header contine:  
- Packet Identifier: 2 bytes (acelasi ca in SUBSCRIBE)

  Payload contine:  
- Lista de Return Codes (cate unul pentru fiecare subscription):
  - 0: Success - Maximum QoS 0
  - 1: Success - Maximum QoS 1
  - 2: Success - Maximum QoS 2
  - 128: Failure

**5.7 Pachetul UNSUBSCRIBE**

<img width="325" height="182" alt="image" src="https://github.com/user-attachments/assets/ed369b6a-ccd5-4846-9d29-7aa9e415e038" />

Clientul se dezaboneaza de la topicuri.

Variable Header contine:  
- Packet Identifier: 2 bytes

Payload contine:  
- Lista de Topic Filters (string UTF-8)

**5.8 Pachetul UNSUBACK**

<img width="348" height="177" alt="image" src="https://github.com/user-attachments/assets/a730908f-b0df-4ce8-8d7a-007dc2881712" />

Brokerul confirma dezabonarea.

Variable Header contine:  
- Packet Identifier: 2 bytes

Nu are Payload (in MQTT 3.1.1)  
In MQTT 5 are Return Codes  

**5.9 Pachetele PINGREQ si PINGRESP**

<p><img style="text-align:left" width="262" height="172" alt="image" src="https://github.com/user-attachments/assets/76b7fd0b-21a6-4461-b1c1-6e35388a6b34" />
<img style="text-align:right" width="271" height="172" alt="image" src="https://github.com/user-attachments/assets/9d40fa03-130c-4302-8b57-4783006d4df8" /></p>

Folosite pentru mecanismul Keep Alive.

PINGREQ:  
- Trimis de client pentru a verifica conexiunea
- Doar Fixed Header (2 bytes)
- Nu are Variable Header
- Nu are Payload

PINGRESP:  
- Raspuns de la broker
- Doar Fixed Header (2 bytes)
- Nu are Variable Header
- Nu are Payload

**5.10 Pachetul DISCONNECT**

<img width="307" height="173" alt="image" src="https://github.com/user-attachments/assets/a0ad5acf-6213-4542-9917-496527758733" />

Clientul inchide conexiunea voluntar.

Doar Fixed Header in MQTT 3.1.1  

In MQTT 5:  
- Poate contine Reason Code
- Poate contine Session Expiry Interval
- Poate fi trimis si de catre broker

## 6. Fluxuri de Interactiune Client-Broker

**6.1 Stabilirea Conexiunii**

<img width="492" height="180" alt="image" src="https://github.com/user-attachments/assets/7e63bf97-8d41-4782-ab0b-1b76b677a488" />

Pasi:  
1. Clientul deschide conexiune TCP/IP catre broker (port 1883 sau 8883 pentru TLS)
2. Clientul trimite pachet CONNECT
3. Brokerul valideaza credentialele si parametrii
4. Brokerul trimite CONNACK cu rezultatul
5. Daca este acceptat, conexiunea este stabilita

Detalii importante:  
- Daca CONNECT nu e trimis rapid, brokerul poate inchide conexiunea
- Clean Session = true: sterge orice sesiune anterioara
- Clean Session = false: creeaza sesiune persistenta

**6.2 Publicarea Mesajelor - QoS 0**

<img width="583" height="163" alt="image" src="https://github.com/user-attachments/assets/c973534c-9d83-4841-ad59-9155654abcbd" />

Caracteristici:  
- "Fire and forget"
- Fara confirmare
- Mesajul poate fi pierdut
- Overhead minim

**6.3 Publicarea Mesajelor - QoS 1**

<img width="551" height="176" alt="image" src="https://github.com/user-attachments/assets/3aba3c7e-9672-4bf4-b54f-c0255894ea9e" />

Caracteristici:  
- "At least once"
- Confirmare obligatorie
- Mesajul poate fi livrat de mai multe ori
- Retransmisie daca nu primeste PUBACK

**6.4 Publicarea Mesajelor - QoS 2**

<img width="556" height="242" alt="image" src="https://github.com/user-attachments/assets/08cc10e3-26a1-4b39-972b-5a4a33f4da72" />

Caracteristici:  
- "Exactly once"
- Handshake in 4 pasi
- Garantie de livrare unica
- Overhead maxim

**6.5 Abonarea la Topicuri**

<img width="557" height="198" alt="image" src="https://github.com/user-attachments/assets/dfcc19d9-0a2e-49d2-b5f3-204b21a4c88c" />

Pasi:  
1. Clientul trimite SUBSCRIBE cu lista de topicuri si QoS dorit
2. Brokerul valideaza permisiunile
3. Brokerul trimite SUBACK cu return codes
4. Clientul primeste mesaje publicate pe acele topicuri

**6.6 Dezabonarea**

<img width="494" height="187" alt="image" src="https://github.com/user-attachments/assets/cdafa7ab-9b74-4c78-91f6-47b8eed92ad1" />

**6.7 Mecanismul Keep Alive**

<img width="537" height="233" alt="image" src="https://github.com/user-attachments/assets/3c3c42cd-41db-4974-bce1-629ea6f612b2" />

Functionare:  
- Client specifica Keep Alive interval in CONNECT
- Daca nu se trimite niciun mesaj in acest interval, se trimite PINGREQ
- Broker raspunde cu PINGRESP
- Daca broker nu primeste PINGREQ in 1.5 x Keep Alive, inchide conexiunea
- Daca client nu primeste PINGRESP, poate inchide conexiunea

**6.8 Deconectarea**

<img width="505" height="169" alt="image" src="https://github.com/user-attachments/assets/1ee7c956-faae-44b2-81ee-b8110735c8d3" />

Caracteristici:  
- Deconectare “gratioasa”
- Broker NU trimite Last Will Message
- Broker poate salva sesiunea (daca Clean Session = false)

**6.9 Last Will and Testament (LWT)**

<img width="582" height="232" alt="image" src="https://github.com/user-attachments/assets/d86b99ce-e857-4371-a4d7-82f6d93d9474" />

Functionare:  
- Client specifica LWT in CONNECT:
	- Will Topic
  	- Will Message
  	- Will QoS
  	- Will Retain
- Broker stocheaza aceste informatii
- Daca clientul se deconecteaza neasteptat, broker publica LWT
- Daca clientul trimite DISCONNECT, broker NU publica LWT

**6.10 Retained Messages**

<img width="622" height="185" alt="image" src="https://github.com/user-attachments/assets/00303736-e071-459c-9383-2c4f7ea24943" />

Caracteristici:  
- Broker pastreaza ultimul mesaj cu Retain=true pentru fiecare topic
- Subscriber nou primeste imediat retained message
- Util pentru status updates
- Pentru a sterge: publica mesaj gol cu Retain=true

**6.11 Persistent Sessions**

La conectare cu Clean Session = false:  

<img width="644" height="200" alt="image" src="https://github.com/user-attachments/assets/a1a46949-dd54-4635-9670-3b00fc1c6acf" />

Ce pastreaza brokerul:  
- Toate subscriptiile clientului
- Mesajele QoS 1 si 2 care nu au fost confirmate
- Mesajele QoS 1 si 2 primite in timpul offline
- Mesajele QoS 2 de la client care asteapta confirmare

Exemplu de recuperare dupa deconectare:  
1. Client se conecteaza cu Clean Session=false
2. Client se aboneaza la "sensors/temperature"
3. Client se deconecteaza  neasteptat
4. Broker primeste 5 mesaje pe "sensors/temperature" (QoS 1)
5. Broker bufferizeaza aceste mesaje
6. Client se reconecteaza cu Clean Session=false
7. Broker trimite mesajele bufferizate

## 7. Caracteristici noi MQTT 5 fata de MQTT 3

**7.1 Session Expiry Interval**

In CONNECT packet:  
Session Expiry Interval: 3600 secunde (1 ora)
- Daca 0: sesiunea se sterge la deconectare
- Daca > 0: sesiunea persista pentru intervalul specificat
- Maxim: 4,294,967,295 secunde (136 ani)

**7.2 Message Expiry Interval**

In PUBLISH packet: 
Message Expiry Interval: 300 secunde (5 minute)
- Mesajul este valid doar pentru acest interval
- Daca nu e livrat in acest timp, se sterge
- Util pentru mesaje time-sensitive

**7.3 User Properties**

In orice pachet:
```
User Property: "region" = "europe"
User Property: "sensor-type" = "temperature"
User Property: "version" = "1.0"
```
- Perechi cheie-valoare custom
- Pot fi multiple
- Folosite pentru metadata
- Similare cu HTTP headers

**7.4 Topic Alias**

Primul mesaj:
```
PUBLISH
	Topic: "very/long/topic/name/for/sensor/data"
	Topic Alias: 1
	Payload: data
```
Mesajele urmatoare:
```
PUBLISH
	Topic: "" (empty)
	Topic Alias: 1
	Payload: data
```
- Reduce bandwidth-ul pentru topicuri lungi
- Negociat la conexiune prin Topic Alias Maximum

**7.5 Shared Subscriptions**

<img width="598" height="193" alt="image" src="https://github.com/user-attachments/assets/eaae41c4-772a-4deb-bd9a-57d7e8a7dfe3" />

Sintaxa:  
```$share/{group-name}/{topic-filter}```

Caracteristici:  
- Load balancing automat
- Mesajele sunt distribuite intre membri grupului
- Useful pentru scalare orizontala

**7.6 Reason Codes si Reason Strings**

MQTT 5 ofera feedback detaliat: 
```
	CONNACK
  		Reason Code: 135 (Not authorized)
  		Reason String: "Invalid credentials for user 'sensor01'"
```
```
	PUBACK
 		Reason Code: 151 (Quota exceeded)
 		Reason String: "Message rate limit exceeded"
```
Beneficii:  
- Debugging mai usor
- Transparenta sporita
- Mesaje de eroare clare

## 8. Securitate in MQTT

**8.1 Transport Layer Security (TLS)**

<img width="585" height="207" alt="image" src="https://github.com/user-attachments/assets/2f962803-32d1-4d55-8c8c-5c300e54c637" />

Port-uri standard:  
- 1883: MQTT fara TLS
- 8883: MQTT cu TLS

**8.2 Autentificare Username/Password**

In CONNECT packet:  
   
`Username: "sensor_001"`

`Password: "secure_password_123"`
   
Best practices:  
- TLS cu username/password
- Parole sigure
- Rate limiting
- Logare incercarile failed

**8.3 Enhanced Authentication (MQTT 5)**

Flow cu SCRAM:  

<img width="511" height="341" alt="image" src="https://github.com/user-attachments/assets/a526423c-72da-45f4-ba2f-a2a6104eb6f9" />

Metode suportate:  
- SCRAM-SHA-1
- SCRAM-SHA-256
- Kerberos
- OAuth

## 9. Optimizari si Best Practices

**9.1 Alegerea QoS Potrivit**

QoS 0:  
- Telemetrie non-critica
- Date redundante (citiri frecvente)
- Overhead minim necesar
- Exemplu: Temperatura citita la fiecare secunda

QoS 1:  
- Majoritatea use case-urilor
- Balans intre reliability si performance
- Permite duplicate (care trebuie gestionate)
- Exemplu: Alarme, notificari

QoS 2:  
- Tranzactii financiare
- Comenzi critice (un singur unlock)
- Updates de firmware
- Exemplu: Plati, comenzi industriale

**9.2 Structura Topicurilor**

| Buna ✔️ | Rea ✖️ |
| -------- | ------ |
| devices/sensors/temperature/livingroom| mycompany/devices/sensors/temperature/livingroom (prefix inutil) |
| devices/sensors/humidity/kitchen | /devices/temperature (leading slash) |
| devices/actuators/lights/bedroom | devices temperature livingroom (spaces) |

Reguli:  
- Folosire forward slash (/) ca separator
- Evitarea leading slash
- Fara spatii
- Folosirea caracterelor ASCII
- Topicuri scurte dar descriptive
- Structura ierarhica logica

**9.3 Wildcard Subscriptions**

Single-level wildcard (+):
```
	home/+/temperature
	Matches:
		- home/livingroom/temperature
		- home/kitchen/temperature
	Does NOT match:
		- home/livingroom/sensor/temperature
```

Multi-level wildcard (#):  
```
	home/livingroom/ 
	Matches:
		- home/livingroom/temperature
		- home/livingroom/humidity
		- home/livingroom/sensor/temperature
		- home/livingroom/sensor/humidity/current
```

Best practice:  
- Evitarea abonarii la "#" (toate mesajele)
- Folosire wildcards specific(+)
- Grupare date similare in ierarhie

**9.4 Client ID**

Reguli:  
- Unic per conexiune
- Maxim 23 caractere (MQTT 3.1.1)
- Poate fi generat de broker daca e empty (cu Clean Session=true)
- Include identifier unic al device-ului
  
Exemple:
|Good ✔️|Bad ✖️|
|-------|-------|
| "sensor-001-livingroom" | "client" |
| "mobile-app-user123" | "sensor_with_very_long_identifier_exceeding_23_chars" |

**9.5 Keep Alive**

 Valori recomandate:  
- Conexiuni stabile: 60-300 secunde
- Conexiuni mobile: 30-60 secunde
- Conexiuni satelit: 300+ secunde
- Testing: 5-10 secunde

Formula:  
`Keep Alive > (timpul maxim asteptat fara mesaje)  * 1.5`

**9.6 Session Management**

Se foloseste cand:

|  Persistent Sessions (Clean Session=false)  | Clean Sessions (Clean Session=true) |
| -----|-----|
| Clientul trebuie sa primeasca toate mesajele | Clientul doar publica |
| Clientul are conexiune intermitenta | Mesajele offline nu sunt importante |
| QoS 1 sau 2 sunt necesare | Clientul se conecteaza rar |

**9.7 Message Size**

Recomandari:  
- Mesaje scurte (<1KB ideal)
- Folosirea compresiei pentru payloads mari
- Batching pentru citiri multiple
- Maxim: 256MB (dar de evitat)

Exemplu payload eficient:  
```json
{
  "t": 22.5,
  "h": 65,
  "ts": 1634567890
}
```

versus payload ineficient:

```json
{
  "temperature": 22.5,
  "humidity": 65,
  "timestamp": 1634567890,
  "sensor_id": "sensor-001",
  "location": "livingroom"
}
```

## 10. Diagrama proiectare:
<img width="1443" height="1556" alt="arch cu culori" src="https://github.com/user-attachments/assets/085d0f8f-3826-4c05-a32b-62532341e168" />

**10.1 PIPELINE CONNECT:**
<img width="1443" height="1554" alt="PIPELINE CONNECT" src="https://github.com/user-attachments/assets/370013be-17cd-4f0d-b543-7d3e648fffdd" />

**10.2 PIPELINE DISCONNECT:**
<img width="3736" height="2021" alt="PIPELINE DISCONNECT" src="https://github.com/user-attachments/assets/0aa04265-71bb-48ec-8957-f6b100732153" />

**10.3 PIPELINE PING:**
<img width="1443" height="1554" alt="PIPELINE PING" src="https://github.com/user-attachments/assets/4425c421-dfca-49c3-b140-c6fbdd94fd58" />

**10.4 PIPELINE PUBLISH:**
<img width="1443" height="1554" alt="PIPELINE PUBLISH" src="https://github.com/user-attachments/assets/b3d4cdd4-3ee8-4e31-a64a-edb16c24af88" />

**10.5 PIPELINE SUBSCRIBE:**
<img width="1443" height="1554" alt="PIPELINE SUBSCRIBE" src="https://github.com/user-attachments/assets/6314e12c-9227-4796-9358-c73dc9330727" />

## Bibliografie:
* https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.pdf
* hivemq-ebook-mqtt-essentials






























