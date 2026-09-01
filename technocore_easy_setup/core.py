"""Security-sensitive Technocore protocol and identity operations.

This is a focused GUI-oriented implementation compatible with
zunmax/technocore-did-starter v1.0.0 (commit
3cc03a6e908e8776de9fdd465c53d23d31db2e9f).
"""

from __future__ import annotations

import base64
import json
import math
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

APP_VERSION = "0.1.0"
DEFAULT_BASE_URL = "https://technocore.chat"
DEFAULT_TIMEOUT_SECONDS = 20.0
MAX_MESSAGE_CHARS = 4096
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
MAX_ERROR_RESPONSE_BYTES = 16 * 1024
MULTICODEC_ED25519 = b"\xed\x01"
MULTIBASE_LENGTH = 48
SIGNATURE_LENGTH = 86
BASE58BTC_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
INVISIBLE_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co", "Zl", "Zp"})
NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,47}")
NONCE_PATTERN = re.compile(r"[0-9]{1,19}")
SIGNATURE_PATTERN = re.compile(rf"[A-Za-z0-9_-]{{{SIGNATURE_LENGTH}}}")
COMMIT_PATTERN = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})")


class IdentityError(ValueError):
    """The local identity cannot be created, loaded, or verified."""


class ProtocolError(ValueError):
    """An input does not satisfy the published Technocore protocol."""


class NetworkError(RuntimeError):
    """A Technocore HTTP request failed or returned an invalid response."""


class LocalFileError(RuntimeError):
    """A local artifact could not be written safely."""


def base58btc_encode(data: bytes) -> str:
    zeroes = len(data) - len(data.lstrip(b"\x00"))
    number = int.from_bytes(data, "big")
    encoded = ""
    while number:
        number, remainder = divmod(number, 58)
        encoded = BASE58BTC_ALPHABET[remainder] + encoded
    return "1" * zeroes + encoded


def did_from_private_key(private_key: Ed25519PrivateKey) -> str:
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    multibase = "z" + base58btc_encode(MULTICODEC_ED25519 + public_key)
    if len(multibase) != MULTIBASE_LENGTH or not multibase.startswith("z6Mk"):
        raise IdentityError("generated an invalid Ed25519 did:key")
    return "did:key:" + multibase


