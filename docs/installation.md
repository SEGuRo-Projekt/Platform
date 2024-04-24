# Installation

1. Install SEGuRo project (and its dependencies) in editable mode
```bash
pip install poetry
poetry install
```
2. Create `.env` file including parameters for platform delpoyment. See: [Configuration](configuration.md).
3. Start platform via Docker Compose
```bash
docker compose up --detach
```

3. Open the [home page](https://localhost)
