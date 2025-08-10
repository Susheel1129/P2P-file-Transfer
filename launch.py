import subprocess
import sys
import time
import os

def create_certificates():
    """Create self-signed certificates if they don't exist"""
    certs_dir = "certs"
    if not os.path.exists(certs_dir):
        os.makedirs(certs_dir)
    
    cert_file = os.path.join(certs_dir, "cert.pem")
    key_file = os.path.join(certs_dir, "key.pem")
    
    if not (os.path.exists(cert_file) and os.path.exists(key_file)):
        print("Generating self-signed certificates...")
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:4096", "-keyout", key_file,
            "-out", cert_file, "-days", "365", "-nodes", "-subj", "/CN=localhost"
        ])
        print("Certificates generated successfully.")

def main(peer_port=None):
    if not peer_port and len(sys.argv) < 2:
        print("Usage: python launch.py <peer_port> or call with peer_port argument")
        sys.exit(1)
    
    peer_port = peer_port or int(sys.argv[1])
    http_port = peer_port + 1
    
    create_certificates()
    
    print(f"Starting HTTP server on port {http_port}...")
    http_server = subprocess.Popen([sys.executable, "http_server.py", str(http_port)])
    time.sleep(1)
    
    print(f"Starting peer on port {peer_port}...")
    peer = subprocess.Popen([sys.executable, "peer.py", str(peer_port)])
    
    try:
        print(f"\nHTTP server and peer running on ports {http_port} and {peer_port}. Press Ctrl+C to stop.")
        processes = {"http_server": http_server, "peer": peer}
        http_server.wait()
        peer.wait()
    except KeyboardInterrupt:
        print("\nShutting down processes...")
        http_server.terminate()
        peer.terminate()
        http_server.wait()
        peer.wait()
        print("All processes have been terminated.")

if __name__ == "__main__":
    main()