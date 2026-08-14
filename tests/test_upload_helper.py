from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile

from backend.app.api.routes.documents import _read_optional_upload


@pytest.mark.asyncio
async def test_read_optional_upload_none() -> None:
    content, filename, content_type = await _read_optional_upload(None)
    assert content is None
    assert filename is None
    assert content_type is None


@pytest.mark.asyncio
async def test_read_optional_upload_empty_swagger_part() -> None:
    upload = UploadFile(filename="", file=BytesIO(b""))
    content, filename, content_type = await _read_optional_upload(upload)
    assert content is None
    assert filename is None


@pytest.mark.asyncio
async def test_read_optional_upload_named_empty_file_errors() -> None:
    upload = UploadFile(filename="empty.txt", file=BytesIO(b""))
    with pytest.raises(HTTPException) as exc:
        await _read_optional_upload(upload)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_read_optional_upload_bytes() -> None:
    upload = UploadFile(filename="notes.txt", file=BytesIO(b"hello"), headers={"content-type": "text/plain"})
    content, filename, content_type = await _read_optional_upload(upload)
    assert content == b"hello"
    assert filename == "notes.txt"
