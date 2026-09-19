from abc import ABC, abstractmethod
from pathlib import Path

from django.conf import settings
from django.utils.module_loading import import_string


class StorageProvider(ABC):
    @abstractmethod
    def save(self, key: str, content: bytes) -> None: ...

    @abstractmethod
    def open(self, key: str): ...

    @abstractmethod
    def delete(self, key: str) -> None: ...


class LocalPrivateStorage(StorageProvider):
    def __init__(self):
        self.root = Path(settings.PRIVATE_MEDIA_ROOT).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root not in path.parents:
            raise ValueError("Invalid private storage key.")
        return path

    def save(self, key: str, content: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f"{path.suffix}.uploading")
        temporary.write_bytes(content)
        temporary.replace(path)

    def open(self, key: str):
        return self._path(key).open("rb")

    def delete(self, key: str) -> None:
        path = self._path(key)
        path.unlink(missing_ok=True)


def get_storage_provider() -> StorageProvider:
    return import_string(settings.PRIVATE_FILE_STORAGE_BACKEND)()
