# Caddy Configuration

Caddy può eseguire un reverse proxy HTTPS verso l`API del Raspberry Pi.

## Caddyfile esempio

```
mio-dominio.duckdns.org {
    reverse_proxy 127.0.0.1:8000
}
```

## Note
- Esporre solo `443/tcp` verso l`esterno.
- FastAPI rimane in ascolto su `127.0.0.1:8000`.
- Usare DNS dinamico come DuckDNS se l`IP cambia.
