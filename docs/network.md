# Calcolatrice algebraica ESP32 + Raspberry Pi

## Obiettivo

Comunicazione Internet tra ESP32 e Raspberry Pi:

- lunga distanza
- gratuita
- senza Tailscale
- abbastanza sicura
- usando JSON

---

# Architettura finale

```text
ESP32
   |
 HTTPS
   |
Caddy Server :443
   |
reverse proxy
   |
FastAPI (localhost:8000)
   |
SymPy / motore algebra
```

---

# Componenti

## ESP32

Gestisce:

- tastiera
- display
- input utente
- invio richieste
- ricezione risultati

Tecnologie:

- WiFi
- HTTPS
- JSON

---

## Raspberry Pi

Gestisce:

- algebra simbolica
- calcoli
- API

Tecnologie:

- FastAPI
- Uvicorn
- SymPy

---

## Caddy Server

Serve per:

- HTTPS automatico
- certificati TLS
- reverse proxy
- sicurezza base

Espone SOLO la porta 443.

FastAPI NON è esposto direttamente.

---

# Sicurezza

## HTTPS/TLS

Protegge da:

- sniffing
- intercettazione traffico
- MITM (man-in-the-middle)
- modifica pacchetti

---

## Bearer Token

Header HTTP:

```http
Authorization: Bearer TOKEN_RANDOM_LUNGO
```

Protegge da:

- richieste non autorizzate
- scanner casuali

---

## FastAPI solo locale

FastAPI ascolta SOLO:

```text
127.0.0.1:8000
```

NON:

```text
0.0.0.0:8000
```

Così Internet vede solo Caddy.

---

## Firewall

Aprire solo:

```text
443/tcp
```

Bloccare tutto il resto.

---

# Esempio richiesta

## ESP32 -> Raspberry

POST `/solve`

```json
{
  "expr": "integrate(x^2)"
}
```

---

## Risposta

```json
{
  "ok": true,
  "result": "x^3/3"
}
```

---

# Cosa evitare

NON usare:

- HTTP senza TLS
- socket raw
- eval()
- exec()
- parser homemade pericolosi
- token corti
- porte aperte inutili

---

# DNS dinamico

Se l’IP di casa cambia:

Usare DuckDNS.

Esempio:

```text
mio-server.duckdns.org
```

---

# Librerie utili

## ESP32

- WiFiClientSecure
- ArduinoJson

---

## Raspberry Pi

- FastAPI
- Uvicorn
- SymPy

---

# Avvio FastAPI

```bash
uvicorn app:app --host 127.0.0.1 --port 8000
```

---

# Configurazione base Caddy

Caddyfile:

```text
miodominio.duckdns.org {

    reverse_proxy 127.0.0.1:8000

}
```

---

# Sicurezza reale

Questa architettura è:

- molto migliore di una porta TCP aperta
- molto migliore di HTTP semplice
- abbastanza sicura per un progetto personale

La sicurezza dipende soprattutto da:

- qualità del codice
- aggiornamenti sistema
- gestione token
- parser matematico
- timeout richieste