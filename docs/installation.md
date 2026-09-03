# Installation

1. Choose python version `3.13.12`

2. Install SEGuRo project (and its dependencies) in editable mode
```bash
pip install uv
uv sync
```
3. Create `.env` file including parameters for platform deployment. See: [Configuration](configuration.md).
4. Start platform via Docker Compose
```bash
docker compose up --detach
```

5. Open the [home page](https://localhost)
