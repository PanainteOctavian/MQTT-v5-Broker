# MQTT Project

## Demo
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/d62c7d4c-337c-4fc0-ba64-b73c138c8102" />

## 1. Introduction
MQTT (Message Queuing Telemetry Transport) is a lightweight messaging protocol based on the publish/subscribe architecture. It is specifically designed for devices with limited resources and high-latency networks. The protocol uses a binary message format to minimize overhead and ensure highly efficient communication.

## 2. MQTT System Components
* **MQTT Client**: Any device running an MQTT library that connects to a broker. It can act as a publisher, a subscriber, or both.
* **MQTT Broker**: The intermediary between clients that receives all messages from publishers, filters and routes them to subscribers, manages authentication/authorization, and maintains client sessions.

## 3. MQTT Packet Types
MQTT defines 15 control packet types:
1. **CONNECT** – Client initiates connection.
2. **CONNACK** – Broker acknowledges connection.
3. **PUBLISH** – Client publishes a message.
4. **PUBACK** – Acknowledgment for QoS 1 PUBLISH.
5. **PUBREC** – Receipt acknowledgment for QoS 2 (Part 1).
6. **PUBREL** – Release packet for QoS 2 (Part 2).
7. **PUBCOMP** – Completion acknowledgment for QoS 2 (Part 3).
8. **SUBSCRIBE** – Client subscribes to topics.
9. **SUBACK** – Broker acknowledges subscription.
10. **UNSUBSCRIBE** – Client unsubscribes.
11. **UNSUBACK** – Broker acknowledges unsubscription.
12. **PINGREQ** – Client checks connection status.
13. **PINGRESP** – Broker responds to PING.
14. **DISCONNECT** – Client initiates voluntary disconnection.
15. **AUTH** – Authentication (MQTT v5 only).

## 4. General Packet Structure
Every MQTT packet contains:
* **Fixed Header**: Present in all packets (min. 2 bytes), containing the message type and flags (DUP, QoS, RETAIN).
* **Variable Header**: Present in some packets; contains the Packet ID and specific properties.
* **Payload**: The actual content of the message (up to 256MB).
* **Reason Code**: A numeric code representing the result of an operation (values < 0x80 indicate success).

## 5. Core Interaction Flows

### 5.1 Quality of Service (QoS) Levels
* **QoS 0 (Fire and Forget)**: Minimal overhead; message may be lost as there is no confirmation.
* **QoS 1 (At Least Once)**: Mandatory confirmation via PUBACK; ensures delivery but might result in duplicates.
* **QoS 2 (Exactly Once)**: Four-step handshake; guarantees unique delivery with maximum overhead.

### 5.2 Connection and Reliability
* **Keep Alive**: A mechanism where the client sends a PINGREQ if no messages are transmitted within a specified interval to keep the connection active.
* **Last Will and Testament (LWT)**: Information stored by the broker and published only if the client disconnects unexpectedly.
* **Persistent Sessions**: If `Clean Session = false`, the broker stores subscriptions and missed QoS 1/2 messages while the client is offline.

## 6. New Features in MQTT 5
* **Session & Message Expiry**: Allows setting time limits for how long sessions or individual messages remain valid.
* **User Properties**: Custom key-value pairs (metadata) similar to HTTP headers.
* **Topic Alias**: Reduces bandwidth by using an integer ID instead of a long topic string.
* **Shared Subscriptions**: Enables load balancing by distributing messages among a group of subscribers.

## 7. Security Best Practices
* **TLS**: Use port 8883 for encrypted communication.
* **Authentication**: Use strong usernames/passwords or MQTT 5 Enhanced Authentication (SCRAM, OAuth).
* **Topic Structure**: Use logical hierarchies with forward slashes (`/`), avoid leading slashes, and keep topics descriptive yet short.

## 8. Topic Wildcards
* **Single-level (+)**: Matches one level (e.g., `home/+/temp` matches `home/kitchen/temp`).
* **Multi-level (#)**: Matches all remaining levels (e.g., `home/#` matches everything under home).
