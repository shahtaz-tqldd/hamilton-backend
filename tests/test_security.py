from datetime import timedelta

from app.core.security import create_token, decode_token, hash_password, verify_password
from app.services.encryption import encryption_service


def test_password_round_trip() -> None:
    encoded = hash_password("correct-horse-battery-staple")
    assert verify_password("correct-horse-battery-staple", encoded)
    assert not verify_password("incorrect", encoded)


def test_access_token_round_trip() -> None:
    token = create_token("user-id", "access", timedelta(minutes=1))
    assert decode_token(token, "access")["sub"] == "user-id"


def test_encryption_round_trip() -> None:
    encrypted = encryption_service.encrypt("top-secret")
    assert encrypted != "top-secret"
    assert encryption_service.decrypt(encrypted) == "top-secret"
