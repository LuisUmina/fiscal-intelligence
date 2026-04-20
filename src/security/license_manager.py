import base64
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


@dataclass
class LicenseValidationResult:
    valid: bool
    message: str
    days_to_expiry: int | None = None
    payload: dict[str, Any] | None = None


def _canonical_payload_bytes(payload: dict[str, Any]) -> bytes:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return serialized.encode("utf-8")


def _load_public_key(public_key_path: Path) -> Ed25519PublicKey:
    key_bytes = public_key_path.read_bytes()
    key = serialization.load_pem_public_key(key_bytes)
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("Public key must be Ed25519")
    return key


def validate_license(license_path: Path, public_key_path: Path) -> LicenseValidationResult:
    if not public_key_path.exists():
        return LicenseValidationResult(
            valid=False,
            message=(
                "Public key not found. Expected file: "
                f"{public_key_path}. Contact administrator."
            ),
        )

    if not license_path.exists():
        return LicenseValidationResult(
            valid=False,
            message=(
                "License file not found. Expected file: "
                f"{license_path}. Contact administrator."
            ),
        )

    try:
        raw = json.loads(license_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return LicenseValidationResult(valid=False, message=f"Invalid license format: {exc}")

    payload = raw.get("payload")
    signature_b64 = raw.get("signature")
    if not isinstance(payload, dict) or not isinstance(signature_b64, str):
        return LicenseValidationResult(valid=False, message="License must contain payload and signature.")

    expires_at = str(payload.get("expires_at", "")).strip()
    if not expires_at:
        return LicenseValidationResult(valid=False, message="License payload is missing expires_at.")

    try:
        expiry_date = datetime.strptime(expires_at, "%Y-%m-%d").date()
    except ValueError:
        return LicenseValidationResult(
            valid=False,
            message="expires_at must use YYYY-MM-DD format.",
        )

    try:
        signature = base64.b64decode(signature_b64)
    except Exception:
        return LicenseValidationResult(valid=False, message="License signature is not valid base64.")

    try:
        pub = _load_public_key(public_key_path)
        pub.verify(signature, _canonical_payload_bytes(payload))
    except InvalidSignature:
        return LicenseValidationResult(
            valid=False,
            message="License signature is invalid. File may be altered.",
        )
    except Exception as exc:
        return LicenseValidationResult(valid=False, message=f"Failed to verify license: {exc}")

    days_to_expiry = (expiry_date - date.today()).days
    if days_to_expiry < 0:
        return LicenseValidationResult(
            valid=False,
            message=f"License expired on {expiry_date.isoformat()}.",
            days_to_expiry=days_to_expiry,
            payload=payload,
        )

    return LicenseValidationResult(
        valid=True,
        message="License is valid.",
        days_to_expiry=days_to_expiry,
        payload=payload,
    )