def _public_key_from_did(did: str) -> Ed25519PublicKey:
    if not isinstance(did, str) or not did.startswith("did:key:z6Mk"):
        raise ProtocolError("DID must start with did:key:z6Mk")
    multibase = did.removeprefix("did:key:")
    if len(multibase) != MULTIBASE_LENGTH:
        raise ProtocolError("DID has an invalid length")
    number = 0
    try:
        for character in multibase[1:]:
            number = number * 58 + BASE58BTC_ALPHABET.index(character)
    except ValueError as error:
        raise ProtocolError("DID contains invalid base58btc data") from error
    decoded = number.to_bytes((number.bit_length() + 7) // 8, "big")
    if len(decoded) != 34 or not decoded.startswith(MULTICODEC_ED25519):
        raise ProtocolError("DID does not contain an Ed25519 public key")
    return Ed25519PublicKey.from_public_bytes(decoded[2:])


def normalize_message(text: str) -> str:
    if not isinstance(text, str):
        raise ProtocolError("message text must be a string")
    normalized = "".join(
        " " if unicodedata.category(character) in INVISIBLE_CATEGORIES else character
        for character in text
    ).strip()
    if not normalized:
        raise ProtocolError("message has no visible text after normalization")
    if len(normalized) > MAX_MESSAGE_CHARS:
        raise ProtocolError(f"message exceeds {MAX_MESSAGE_CHARS} characters")
    return normalized


def validate_room(room: str) -> str:
    if not isinstance(room, str) or NAME_PATTERN.fullmatch(room) is None:
        raise ProtocolError("room must match ^[a-z0-9][a-z0-9_-]{0,47}$")
    return room


def validate_nonce(value: str | int) -> str:
    nonce = str(value)
    if NONCE_PATTERN.fullmatch(nonce) is None:
        raise ProtocolError("nonce must contain 1-19 ASCII digits")
    return nonce


def validate_https_url(value: str) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise ProtocolError("URL must not contain surrounding whitespace")
    try:
        parsed = urlsplit(value)
        _port = parsed.port
    except ValueError as error:
        raise ProtocolError("URL is malformed") from error
    if parsed.scheme != "https" or not parsed.netloc or parsed.fragment:
        raise ProtocolError("URL must be an absolute HTTPS URL without a fragment")
    if parsed.username is not None or parsed.password is not None:
        raise ProtocolError("URL must not contain embedded credentials")
    return value


def create_identity(path: Path, passphrase: str) -> str:
    resolved = path.expanduser().resolve()
    if resolved.exists():
        raise IdentityError(f"refusing to overwrite existing identity: {resolved}")
    if not isinstance(passphrase, str) or len(passphrase) < 12:
        raise IdentityError("passphrase must contain at least 12 characters")
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(passphrase.encode("utf-8")),
    )
    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(resolved, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as output:
            output.write(private_bytes)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(resolved, 0o600)
    except FileExistsError as error:
        raise IdentityError(f"refusing to overwrite existing identity: {resolved}") from error
    except OSError as error:
        try:
            resolved.unlink(missing_ok=True)
        except OSError:
            pass
        raise IdentityError(f"cannot write encrypted identity: {error}") from error
    return did_from_private_key(private_key)


def load_identity(path: Path, passphrase: str) -> Ed25519PrivateKey:
    resolved = path.expanduser().resolve()
    try:
        private_bytes = resolved.read_bytes()
    except OSError as error:
        raise IdentityError(f"cannot read identity: {resolved}") from error
    try:
        loaded = serialization.load_pem_private_key(
            private_bytes, password=passphrase.encode("utf-8")
        )
    except UnsupportedAlgorithm as error:
        raise IdentityError("identity uses unsupported encryption") from error
    except (ValueError, TypeError) as error:
        raise IdentityError("incorrect passphrase or invalid encrypted identity") from error
    if not isinstance(loaded, Ed25519PrivateKey):
        raise IdentityError("identity must contain an Ed25519 private key")
    return loaded


def import_identity(source: Path, destination: Path, passphrase: str) -> str:
    """Validate and locally copy an existing encrypted starter identity."""
    source_resolved = source.expanduser().resolve()
    destination_resolved = destination.expanduser().resolve()
    if destination_resolved.exists():
        raise IdentityError(
            f"refusing to overwrite existing identity: {destination_resolved}"
        )
    if source_resolved == destination_resolved:
        raise IdentityError("source identity is already in the application location")
    private_key = load_identity(source_resolved, passphrase)
    try:
        private_bytes = source_resolved.read_bytes()
        destination_resolved.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            destination_resolved, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
        with os.fdopen(descriptor, "wb") as output:
            output.write(private_bytes)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(destination_resolved, 0o600)
    except FileExistsError as error:
        raise IdentityError(
            f"refusing to overwrite existing identity: {destination_resolved}"
        ) from error
    except OSError as error:
        try:
            destination_resolved.unlink(missing_ok=True)
        except OSError:
            pass
        raise IdentityError(f"cannot import encrypted identity: {error}") from error
    return did_from_private_key(private_key)


def _signature(private_key: Ed25519PrivateKey, payload: bytes) -> str:
    encoded = base64.urlsafe_b64encode(private_key.sign(payload)).decode("ascii").rstrip("=")
    if SIGNATURE_PATTERN.fullmatch(encoded) is None:
        raise IdentityError("generated an invalid signature")
    return encoded


def message_payload(room: str, nonce: str | int, text: str) -> tuple[str, bytes]:
    valid_room = validate_room(room)
    valid_nonce = validate_nonce(nonce)
    normalized = normalize_message(text)
    return normalized, f"{valid_room}|{valid_nonce}|{normalized}".encode("utf-8")


def _safe_error_detail(value: Any) -> str:
    return "".join(
        " " if unicodedata.category(character) in INVISIBLE_CATEGORIES else character
        for character in str(value)
    ).strip()


def _read_response(response: Any, *, expected_room: str, expected: dict[str, Any]) -> dict[str, Any]:
    raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise NetworkError("Technocore response exceeded the safety limit")
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise NetworkError("Technocore returned an invalid JSON response") from error
    if not isinstance(body, dict) or body.get("room") != expected_room:
        raise NetworkError("Technocore returned data for a different room")
    count = body.get("count")
    last_seq = body.get("last_seq")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise NetworkError("Technocore returned an invalid message count")
    if isinstance(last_seq, bool) or not isinstance(last_seq, int) or last_seq < 0:
        raise NetworkError("Technocore returned an invalid sequence cursor")
    messages = body.get("messages")
    if not isinstance(messages, list):
        raise NetworkError("Technocore returned an invalid messages list")
    posted = body.get("posted")
    if not isinstance(posted, dict):
        raise NetworkError("Technocore did not return a posted record")
    posted_seq = posted.get("seq")
    try:
        nonce_matches = int(posted.get("nonce")) == int(expected["nonce"])
    except (TypeError, ValueError):
        nonce_matches = False
    if not (
        posted.get("from") == expected["did"]
        and posted.get("text") == expected["text"]
        and nonce_matches
        and isinstance(posted_seq, int)
        and not isinstance(posted_seq, bool)
        and posted_seq > 0
        and any(isinstance(item, dict) and item.get("seq") == posted_seq for item in messages)
    ):
        raise NetworkError("Technocore response does not match the signed request")
    return body


def post_signed_message(
    private_key: Ed25519PrivateKey,
    room: str,
    text: str,
    *,
    nonce: str | int | None = None,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    if not math.isfinite(timeout) or timeout <= 0:
        raise ProtocolError("timeout must be a positive finite number")
    if base_url != DEFAULT_BASE_URL:
        raise ProtocolError("this MVP only connects to https://technocore.chat")
    selected_nonce = validate_nonce(nonce if nonce is not None else time.time_ns())
    normalized, payload = message_payload(room, selected_nonce, text)
    did = did_from_private_key(private_key)
    request_data = {
        "did": did,
        "sig": _signature(private_key, payload),
        "nonce": selected_nonce,
        "text": normalized,
    }
    request = Request(
        f"{base_url}/r/{validate_room(room)}?format=json",
        data=json.dumps(request_data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": f"technocore-easy-setup/{APP_VERSION}",
        },
    )
    try:
        with opener(request, timeout=timeout) as response:
            return _read_response(response, expected_room=room, expected=request_data)
    except HTTPError as error:
        detail = _safe_error_detail(error.read(MAX_ERROR_RESPONSE_BYTES).decode("utf-8", "replace"))
        raise NetworkError(f"Technocore returned HTTP {error.code}: {detail or error.reason}") from None
    except (TimeoutError, URLError) as error:
        raise NetworkError(
            "Technocore write timed out or could not be confirmed. Check the room before retrying."
        ) from error
    except OSError as error:
        raise NetworkError(f"Technocore request failed: {_safe_error_detail(error)}") from error


def contribution_message(artifact_url: str, description: str) -> str:
    url = validate_https_url(artifact_url)
    detail = normalize_message(description).rstrip(".")
    return normalize_message(
        f"I published a Technocore contribution: {url}. It helps people {detail}."
    )


def contribution_payload(artifact_url: str, commit: str) -> bytes:
    url = validate_https_url(artifact_url)
    if not isinstance(commit, str) or COMMIT_PATTERN.fullmatch(commit) is None:
        raise ProtocolError("commit must be a complete 40- or 64-character hexadecimal revision")
    record = {
        "artifact_url": url,
        "commit": commit.lower(),
        "schema": "technocore-contribution-v1",
    }
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def create_contribution_proof(
    private_key: Ed25519PrivateKey, artifact_url: str, commit: str
) -> dict[str, str]:
    payload = contribution_payload(artifact_url, commit)
    return {
        "schema": "technocore-contribution-proof-v1",
        "did": did_from_private_key(private_key),
        "artifact_url": artifact_url,
        "commit": commit.lower(),
        "signature": _signature(private_key, payload),
    }


def verify_contribution_proof(proof: dict[str, Any]) -> None:
    if proof.get("schema") != "technocore-contribution-proof-v1":
        raise ProtocolError("unsupported contribution proof schema")
    required = ("did", "artifact_url", "commit", "signature")
    if any(not isinstance(proof.get(field), str) for field in required):
        raise ProtocolError("proof is missing required fields")
    payload = contribution_payload(proof["artifact_url"], proof["commit"])
    signature = proof["signature"]
    if SIGNATURE_PATTERN.fullmatch(signature) is None:
        raise ProtocolError("proof signature has an invalid format")
    try:
        _public_key_from_did(proof["did"]).verify(
            base64.urlsafe_b64decode(signature + "=="), payload
        )
    except InvalidSignature as error:
        raise IdentityError("proof signature does not match the DID") from error


def write_new_json(path: Path, payload: dict[str, Any]) -> None:
    resolved = path.expanduser().resolve()
    serialized = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        descriptor = os.open(resolved, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(descriptor, "wb") as output:
            output.write(serialized)
            output.flush()
            os.fsync(output.fileno())
    except FileExistsError as error:
        raise LocalFileError(f"refusing to overwrite existing file: {resolved}") from error
    except OSError as error:
        try:
            resolved.unlink(missing_ok=True)
        except OSError:
            pass
        raise LocalFileError(f"cannot write proof file: {error}") from error
