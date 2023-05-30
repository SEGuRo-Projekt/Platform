# Plattform

Dieses ist das Git Repository der SEGuRo Plattform.

## Architektur

![](./docs/images/Platform%20Architektur.jpg)

```mermaid

flowchart LR
    broker[Message\nBroker] --> recorder{{Recorder}}
    recorder -->  store[(Data\nStore)]

    store --> player{{Player}}
    player --> broker

    ms[Messstellen] --> broker



    scheduler([Scheduler])
    worker[Streaming\nWorker]

    alarm[Alarmierung]
    dashboard[Web\nDashboard]

    repo[Docker Repo]

    worker <--> broker
    dt[DT] <--> broker
    dt <--> store
    job[Job] <--> store
    alarm <--> broker
    broker --> dashboard
    store --> dashboard

    store -->|config| scheduler
    scheduler -->|starts| job
    repo <--> store

    pki[CloudPKI]
    ids[IDS]


    classDef custom fill:lightblue
    class player,recorder,worker,scheduler,alarm custom
```

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
