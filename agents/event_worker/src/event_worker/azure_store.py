"""Azure Blob Storage result store. One blob per event gives cheap, race-free idempotency."""

from __future__ import annotations

import contextlib
from typing import Any

from event_worker.settings import WorkerSettings


class BlobResultStore:
    def __init__(self, settings: WorkerSettings) -> None:
        self._settings = settings
        self._service: Any = None
        self._container: Any = None
        self._credential: Any = None

    async def start(self) -> None:
        from azure.storage.blob.aio import BlobServiceClient

        s = self._settings
        if s.blob_connection_string is not None:  # local Azurite or key-based access
            self._service = BlobServiceClient.from_connection_string(
                s.blob_connection_string.get_secret_value()
            )
        elif s.blob_account_url:  # production: managed identity / workload identity
            from azure.identity.aio import DefaultAzureCredential

            self._credential = DefaultAzureCredential()
            self._service = BlobServiceClient(s.blob_account_url, credential=self._credential)
        else:
            raise ValueError("set EVENTS_BLOB_ACCOUNT_URL or EVENTS_BLOB_CONNECTION_STRING")
        self._container = self._service.get_container_client(s.blob_container)
        from azure.core.exceptions import ResourceExistsError

        with contextlib.suppress(ResourceExistsError):
            await self._container.create_container()

    async def stop(self) -> None:
        if self._service is not None:
            await self._service.close()
        if self._credential is not None:
            await self._credential.close()

    async def put_if_absent(self, name: str, value: bytes) -> bool:
        from azure.core.exceptions import ResourceExistsError

        try:
            await self._container.upload_blob(name, value, overwrite=False)
        except ResourceExistsError:
            return False
        return True

    async def get(self, name: str) -> bytes | None:
        from azure.core.exceptions import ResourceNotFoundError

        try:
            stream = await self._container.download_blob(name)
        except ResourceNotFoundError:
            return None
        return bytes(await stream.readall())
