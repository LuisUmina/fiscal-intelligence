import argparse
import base64
import json
from datetime import date
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_PRIVATE_KEY_PATH = SCRIPT_DIR / "license_keys" / "private_key.pem"
DEFAULT_PUBLIC_KEY_PATH = SCRIPT_DIR / "license_public_key.pem"
DEFAULT_LICENSE_PATH = SCRIPT_DIR / "license.json"


def _canonical_payload_bytes(payload: dict[str, Any]) -> bytes:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return serialized.encode("utf-8")


def init_keys(private_key_path: Path, public_key_path: Path, overwrite: bool = False) -> bool:
    private_key_path.parent.mkdir(parents=True, exist_ok=True)
    public_key_path.parent.mkdir(parents=True, exist_ok=True)

    if private_key_path.exists() or public_key_path.exists():
        if not overwrite:
            print("[OK] Key files already exist. Skipping generation.")
            print(f"[OK] Private key: {private_key_path}")
            print(f"[OK] Public key:  {public_key_path}")
            return False
        if private_key_path.exists():
            private_key_path.unlink()
        if public_key_path.exists():
            public_key_path.unlink()

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_key_path.write_bytes(private_bytes)
    public_key_path.write_bytes(public_bytes)
    return True


def issue_license(
    private_key_path: Path,
    output_path: Path,
    company: str,
    expires_at: str,
    user: str = "",
) -> None:
    key = serialization.load_pem_private_key(private_key_path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Private key must be Ed25519")

    payload: dict[str, Any] = {
        "company": company,
        "expires_at": expires_at,
        "issued_at": date.today().isoformat(),
    }
    if user:
        payload["user"] = user

    signature = key.sign(_canonical_payload_bytes(payload))
    license_data = {
        "payload": payload,
        "signature": base64.b64encode(signature).decode("utf-8"),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(license_data, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and renew app licenses")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_init = subparsers.add_parser("init-keys", help="Create Ed25519 key pair")
    p_init.add_argument("--private-key", default=None, help="Path for private key PEM")
    p_init.add_argument("--public-key", default=None, help="Path for public key PEM")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing key files")

    p_issue = subparsers.add_parser("issue", help="Issue or renew license JSON")
    p_issue.add_argument("--private-key", default=None, help="Path to private key PEM")
    p_issue.add_argument("--company", required=True, help="Company name")
    p_issue.add_argument("--user", default="", help="Optional user name")
    p_issue.add_argument("--expires-at", required=True, help="Expiration date in YYYY-MM-DD")
    p_issue.add_argument("--output", default=None, help="Output path for license JSON")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    default_private_key = DEFAULT_PRIVATE_KEY_PATH
    default_public_key = DEFAULT_PUBLIC_KEY_PATH
    default_license = DEFAULT_LICENSE_PATH

    if args.command == "init-keys":
        private_key_path = Path(args.private_key) if args.private_key else default_private_key
        public_key_path = Path(args.public_key) if args.public_key else default_public_key
        created = init_keys(private_key_path, public_key_path, overwrite=args.force)
        if created:
            print(f"[OK] Private key: {private_key_path}")
            print(f"[OK] Public key:  {public_key_path}")
        return

    if args.command == "issue":
        private_key_path = Path(args.private_key) if args.private_key else default_private_key
        output_path = Path(args.output) if args.output else default_license
        issue_license(
            private_key_path=private_key_path,
            output_path=output_path,
            company=args.company,
            user=args.user,
            expires_at=args.expires_at,
        )
        print(f"[OK] License file written to: {output_path}")


if __name__ == "__main__":
    main()
