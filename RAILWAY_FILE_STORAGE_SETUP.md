# Railway File Storage Setup

## Important: File Persistence on Railway

Railway containers are **ephemeral** - any files saved to the local filesystem will be **lost when the container restarts or redeploys**.

## Solution: Mount Railway Volumes

You need to mount volumes for **two types of persistent storage**:

1. **File Uploads** - User-uploaded documents
2. **ChromaDB Vector Store** - Document embeddings for semantic search

### Step 1: Mount Volume for File Uploads

1. Go to your Railway project dashboard
2. Click on your **backend service**
3. Go to **Settings** tab
4. Scroll down to **Volumes** section
5. Click **"Mount Volume"** or **"+ New Volume"**
6. Configure:
   - **Mount Path**: `/app/uploads` (must match your `UPLOAD_DIR` env var)
   - **Volume Name**: `file-storage` (or any name you prefer)
7. Click **"Mount"** or **"Create"**

### Step 2: Mount Volume for ChromaDB

1. Still in the **Volumes** section
2. Click **"+ New Volume"** again
3. Configure:
   - **Mount Path**: `/app/chroma_db` (must match your `CHROMA_PERSIST_DIR` env var)
   - **Volume Name**: `chroma-vector-store` (or any name you prefer)
4. Click **"Mount"** or **"Create"**

### Step 3: Verify Environment Variables

Make sure these are set in your Railway service variables:
- Go to **Variables** tab
- Ensure:
  - `UPLOAD_DIR=uploads` (or matches your mount path)
  - `CHROMA_PERSIST_DIR=chroma_db` (or matches your mount path)

**Note:** The mount paths in Railway should be absolute paths like `/app/uploads` and `/app/chroma_db`, while the env vars can be relative like `uploads` and `chroma_db` (they'll resolve to `/app/uploads` and `/app/chroma_db` in the container).

### Step 4: Verify It Works

After mounting the volumes:
1. Upload a file through your app
2. The file should be stored in the mounted volume
3. Restart/redeploy your service
4. Both the file and ChromaDB embeddings should still be accessible

## Alternative: Use External Storage (Future)

If you need more robust file storage, consider:
- **AWS S3** (via boto3)
- **Cloudflare R2** (S3-compatible)
- **DigitalOcean Spaces** (S3-compatible)

These would require code changes to use the storage abstraction layer.

## Current Implementation

- **Files** are stored in: `{UPLOAD_DIR}/` directory (default: `uploads/`)
- **ChromaDB** stores vector embeddings in: `{CHROMA_PERSIST_DIR}/` directory (default: `chroma_db/`)
- PDFs are uploaded to OpenAI Files API (stored by OpenAI)
- Other files (Excel, Word, etc.) are stored locally
- File metadata is stored in PostgreSQL database
- Document embeddings are stored in ChromaDB (per-organization collections)

## Notes

- **Volume mounts ensure persistence** - Without volumes, both files and vector embeddings will be lost on each deploy
- Database records will remain, but:
  - File downloads will fail if files are missing
  - Semantic search will fail if ChromaDB data is missing
- ChromaDB runs **embedded** (in-process), not as a separate service - no need to add a ChromaDB service to Railway
- Each organization has its own ChromaDB collection: `org_{organization_id}_documents`

