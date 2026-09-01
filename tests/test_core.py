from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import Request

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from technocore_easy_setup.core import (
    IdentityError,
    LocalFileError,
    NetworkError,
    ProtocolError,
    contribution_message,
    contribution_payload,
    create_contribution_proof,
    create_identity,
    did_from_private_key,
    import_identity,
    load_identity,
    message_payload,
    normalize_message,
    post_signed_message,
    validate_https_url,
    validate_room,
    verify_contribution_proof,
    write_new_json,
)


PASSPHRASE = "correct horse battery staple"
COMMIT = "a" * 40


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, _limit: int) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_identity_is_encrypted_and_round_trips(tmp_path: Path) -> None:
    key_path = tmp_path / "private" / "identity.pem"
    did = create_identity(key_path, PASSPHRASE)
    data = key_path.read_bytes()
    assert data.startswith(b"-----BEGIN ENCRYPTED PRIVATE KEY-----")
    assert b"PRIVATE KEY-----\nMC" not in data
    assert did_from_private_key(load_identity(key_path, PASSPHRASE)) == did
    if os.name != "nt":
        assert key_path.stat().st_mode & 0o777 == 0o600


def test_identity_refuses_overwrite(tmp_path: Path) -> None:
    key_path = tmp_path / "identity.pem"
    original_did = create_identity(key_path, PASSPHRASE)
    original_bytes = key_path.read_bytes()
    with pytest.raises(IdentityError, match="overwrite"):
        create_identity(key_path, "another secure passphrase")
    assert key_path.read_bytes() == original_bytes
    assert did_from_private_key(load_identity(key_path, PASSPHRASE)) == original_did


def test_import_existing_starter_identity_without_changing_source(tmp_path: Path) -> None:
    source = tmp_path / "starter" / "identity.pem"
    destination = tmp_path / "app" / "identity.pem"
    expected_did = create_identity(source, PASSPHRASE)
    source_bytes = source.read_bytes()
    imported_did = import_identity(source, destination, PASSPHRASE)
    assert imported_did == expected_did
    assert destination.read_bytes() == source_bytes
    assert source.read_bytes() == source_bytes


def test_import_refuses_destination_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "source.pem"
    destination = tmp_path / "destination.pem"
    create_identity(source, PASSPHRASE)
    destination.write_text("keep me")
    with pytest.raises(IdentityError, match="overwrite"):
        import_identity(source, destination, PASSPHRASE)
    assert destination.read_text() == "keep me"


def test_identity_requires_long_passphrase(tmp_path: Path) -> None:
    with pytest.raises(IdentityError, match="12"):
        create_identity(tmp_path / "identity.pem", "short")


def test_wrong_passphrase_is_not_exposed(tmp_path: Path) -> None:
    key_path = tmp_path / "identity.pem"
    create_identity(key_path, PASSPHRASE)
    with pytest.raises(IdentityError, match="incorrect passphrase") as captured:
        load_identity(key_path, "this password is wrong")
    assert "this password is wrong" not in str(captured.value)


def test_did_has_canonical_ed25519_shape() -> None:
    did = did_from_private_key(Ed25519PrivateKey.generate())
    assert did.startswith("did:key:z6Mk")
    assert len(did.removeprefix("did:key:")) == 48


def test_normalize_message_matches_server_single_line_sweep() -> None:
    assert normalize_message("  hello\nworld\u200b!  ") == "hello world !"


@pytest.mark.parametrize("value", ["", " \n\t", "\u200b"])
def test_normalize_rejects_invisible_messages(value: str) -> None:
    with pytest.raises(ProtocolError):
        normalize_message(value)


def test_message_payload_is_exact() -> None:
    normalized, payload = message_payload("lobby", "123", " Hi\nthere ")
    assert normalized == "Hi there"
    assert payload == b"lobby|123|Hi there"


@pytest.mark.parametrize("room", ["Lobby", "two words", "../admin", "", "a" * 49])
def test_room_validation_rejects_unsafe_names(room: str) -> None:
    with pytest.raises(ProtocolError):
        validate_room(room)


@pytest.mark.parametrize(
    "url",
    ["http://example.com", "https://user:pass@example.com", "https://example.com/#secret", " https://example.com"],
)
def test_url_validation_rejects_unsafe_values(url: str) -> None:
    with pytest.raises(ProtocolError):
        validate_https_url(url)


def test_contribution_message_is_unambiguous() -> None:
    result = contribution_message("https://example.com/guide", "use Technocore safely")
    assert result == "I published a Technocore contribution: https://example.com/guide. It helps people use Technocore safely."


def test_contribution_payload_matches_starter_canonical_json() -> None:
    assert contribution_payload("https://example.com/repo", "A" * 40) == (
        b'{"artifact_url":"https://example.com/repo","commit":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","schema":"technocore-contribution-v1"}'
    )


def test_proof_verifies_and_tampering_fails() -> None:
    proof = create_contribution_proof(
        Ed25519PrivateKey.generate(), "https://example.com/repo", COMMIT
    )
    verify_contribution_proof(proof)
    proof["commit"] = "b" * 40
    with pytest.raises(IdentityError):
        verify_contribution_proof(proof)


def test_write_json_refuses_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "proof.json"
    write_new_json(output, {"public": True})
    with pytest.raises(LocalFileError, match="overwrite"):
        write_new_json(output, {"public": False})
    assert json.loads(output.read_text()) == {"public": True}


def test_post_sends_no_private_key_and_checks_receipt() -> None:
    private_key = Ed25519PrivateKey.generate()
    did = did_from_private_key(private_key)
    captured: dict[str, object] = {}

    def opener(request: Request, timeout: float) -> FakeResponse:
        assert timeout == 20.0
        body = json.loads(request.data.decode("utf-8"))  # type: ignore[union-attr]
        captured.update(body)
        posted = {
            "seq": 42,
            "from": did,
            "nonce": body["nonce"],
            "text": body["text"],
            "ts": "2026-08-31T00:00:00Z",
        }
        return FakeResponse(
            {"room": "lobby", "count": 1, "last_seq": 42, "posted": posted, "messages": [posted]}
        )

    result = post_signed_message(
        private_key, "lobby", "Hello", nonce="123456", opener=opener
    )
    assert result["posted"]["seq"] == 42
    assert set(captured) == {"did", "sig", "nonce", "text"}
    assert "private" not in json.dumps(captured).lower()
    assert captured["did"] == did


def test_post_rejects_mismatched_server_receipt() -> None:
    def opener(_request: Request, timeout: float) -> FakeResponse:
        assert timeout == 20.0
        posted = {"seq": 9, "from": "did:key:z6Mkwrong", "nonce": "123", "text": "Hello"}
        return FakeResponse(
            {"room": "lobby", "count": 1, "last_seq": 9, "posted": posted, "messages": [posted]}
        )

    with pytest.raises(NetworkError, match="does not match"):
        post_signed_message(
            Ed25519PrivateKey.generate(), "lobby", "Hello", nonce="123", opener=opener
        )


def test_mvp_refuses_alternate_server() -> None:
    with pytest.raises(ProtocolError, match="only connects"):
        post_signed_message(
            Ed25519PrivateKey.generate(),
            "lobby",
            "Hello",
            base_url="https://phishing.example",
        )
