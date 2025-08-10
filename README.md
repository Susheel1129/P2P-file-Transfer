# P2P File Transfer with QUIC

A peer-to-peer file transfer system using QUIC (aioquic) with a web interface for dynamic peer registration and chunk-based file transfers.

## Prerequisites
- Python 3.8+
- OpenSSL (for generating certificates)
- Install dependencies: `pip install -r requirements.txt`

## Setup
1. Generate SSL certificates:
   ```bash
   mkdir certs
   openssl req -x509 -newkey rsa:2048 -nodes -days 365 -keyout certs/key.pem -out certs/cert.pem -subj "/CN=localhost"