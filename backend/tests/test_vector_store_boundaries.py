"""Tests for vector-store behavior with Chroma/OpenAI mocked at their boundaries."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src import vector_store


def test_collection_name_and_get_or_create_paths(monkeypatch):
    existing = object()
    client = MagicMock()
    client.get_collection.return_value = existing
    monkeypatch.setattr(vector_store, "chroma_client", client)

    assert vector_store.get_collection_name(12) == "org_12_documents"
    assert vector_store.get_or_create_collection(12) is existing
    client.get_collection.assert_called_once_with(name="org_12_documents")

    created = object()
    client.get_collection.side_effect = RuntimeError("missing")
    client.create_collection.return_value = created
    assert vector_store.get_or_create_collection(13) is created
    client.create_collection.assert_called_with(
        name="org_13_documents",
        metadata={"organization_id": 13},
    )


def test_generate_embedding_forwards_payload_and_propagates_errors(monkeypatch):
    embeddings = MagicMock()
    embeddings.create.return_value = SimpleNamespace(
        data=[SimpleNamespace(embedding=[0.1, 0.2])]
    )
    monkeypatch.setattr(vector_store.client, "embeddings", embeddings)

    assert vector_store.generate_embedding("query") == [0.1, 0.2]
    embeddings.create.assert_called_once_with(model="text-embedding-3-small", input="query")

    embeddings.create.side_effect = RuntimeError("provider down")
    with pytest.raises(RuntimeError, match="provider down"):
        vector_store.generate_embedding("query")


def test_chunk_text_short_long_and_sentence_boundary():
    assert vector_store.chunk_text("short", chunk_size=10) == ["short"]

    text = "a" * 205 + ". " + "b" * 250
    chunks = vector_store.chunk_text(text, chunk_size=300, chunk_overlap=20)

    assert chunks[0].endswith(".")
    assert "".join(chunks).count("b") >= 250
    assert len(chunks) == 2


def test_add_document_deletes_old_chunks_and_adds_successful_embeddings(monkeypatch):
    collection = MagicMock()
    collection.delete.side_effect = RuntimeError("not present")
    monkeypatch.setattr(vector_store, "get_or_create_collection", lambda _org: collection)
    monkeypatch.setattr(vector_store, "chunk_text", lambda _text: ["first", "bad", "third"])

    def embed(chunk: str):
        if chunk == "bad":
            raise RuntimeError("embedding failed")
        return [float(len(chunk))]

    monkeypatch.setattr(vector_store, "generate_embedding", embed)

    vector_store.add_document_to_store(4, 9, "report.txt", "content")

    assert collection.delete.call_count == 1
    collection.add.assert_called_once_with(
        ids=["file_9_chunk_0", "file_9_chunk_2"],
        embeddings=[[5.0], [5.0]],
        metadatas=[
            {"file_id": 9, "filename": "report.txt", "chunk_index": 0, "total_chunks": 3},
            {"file_id": 9, "filename": "report.txt", "chunk_index": 2, "total_chunks": 3},
        ],
        documents=["first", "third"],
    )


def test_add_document_stops_without_chunks_or_embeddings(monkeypatch):
    collection = MagicMock()
    monkeypatch.setattr(vector_store, "get_or_create_collection", lambda _org: collection)
    monkeypatch.setattr(vector_store, "chunk_text", lambda _text: [])
    vector_store.add_document_to_store(1, 2, "empty.txt", "")
    collection.add.assert_not_called()

    monkeypatch.setattr(vector_store, "chunk_text", lambda _text: ["chunk"])
    monkeypatch.setattr(
        vector_store,
        "generate_embedding",
        lambda _chunk: (_ for _ in ()).throw(RuntimeError("down")),
    )
    vector_store.add_document_to_store(1, 2, "empty.txt", "content")
    collection.add.assert_not_called()


def test_add_document_propagates_collection_add_failure(monkeypatch):
    collection = MagicMock()
    collection.add.side_effect = RuntimeError("write failed")
    monkeypatch.setattr(vector_store, "get_or_create_collection", lambda _org: collection)
    monkeypatch.setattr(vector_store, "chunk_text", lambda _text: ["chunk"])
    monkeypatch.setattr(vector_store, "generate_embedding", lambda _chunk: [1.0])

    with pytest.raises(RuntimeError, match="write failed"):
        vector_store.add_document_to_store(1, 2, "report.txt", "content")


def test_remove_document_uses_metadata_then_id_fallback(monkeypatch):
    collection = MagicMock()
    monkeypatch.setattr(vector_store, "get_or_create_collection", lambda _org: collection)
    vector_store.remove_document_from_store(1, 8)
    collection.delete.assert_called_once_with(where={"file_id": 8})

    collection.reset_mock()
    collection.delete.side_effect = [RuntimeError("where unsupported"), None]
    collection.get.return_value = {"ids": ["file_8_chunk_0", "file_8_chunk_1"]}
    vector_store.remove_document_from_store(1, 8)
    assert collection.delete.call_args_list[-1].kwargs == {
        "ids": ["file_8_chunk_0", "file_8_chunk_1"]
    }


def test_search_formats_results_and_returns_empty_on_failure(monkeypatch):
    collection = MagicMock()
    collection.query.return_value = {
        "ids": [["one", "two"]],
        "documents": [["first", "second"]],
        "metadatas": [[{"file_id": 1}, {"file_id": 2}]],
        "distances": [[0.2, 0.75]],
    }
    monkeypatch.setattr(vector_store, "get_or_create_collection", lambda _org: collection)
    monkeypatch.setattr(vector_store, "generate_embedding", lambda _query: [0.4])

    assert vector_store.search_documents(5, "risk", n_results=2) == [
        {
            "chunk": "first",
            "metadata": {"file_id": 1},
            "distance": 0.2,
            "similarity": 0.8,
        },
        {
            "chunk": "second",
            "metadata": {"file_id": 2},
            "distance": 0.75,
            "similarity": 0.25,
        },
    ]
    collection.query.assert_called_once_with(query_embeddings=[[0.4]], n_results=2)

    collection.query.side_effect = RuntimeError("query failed")
    assert vector_store.search_documents(5, "risk") == []


def test_document_count_returns_count_or_zero(monkeypatch):
    collection = MagicMock()
    collection.count.return_value = 7
    monkeypatch.setattr(vector_store, "get_or_create_collection", lambda _org: collection)
    assert vector_store.get_document_count(1) == 7

    monkeypatch.setattr(
        vector_store,
        "get_or_create_collection",
        lambda _org: (_ for _ in ()).throw(RuntimeError("down")),
    )
    assert vector_store.get_document_count(1) == 0
