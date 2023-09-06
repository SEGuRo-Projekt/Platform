# Plattform

Dieses ist das Git Repository der SEGuRo Plattform.

## Architektur

### Übersicht

![overview](./docs/platform_architecture.png)

### Daten Integrität

![data_integrity](./docs/data_integrity.png)

### Daten Signierung

![data_signing](./docs/data_signing.png)

## Konfiguration

Siehe [.env](./.env).

## Nutzung

```bash
docker compose up --detach --build
```

- **Object Store Frontend:**
  - **URL:** http://localhost:9001/
  - **Nutzername:** seguro
  - **Passwort:** stwh4herne
- **Docker Registry Frontend:**
  - **URL:** http://localhost:8080
- **Docker Dashboard:**
  - **URL:** http://localhost:8000
  - **Nutzername:** admin@yacht.local
  - **Passwort:** pass


## Entwicklung

1. Install Docker, Git & Visual Studio Code
2. Clone Repo: `git clone git@github.com:SEGuRo-Projekt/Plattform.git`
3. Setup environment:

```bash
python -m venv .venv
. .venv/scripts/activate
#. .venv/bin/activate (on Linux)
pip install -r python/requirements.txt
pip install -r python/requirements-dev.txt
pre-commit install
pip install --editable .
```

## Lizenz

SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH\
SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen  University\
SPDX-License-Identifier: Apache-2.0
