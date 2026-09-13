from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class EncryptionService:
    def __init__(self) -> None:
        try:
            self._fernet = Fernet(settings.fernet_key.encode())
        except (ValueError, TypeError) as exc:
            raise RuntimeError("FERNET_KEY must be a valid url-safe base64 Fernet key") from exc

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, encrypted_value: str) -> str:
        try:
            return self._fernet.decrypt(encrypted_value.encode()).decode()
        except InvalidToken as exc:
            raise RuntimeError("Unable to decrypt stored value") from exc


encryption_service = EncryptionService()
