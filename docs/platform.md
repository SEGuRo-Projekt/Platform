# Platform

**Code:** [github.com/SEGuRo-Projekt/Platform](https://github.com/SEGuRo-Projekt/Platform)


The SEGuRo platform is based on a [microservice architecture](https://en.wikipedia.org/wiki/Microservices).

Microservice architecture is a software design approach where an application is composed of a collection of small, independent services, each focusing on a specific business capability.
These services can be developed, deployed, and maintained independently, enabling greater flexibility, scalability, and resilience.
Microservices communicate with each other through APIs, often using lightweight protocols such as HTTP/REST or message queues.
This architecture allows teams to work on different services simultaneously, and services can be scaled up or down independently to handle different levels of demand.
Additionally, microservices promote modularity and can simplify the overall system, improving maintainability and reducing the impact of changes on the rest of the system.

Services in the SEGuRo platform are categorized into two groups:

- **Platform services** provide core functionality of the platform itself and enable _application services_.
- **Application services** provide application-specific functionality and are usually provided by the user.


## Data Store

The data store (also object store) provides the central data storage in the platform.
This store is used to persist time series data such as measurement data or load/weather data as well as network and configuration data.
With the exception of the object memory, all other components of the platform are largely stateless.
This central storage of data simplifies data management, as data can be backed up or access rights for the entire platform can be managed centrally, for example.

The SEGuRo platform uses the Simple Storage Service (S3) interface, which is widely used in the industry, to implement the object storage.
S3 is a scalable cloud storage service that was originally introduced by Amazon Web Services (AWS), but has since established itself as an industry standard.
It enables the storage and retrieval of data via the internet.
S3 uses an object storage approach in which data is stored in so-called buckets. Each bucket can contain any number of objects, which are identified by a unique key (e.g. URL).

The main features of S3 are:
- **Scalability:** S3 enables the storage of virtually unlimited amounts of data and automatic scaling as required.
- **Reliability and durability:** Data in S3 is highly available and durable. S3 automatically replicates data to multiple data centers to ensure resilience.
- **Security:** S3 offers various security mechanisms, including encryption, access control lists (ACLs) and access authorizations via AWS Identity and Access Management (IAM).
- **Flexibility:** S3 supports various data formats and enables access to data via APIs or directly via the web.
- **Cost efficiency:** The prices for data stored in an S3 bucket with common cloud providers depend on the amount of storage used, the requests and the data transfer.

In the SEGuRo platform, the S3 object storage is realized with the help of the open source software [Minio](https://min.io/).

## Message Broker

The message broker is the central hub for the exchange of signals in real-time.
This includes measurement data from the measuring points, which is streamed to the broker immediately after acquisition, as well as intermediate results from the simulations of the digital twin or the state estimation.
Additional external sources of information, such as weather data, can also be integrated into the platform via the broker.
In the SEGuRo platform, communication with the message broker is realized using the MQTT protocol.

MQTT (Message Queuing Telemetry Transport) is an open network protocol that is optimized for the transmission of messages between devices in a distributed network.
It was developed to enable efficient communication in environments with limited bandwidth and unreliable network connections.
MQTT works according to the publish/subscribe principle, in which devices (clients) can publish messages on specific topics and subscribe to these messages from other devices.

The protocol consists of various components:
- **Broker:** A central server that coordinates communication between the clients. The broker receives messages from the publishers and forwards them to the subscribers.
- **Publisher:** A client that publishes messages on specific topics. These topics serve as channels for message transmission.
- **Subscriber:** A client who subscribes to certain topics and thus receives messages from publishers on these topics.
- **Message:** The actual unit of information sent by publishers to the broker and then forwarded to the relevant subscribers.
- **Topic:** A hierarchical identifier used to categorize messages. Clients can subscribe to messages based on topics.
- **QoS (Quality of Service):** A mechanism that regulates the reliability of message transmission. There are three QoS levels: 0 (At most once), 1 (At least once) and 2 (Exactly once).

MQTT offers flexibility, scalability and low overhead, making it a popular choice for Internet of Things (IoT) applications and other networked environments.

In the SEGuRo platform, the MQTT broker is realized with the help of the open source software [Eclipse Mosquitto](https://mosquitto.org/).

## Public Key Infrastructure (PKI)

A Public Key Infrastructure (PKI) is a framework that provides a secure environment for the exchange of information over the internet.
It uses public and private key cryptography to secure data, authenticate entities, and enable digital signatures and certificates.
In the SEGuRo context, the PKI includes two components: a Certificate Authoritiy (CA) that issue and manage digital certificates, and a Timestamping Authority (TSA), a trusted third party that issues time stamps certifying the time and date of a digital event or transaction, ensuring its integrity and non-repudiation.

By providing these services, a PKI establishes trust and security in electronic communications and transactions.

### Certificate Authority (CA)

A Certificate Authority (CA) is a trusted entity that issues digital certificates, which are data files used to cryptographically link an entity with a public key.
In the realm of public key infrastructure (PKI), CAs play a critical role in providing assurances about the identity of entities involved in a digital transaction or communication exchange.
These digital certificates are used in numerous internet protocols and systems, like HTTPS for secure web browsing, to authenticate and secure the data transmission.
They are crucial components for establishing secure connections in a digital world where the identities of the parties involved can't always be verified in person.
The process typically involves the CA verifying the identity or attributes of the entity requesting the certificate.
Once identity is validated, the CA creates a digital certificate that includes the entity's public key and other identification information. This digital certificate is then digitally signed with the CA's private key, essentially vouching for the entity's identity.
Utilizing the CA's public key, others can verify the authenticity of the digital certificate.
Having a centralized and trusted authority issuing these certificates is a crucial aspect of maintaining trust and security in the digital landscape.
It is the responsibility of the CA to ensure that their process of issuing certificates is stringent, to prevent any security breaches or issuance to malicious entities.

### Timestamping Authority (TSA)

A Timestamping Authority (TSA) primary role is to generate trusted timestamps that can be used within various computational contexts.
These timestamps are digital receipts providing proof that a certain piece of data existed at a specific moment in time.
They are a critical part of establishing non-repudiation, the concept that guarantees that the creator of certain data cannot deny the authenticity of their production or transmission.
TSAs work by taking in a piece of data, generating a timestamp that reflects the exact time it received the data, and then signing both the data and the timestamp with a trusted digital certificate.
This process creates a digital proof that the data existed in the specific state at the specific time the timestamp indicates.
Timestamping is widely used in industries like law, finance, digital forensics, and any other situation where proving the existence of data at a specific time is important.
However, the TSA itself doesn't inspect or even store the actual data—it only confirms the time of its existence.
This makes it suitable for a variety of applications while maintaining data privacy and confidentiality.

## Scheduler

**Code:** [`seguro/commands/scheduler`](https://github.com/SEGuRo-Projekt/Platform/tree/main/seguro/commands/scheduler)

The scheduler, manages application services (either _job workers_ or _streaming workers_) by starting and stopping their respective containers using the Docker daemon.

The scheduler acts on specifications which are stored in YAML format on the _data store_.
The scheduler watches the data store for any newly added, removed or modified specifications and ensures that the currently active and scheduled service in the platform are in sync with those specifications.

Scheduled services can be:
- short-lived to service data processing tasks (_job worker_) which are triggered by events in the platform.
- long-lived to continuously perform their tasks (_streaming worker_).

Supported events in the platform are:

- Data store-related:
  - `created`: A new object has been added to the data store.
  - `removed`: An existing object has been deleted from the data store.
  - `modified`: An existing object has been replaced in the data store.

- Scheduling-related:
  - `schedule`: A calendar / time-based event.

- Life cycle-related:
  - `startup`: The scheduler has been started.
  - `shutdown`: The scheduler has been stopped.

Data store events can be further limited to certain object paths in the store.

Scheduled events can occur at a fixed point in time or at regular intervals.

Life cycle events are used to start long-lived services at the start-up of the platform or to perform housekeeping tasks when the platform is shut down.

## Sample Recorder

**Code:** [`seguro/commands/scheduler`](https://github.com/SEGuRo-Projekt/Platform/tree/main/seguro/commands/scheduler)

The sample recorder is a bridge between the real-time message broker and the data store.
It aggregates measurement samples transported over the message broker into blocks and stores those blocks as [Parquet files](https://en.wikipedia.org/wiki/Apache_Parquet) in the data store.

Persisted measurements can then be later processed by _job workers_.

The scheduler can watch for newly added blocks of measurements data and trigger these _job workers_.

## Notifier

**Code:** [`seguro/commands/notifier`](https://github.com/SEGuRo-Projekt/Platform/tree/main/seguro/commands/notifier)

The notifier service watches for notification messages on the message broker and relays them to more common notification channels such as mail and instant messengers.

The service uses the established notification library [Apprise](https://github.com/caronc/apprise) to deliver notifications which supports a wide variety of notification channels.

## Alerter

**Code:** _to be written_

The alerter service monitors if messages published broker conform to certain rules.

If any threshold violation or similar is detected, it sends a notification message back to the broker which gets consumed by the notifier service.

## ACL Syncer

**Code:** [`seguro/commands/acl_syncer`](https://github.com/SEGuRo-Projekt/Platform/tree/main/seguro/commands/acl_syncer)

The ACL syncer service maintains the access control lists (ACL) of both the data store and the message broker.
The service uses a common ACL, stored in YAML format on the data store, to configure the ACLs of the store and broker.

## Signature Recorder

**Code:** [`seguro/commands/signature_recorder`](https://github.com/SEGuRo-Projekt/Platform/tree/main/seguro/commands/signature_recorder)

The signature recorder subscribes to signatures published by the signature sender and stores them into the data store.

Together with the sample recorder, this results in both the sample data itself and the signatures over them to be persisted in the data store.
This allows for verifying the data integrity of the data stored at any later point in time.

## Application Services

In the SEGuRo platform, application services are roughly categorized into two groups:

### Job Workers

#### Notebook Executor

**Code:** [`seguro/commands/notebook_executor`](https://github.com/SEGuRo-Projekt/Platform/tree/main/seguro/commands/notebook_executor)

#### Streaming Workers
