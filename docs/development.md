# Development

## With [Docker](https://www.docker.com/) & [Devcontainer](https://containers.dev/)

1. Install Docker, Git & Visual Studio Code
2. Clone Repo: `git clone git@github.com:SEGuRo-Projekt/Platform.git`
3. Open Repo as [Devcontainer in Visual Studio Code](https://code.visualstudio.com/docs/devcontainers/containers)
  - Press:  Ctrl + Shift + P
  - Type: `Dev Containers: Reopen in container`
  - Press Enter
  - Wait (the initial setup can take a couple of minutes)

## Manual

1. Clone Repo: `git clone git@github.com:SEGuRo-Projekt/Platform.git`
2. Install Poetry: `pip install poetry`
3. Install Python packages and dependencies: `poetry install`
4. Start Platform via Docker Compose: `docker compose up -d`
