"""
Vector store service for document corpus using ChromaDB and OpenAI embeddings.
Provides semantic search capabilities for organization documents.
"""
import os
import chromadb
from chromadb.config import Settings
from typing import List, Optional, Dict, Tuple
from openai import OpenAI
import hashlib

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ChromaDB persistence directory
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(
    path=CHROMA_PERSIST_DIR,
    settings=Settings(anonymized_telemetry=False)
)


def get_collection_name(organization_id: int) -> str:
    """Get the ChromaDB collection name for an organization"""
    return f"org_{organization_id}_documents"


def get_or_create_collection(organization_id: int):
    """Get or create a ChromaDB collection for an organization"""
    collection_name = get_collection_name(organization_id)
    try:
        collection = chroma_client.get_collection(name=collection_name)
    except Exception:
        # Collection doesn't exist, create it
        collection = chroma_client.create_collection(
            name=collection_name,
            metadata={"organization_id": organization_id}
        )
    return collection


def generate_embedding(text: str) -> List[float]:
    """Generate embedding for text using OpenAI"""
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        raise


def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """
    Split text into chunks with overlap for better context preservation.
    Uses simple character-based chunking (can be improved with sentence-aware chunking).
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary if possible
        if end < len(text):
            # Look for sentence endings in the last 100 chars
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            if break_point > chunk_size - 200:  # Don't break too early
                chunk = chunk[:break_point + 1]
                end = start + len(chunk)
        
        chunks.append(chunk)
        start = end - chunk_overlap  # Overlap for context
    
    return chunks


def add_document_to_store(
    organization_id: int,
    file_id: int,
    filename: str,
    text_content: str
) -> None:
    """
    Add a document to the vector store by chunking it and generating embeddings.
    If the document already exists, it will be updated.
    """
    collection = get_or_create_collection(organization_id)
    
    # Delete existing chunks for this file (in case of update)
    try:
        collection.delete(ids=[f"file_{file_id}_chunk_{i}" for i in range(1000)])  # Delete up to 1000 chunks
    except Exception:
        pass  # File doesn't exist yet, that's fine
    
    # Chunk the text
    chunks = chunk_text(text_content)
    
    if not chunks:
        print(f"Warning: No chunks generated for file {file_id}")
        return
    
    # Generate embeddings for all chunks
    embeddings = []
    ids = []
    metadatas = []
    documents = []
    
    for i, chunk in enumerate(chunks):
        chunk_id = f"file_{file_id}_chunk_{i}"
        try:
            embedding = generate_embedding(chunk)
            embeddings.append(embedding)
            ids.append(chunk_id)
            metadatas.append({
                "file_id": file_id,
                "filename": filename,
                "chunk_index": i,
                "total_chunks": len(chunks)
            })
            documents.append(chunk)
        except Exception as e:
            print(f"Error processing chunk {i} for file {file_id}: {e}")
            continue
    
    if not embeddings:
        print(f"Warning: No embeddings generated for file {file_id}")
        return
    
    # Add to collection
    try:
        collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
        print(f"Added {len(embeddings)} chunks for file {file_id} to vector store")
    except Exception as e:
        print(f"Error adding document to vector store: {e}")
        raise


def remove_document_from_store(organization_id: int, file_id: int) -> None:
    """Remove a document from the vector store"""
    try:
        collection = get_or_create_collection(organization_id)
        # Delete all chunks for this file using where clause
        # ChromaDB supports deleting by metadata
        collection.delete(where={"file_id": file_id})
        print(f"Removed document {file_id} from vector store")
    except Exception as e:
        print(f"Error removing document from vector store: {e}")
        # Try alternative method: get all and delete by IDs
        try:
            results = collection.get(where={"file_id": file_id})
            if results and results.get('ids'):
                collection.delete(ids=results['ids'])
                print(f"Removed document {file_id} from vector store (fallback method)")
        except Exception as e2:
            print(f"Fallback deletion also failed: {e2}")


def search_documents(
    organization_id: int,
    query: str,
    n_results: int = 5
) -> List[Dict[str, any]]:
    """
    Search documents in the vector store using semantic search.
    Returns a list of results with document chunks, metadata, and similarity scores.
    """
    try:
        collection = get_or_create_collection(organization_id)
        
        # Generate embedding for query
        query_embedding = generate_embedding(query)
        
        # Search
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # Format results
        formatted_results = []
        if results['ids'] and len(results['ids']) > 0:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    "chunk": results['documents'][0][i] if results['documents'] else "",
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if results['distances'] else None,
                    "similarity": 1 - (results['distances'][0][i] if results['distances'] else 1.0)  # Convert distance to similarity
                })
        
        return formatted_results
    except Exception as e:
        print(f"Error searching vector store: {e}")
        # Return empty results on error
        return []


def get_document_count(organization_id: int) -> int:
    """Get the number of documents in the vector store for an organization"""
    try:
        collection = get_or_create_collection(organization_id)
        count = collection.count()
        return count
    except Exception:
        return 0

