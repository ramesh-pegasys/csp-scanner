"""
Interactive script to generate static JWT tokens and self-signed SSL certificates for local testing.

Usage:
    python utils/generate_certs_and_jwt.py
    # Or use command-line options as before

Options:
    --jwt               Generate static JWT token
    --certs             Generate self-signed certs
    --certs-dir DIR     Directory to store certs (default: ./certs)
    --certs-name NAME   Base name for cert files (default: server)

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


def generate_jwt_interactive():
    print("\n--- JWT Generation ---")
    secret = input(
        f"JWT Secret Key [{os.getenv('JWT_SECRET_KEY', 'your-secret-key')}]: "
    ) or os.getenv("JWT_SECRET_KEY", "your-secret-key")
    algorithm = input(
        f"JWT Algorithm [{os.getenv('JWT_ALGORITHM', 'HS256')}]: "
    ) or os.getenv("JWT_ALGORITHM", "HS256")
    expire_days = input(
        f"JWT Expire Days [{os.getenv('JWT_EXPIRE_DAYS', '365')}]: "
    ) or os.getenv("JWT_EXPIRE_DAYS", "365")
    try:
        expire_days = int(expire_days)
    except ValueError:
        expire_days = 365
    payload = {"api": "access", "exp": datetime.utcnow() + timedelta(days=expire_days)}
    token = jwt.encode(payload, secret, algorithm=algorithm)
    print("\nYour static JWT token:")
    print(token)
    print()


def generate_certs_interactive():
    print("\n--- Self-Signed Certificate Generation ---")
    certs_dir = input("Certs directory [./certs]: ") or "./certs"
    certs_name = input("Certs base name [server]: ") or "server"
    certs_dir = Path(certs_dir)
    certs_dir.mkdir(parents=True, exist_ok=True)
    key_path = certs_dir / f"{certs_name}.key"
    crt_path = certs_dir / f"{certs_name}.crt"
    print(f"Generating self-signed certs in {certs_dir}...")
    cmd = [
        "openssl",
        "req",
        "-x509",
        "-nodes",
        "-days",
        "365",
        "-newkey",
        "rsa:2048",
        "-keyout",
        str(key_path),
        "-out",
        str(crt_path),
        "-subj",
        "/CN=localhost",
    ]
    subprocess.run(cmd, check=True)
    print(f"Certs generated: {key_path}, {crt_path}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Generate JWT and self-signed certs for local testing."
    )
    parser.add_argument("--jwt", action="store_true", help="Generate static JWT token")
    parser.add_argument(
        "--certs", action="store_true", help="Generate self-signed certs"
    )
    parser.add_argument(
        "--certs-dir", default="./certs", help="Directory to store certs"
    )
    parser.add_argument(
        "--certs-name", default="server", help="Base name for cert files"
    )
    args = parser.parse_args()

    if not args.jwt and not args.certs:
        print("Welcome to the JWT & Cert Generator!")
        print("Select what you want to generate:")
        print("1. JWT Token")
        print("2. Self-Signed Certs")
        print("3. Both")
        print("0. Exit")
        choice = input("Enter choice [1/2/3/0]: ").strip()
        if choice == "1":
            generate_jwt_interactive()
        elif choice == "2":
            generate_certs_interactive()
        elif choice == "3":
            generate_jwt_interactive()
            generate_certs_interactive()
        else:
            print("Exiting.")
            return
    else:
        if args.jwt:
            generate_jwt_interactive()
        if args.certs:
            # Use CLI args for certs if provided
            certs_dir = args.certs_dir
            certs_name = args.certs_name
            certs_dir = Path(certs_dir)
            certs_dir.mkdir(parents=True, exist_ok=True)
            key_path = certs_dir / f"{certs_name}.key"
            crt_path = certs_dir / f"{certs_name}.crt"
            print(f"Generating self-signed certs in {certs_dir}...")
            cmd = [
                "openssl",
                "req",
                "-x509",
                "-nodes",
                "-days",
                "365",
                "-newkey",
                "rsa:2048",
                "-keyout",
                str(key_path),
                "-out",
                str(crt_path),
                "-subj",
                "/CN=localhost",
            ]
            subprocess.run(cmd, check=True)
            print(f"Certs generated: {key_path}, {crt_path}\n")


if __name__ == "__main__":
    main()
