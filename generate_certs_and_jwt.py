"""
Script to generate static JWT tokens and self-signed SSL certificates for local testing.

Usage:
    python generate_certs_and_jwt.py --jwt           # Generate JWT only
    python generate_certs_and_jwt.py --certs         # Generate self-signed certs only
    python generate_certs_and_jwt.py --jwt --certs   # Generate both

Options:
    --certs-dir DIR     Directory to store certs (default: ./certs)
    --certs-name NAME   Base name for cert files (default: server)
    --jwt               Generate static JWT token
    --certs             Generate self-signed certs

Environment variables for JWT:
    JWT_SECRET_KEY (default: 'your-secret-key')
    JWT_ALGORITHM (default: 'HS256')
    JWT_EXPIRE_DAYS (default: 365)

Example for HTTPS local testing:
    uvicorn app.main:app --host 0.0.0.0 --port 8443 --ssl-keyfile certs/server.key --ssl-certfile certs/server.crt
"""
import os
import argparse
from datetime import datetime, timedelta
from jose import jwt
from pathlib import Path
import subprocess

# JWT generation

def generate_jwt():
    secret = os.getenv("JWT_SECRET_KEY", "your-secret-key")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    expire_days = int(os.getenv("JWT_EXPIRE_DAYS", "365"))
    payload = {
        "api": "access",
        "exp": datetime.utcnow() + timedelta(days=expire_days)
    }
    token = jwt.encode(payload, secret, algorithm=algorithm)
    print("Your static JWT token:")
    print(token)

# Cert generation

def generate_certs(certs_dir, certs_name):
    certs_dir = Path(certs_dir)
    certs_dir.mkdir(parents=True, exist_ok=True)
    key_path = certs_dir / f"{certs_name}.key"
    crt_path = certs_dir / f"{certs_name}.crt"
    print(f"Generating self-signed certs in {certs_dir}...")
    cmd = [
        "openssl", "req", "-x509", "-nodes", "-days", "365",
        "-newkey", "rsa:2048",
        "-keyout", str(key_path),
        "-out", str(crt_path),
        "-subj", "/CN=localhost"
    ]
    subprocess.run(cmd, check=True)
    print(f"Certs generated: {key_path}, {crt_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate JWT and self-signed certs for local testing.")
    parser.add_argument("--jwt", action="store_true", help="Generate static JWT token")
    parser.add_argument("--certs", action="store_true", help="Generate self-signed certs")
    parser.add_argument("--certs-dir", default="./certs", help="Directory to store certs")
    parser.add_argument("--certs-name", default="server", help="Base name for cert files")
    args = parser.parse_args()

    if args.jwt:
        generate_jwt()
    if args.certs:
        generate_certs(args.certs_dir, args.certs_name)
    if not args.jwt and not args.certs:
        parser.print_help()
