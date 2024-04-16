# Configuration

## Environment Variables

During startup, the platform retrieves configuration parameters (such as admin credentials for the web UI) from environment variables specified in the `.env` file.

> Note: It is required to manually create a `.env` file in the platform root directory, before initiating the platform with docker compose!

For an example configuration, see [`.env.example`](https://github.com/SEGuRo-Projekt/Platform/blob/main/.env.example):

```{literalinclude} ../.env.example
```
