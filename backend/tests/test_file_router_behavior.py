"""File-router and OpenAI-file boundary tests with real payload assertions."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, UploadFile

from src import file_extraction, openai_files, storage, vector_store
from src.routers import files as router


def _db_file(**overrides):
    values = {
        "id": 4,
        "user_id": 2,
        "organization_id": 3,
        "filename": "stored.txt",
        "original_filename": "report.txt",
        "content_type": "text/plain",
        "file_size": 7,
        "file_path": "/tmp/stored.txt",
        "created_at": datetime(2026, 1, 1),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.asyncio
async def test_upload_validates_access_persists_and_indexes(monkeypatch):
    db = object()
    db_file = _db_file()
    monkeypatch.setattr(router.crud, "get_user", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(router.crud, "get_organization", lambda *_args, **_kwargs: object())
    permission = MagicMock(return_value=True)
    create = MagicMock(return_value=db_file)
    monkeypatch.setattr(router.crud, "check_org_permission", permission)
    monkeypatch.setattr(router.crud, "create_file", create)
    monkeypatch.setattr(storage, "validate_file_type", lambda *_args: (True, None))
    monkeypatch.setattr(
        file_extraction,
        "extract_text_from_file",
        lambda *_args: ("indexed text", None),
    )
    add = MagicMock()
    monkeypatch.setattr(vector_store, "add_document_to_store", add)
    upload = UploadFile(
        filename="report.txt",
        file=BytesIO(b"payload"),
        headers={"content-type": "text/plain"},
    )

    response = await router.upload_file(upload, user_id=2, organization_id=3, db=db)

    permission.assert_called_once_with(db, 3, 2, require_write=True)
    create.assert_called_once_with(
        db=db,
        user_id=2,
        organization_id=3,
        original_filename="report.txt",
        file_content=b"payload",
        content_type="text/plain",
    )
    add.assert_called_once_with(
        organization_id=3,
        file_id=4,
        filename="report.txt",
        text_content="indexed text",
    )
    assert response.id == 4
    assert response.original_filename == "report.txt"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("user", "organization", "permission", "status_code"),
    [
        (None, object(), True, 404),
        (object(), None, True, 404),
        (object(), object(), False, 403),
    ],
)
async def test_upload_rejects_missing_user_org_or_permission(
    monkeypatch,
    user,
    organization,
    permission,
    status_code,
):
    monkeypatch.setattr(router.crud, "get_user", lambda *_args, **_kwargs: user)
    monkeypatch.setattr(
        router.crud,
        "get_organization",
        lambda *_args, **_kwargs: organization,
    )
    monkeypatch.setattr(
        router.crud,
        "check_org_permission",
        lambda *_args, **_kwargs: permission,
    )
    upload = UploadFile(filename="report.txt", file=BytesIO(b"payload"))
    with pytest.raises(HTTPException) as exc:
        await router.upload_file(upload, user_id=2, organization_id=3, db=object())
    assert exc.value.status_code == status_code


@pytest.mark.asyncio
async def test_upload_rejects_invalid_type_and_tolerates_index_failure(monkeypatch):
    monkeypatch.setattr(router.crud, "get_user", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(router.crud, "get_organization", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(router.crud, "check_org_permission", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(storage, "validate_file_type", lambda *_args: (False, "blocked"))
    with pytest.raises(HTTPException) as exc:
        await router.upload_file(
            UploadFile(filename="malware.exe", file=BytesIO(b"x")),
            user_id=2,
            organization_id=3,
            db=object(),
        )
    assert exc.value.status_code == 400
    assert exc.value.detail == "blocked"

    monkeypatch.setattr(storage, "validate_file_type", lambda *_args: (True, None))
    monkeypatch.setattr(router.crud, "create_file", lambda **_kwargs: _db_file())
    monkeypatch.setattr(
        file_extraction,
        "extract_text_from_file",
        lambda *_args: ("text", None),
    )
    monkeypatch.setattr(
        vector_store,
        "add_document_to_store",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("vector down")),
    )
    response = await router.upload_file(
        UploadFile(filename="report.txt", file=BytesIO(b"x")),
        user_id=2,
        organization_id=3,
        db=object(),
    )
    assert response.id == 4


@pytest.mark.asyncio
async def test_file_info_owner_member_and_denied(monkeypatch):
    db_file = _db_file()
    monkeypatch.setattr(router.crud, "get_file", lambda *_args, **_kwargs: db_file)
    response = await router.get_file_info(4, user_id=2, db=object())
    assert response.id == 4

    db_file.user_id = 99
    monkeypatch.setattr(router.crud, "check_org_permission", lambda *_args, **_kwargs: True)
    assert (await router.get_file_info(4, user_id=2, db=object())).id == 4

    monkeypatch.setattr(router.crud, "check_org_permission", lambda *_args, **_kwargs: False)
    with pytest.raises(HTTPException) as exc:
        await router.get_file_info(4, user_id=2, db=object())
    assert exc.value.status_code == 403

    monkeypatch.setattr(router.crud, "get_file", lambda *_args, **_kwargs: None)
    with pytest.raises(HTTPException) as exc:
        await router.get_file_info(4, user_id=2, db=object())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_download_checks_access_and_storage(monkeypatch, tmp_path):
    path = tmp_path / "report.txt"
    path.write_text("payload")
    db_file = _db_file(file_path=str(path))
    monkeypatch.setattr(router.crud, "get_file", lambda *_args, **_kwargs: db_file)
    monkeypatch.setattr(storage, "file_exists", lambda _path: True)

    response = await router.download_file(4, user_id=2, db=object())
    assert response.path == str(path)
    assert response.filename == "report.txt"

    monkeypatch.setattr(storage, "file_exists", lambda _path: False)
    with pytest.raises(HTTPException) as exc:
        await router.download_file(4, user_id=2, db=object())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_and_delete_files(monkeypatch):
    files = [_db_file(id=1), _db_file(id=2)]
    get_files = MagicMock(return_value=files)
    monkeypatch.setattr(router.crud, "get_files_by_user", get_files)
    response = await router.get_files(
        user_id=2,
        organization_id=3,
        skip=4,
        limit=5,
        db=object(),
    )
    assert [item.id for item in response] == [1, 2]
    get_files.assert_called_once_with(
        get_files.call_args.args[0],
        user_id=2,
        organization_id=3,
        skip=4,
        limit=5,
    )

    monkeypatch.setattr(router.crud, "delete_file", lambda *_args, **_kwargs: True)
    assert await router.delete_file_endpoint(1, user_id=2, db=object()) is None
    monkeypatch.setattr(router.crud, "delete_file", lambda *_args, **_kwargs: False)
    with pytest.raises(HTTPException) as exc:
        await router.delete_file_endpoint(1, user_id=2, db=object())
    assert exc.value.status_code == 404


def test_openai_file_upload_attachment_batch_and_cleanup(monkeypatch):
    client = MagicMock()
    client.files.create.return_value = SimpleNamespace(id="file-1")

    file_id = openai_files.upload_file_to_openai(client, b"payload", "report.pdf")
    assert file_id == "file-1"
    uploaded = client.files.create.call_args.kwargs["file"]
    assert uploaded.read() == b"payload"
    assert uploaded.name == "report.pdf"
    assert openai_files.create_file_attachment("file-1", "report.pdf") == {
        "type": "file",
        "file_id": "file-1",
        "name": "report.pdf",
    }

    db_files = [
        SimpleNamespace(file_path="/one", original_filename="one.txt"),
        SimpleNamespace(file_path="/bad", original_filename="bad.txt"),
    ]
    monkeypatch.setattr(storage, "get_file", lambda path: b"one" if path == "/one" else b"bad")
    upload = MagicMock(side_effect=["file-one", RuntimeError("upload failed")])
    monkeypatch.setattr(openai_files, "upload_file_to_openai", upload)
    assert openai_files.upload_files_to_openai(client, db_files) == [
        {"file_id": "file-one", "filename": "one.txt"}
    ]

    openai_files.cleanup_openai_file(client, "file-one")
    client.files.delete.assert_called_with("file-one")
    client.files.delete.side_effect = RuntimeError("already gone")
    openai_files.cleanup_openai_file(client, "file-one")


def test_openai_upload_wraps_provider_error():
    client = MagicMock()
    client.files.create.side_effect = RuntimeError("provider down")
    with pytest.raises(Exception, match="Failed to upload file to OpenAI: provider down"):
        openai_files.upload_file_to_openai(client, b"payload", "report.pdf")
