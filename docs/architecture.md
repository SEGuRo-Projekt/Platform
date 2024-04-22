# Platform Architecture

![overview](./_static/platform_architecture.png)

## Data Integrity

![data_integrity](./_static/data_integrity.png)

## Signing Chain

![data_signing](./_static/data_signing.png)

## Components

### `scheduler`: Execute triggered jobs

**Code:** [github.com/SEGuRo-Projekt/Platform/seguro/commands/scheduler](https://github.com/SEGuRo-Projekt/Platform/tree/main/seguro/commands/scheduler)

### `recorder`: Persist real-time data from broker into data store

**Code:** [github.com/SEGuRo-Projekt/Platform/seguro/commands/scheduler](https://github.com/SEGuRo-Projekt/Platform/tree/main/seguro/commands/scheduler)

### `notifier`: Notify users about events in the platform

**Code:** [github.com/SEGuRo-Projekt/Platform/seguro/commands/notifier](https://github.com/SEGuRo-Projekt/Platform/tree/main/seguro/commands/notifier)

### `acl-syncer`: Configure Access Control Lists (ACL)

**Code:** [github.com/SEGuRo-Projekt/Platform/seguro/commands/acl_syncer](https://github.com/SEGuRo-Projekt/Platform/tree/main/seguro/commands/acl_syncer)

### `heartbeat-sender`: Send regular heartbeat status messages from gateway to platform

**Code:** [github.com/SEGuRo-Projekt/Platform/seguro/commands/heartbeat_sender](https://github.com/SEGuRo-Projekt/Platform/tree/main/seguro/commands/heartbeat_sender)

### `signature-sender`: Calculate and send cryptographic signatures of measurement data

**Code:** [github.com/SEGuRo-Projekt/Platform/seguro/commands/signature_sender](https://github.com/SEGuRo-Projekt/Platform/tree/main/seguro/commands/signature_sender)

### `signature-recorder`: Store cryptographic signatures in data store

**Code:** [github.com/SEGuRo-Projekt/Platform/seguro/commands/signature_recorder](https://github.com/SEGuRo-Projekt/Platform/tree/main/seguro/commands/signature_recorder)

### `notebook-executor`: Produce reports by evaluating Jupyter Notebooks

**Code:** [github.com/SEGuRo-Projekt/Platform/seguro/commands/notebook_executor](https://github.com/SEGuRo-Projekt/Platform/tree/main/seguro/commands/notebook_executor)
