# Gateway

**Code:** [github.com/SEGuRo-Projekt/Gateway](https://github.com/SEGuRo-Projekt/Gateway)

Although the measurement data gateway itself is not part of the platform, it provides the primary source of data that is processed by it.

## Data Gateway

**Code:** [github.com/VILLASframework/node](https://github.com/VILLASframework/node)

The SEGuRo gateway uses [VILLASnode](https://github.com/VILLASframework/node) as a gateway to transport samples from a measurement device to the message broker of the platform.

VILLASnode supports various established automation communication protocols to interact with measurement devices and the platform. In this context the measurement device interfaced via the [OPC-UA protocol](https://en.wikipedia.org/wiki/OPC_Unified_Architecture) and samples are forwarded to the platform using the [MQTT protocol](https://en.wikipedia.org/wiki/MQTT).

The gateway is tightly integrated with the [_signature sender_](#signature-sender) as it groups the sample data into blocks and calculates message digests over them which are passed to the [_signature sender_](#signature-sender) for signing.

## Signature Sender

**Code:** [`seguro/commands/signature_sender`](https://github.com/SEGuRo-Projekt/Platform/tree/main/seguro/commands/signature_sender)

The signature sender is another service running on the measurement gateway itself.

It receives [cryptographic message digests (hashes)](https://en.wikipedia.org/wiki/Cryptographic_hash_function) over blocks of the acquired measurement samples.

The service then produces two digital cryptographic signatures over the message digest:
- **Proof of Time:** A signature issued by a [Timestamping Authority (TSA)](platform.md#timestamping-authority-tsa) notarizing the point time at which the measurements have been gathered.
- **Proof of Origin:** A signature issued by a the gateway itself notarizing the origin from which measurements have been gathered.

Both signatures are published by the service to the platform via the message broker.

## Heartbeat Sender

**Code:** [`seguro/commands/heartbeat_sender`](https://github.com/SEGuRo-Projekt/Platform/tree/main/seguro/commands/heartbeat_sender)

The heartbeat sender is a service which is not running in the platform itself, but is executed in regular intervals on the measurement gateway.

It gathers basic metrics of the measurement gateway and publishes them via the message broker to the platform.
On the platform these heartbeat messages are used to monitor the status of the gateway device and support troubleshooting of the remotely deployed devices.
