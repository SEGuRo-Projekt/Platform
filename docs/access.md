# Access

The components compromising the SEGuRo platform are accessible via various sub-domains of `seguro`:

- [`localhost`](https://localhost) Platform Landing Page
- [`ui.localhost`](https://ui.localhost) Docker Web-Interface ([Yacht](https://yacht.sh/))
- [`store.localhost`](https://store.localhost) S3 Datastore ([Minio](https://min.io/))
- [`ui.store.localhost`](https://ui.store.localhost) S3 Datastore Web-Interface
- [`registry.localhost`](https://registry.localhost) Docker Image Registry ([distribution](https://distribution.github.io/distribution/about/))
- [`ui.registry.localhost`](https://ui.registry.localhost) Docker Image Registry Web-Interface ([docker-registry-ui](https://github.com/Joxit/docker-registry-ui))
- [`heartbeats.localhost`](https://heartbeats.localhost) Web-Interface for Gateway Heartbeats ([SEGuRo Gateway](https://github.com/SEGuRo-Projekt/Gateway))

```{note}
Please substitute `localhost` with the `DOMAIN` from your [configuration](./configuration.md).
```

## Certificate Authority

All connections to the SEGuRo Platform are TLS encrypted.
Server and client certificates are signed by a dedicated Certificate Authority (CA).

Please download, import and trust the <a href="/certs/ca.crt">Platform's CA certificate</a> in your operating systems certificate store.

## Default Credentials

The administrator credentials can be configured in the `.env` file.

The defaults are:

- **Username:** admin
- **Password:** s3gur0herne

## Accessing remotely

In case the platform is not deployed on the same host from which you attempt accessing it, further steps are necessary:

### For development: Patching `/etc/hosts`

Please add the following line to your `/etc/hosts` file and substitute the IP address with the one on which the Docker Compose stack is running:

```text
172.23.157.5 seguro ui.seguro store.seguro ui.store.seguro registry.seguro ui.registry.seguro
```

You then can access the links above by substituting `localhost` with `seguro`.

### Production

For production setup, you will need to register and configure a domain name (environment variable `DOMAIN` in `.env`) and point its `A` and `AAAA` records to the IP address of your Docker host.
