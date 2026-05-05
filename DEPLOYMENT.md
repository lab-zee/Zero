# Deployment Guide

This guide covers deploying LabZ to **Vercel (Frontend)** and **Railway (Backend + Database)**.

## Prerequisites

- GitHub account
- Vercel account (free)
- Railway account (free trial, then $5/month)

## Step 1: Prepare Your Repository

Make sure your code is pushed to GitHub:

```bash
git add .
git commit -m "Prepare for deployment"
git push origin main
```

## Step 2: Deploy Backend to Railway

### 2.1 Create Railway Account
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Click "New Project"

### 2.2 Add PostgreSQL Database
1. In your Railway project, click "+ New"
2. Select "Database" → "Add PostgreSQL"
3. Railway will create a Postgres instance
4. **Copy the connection string** from the "Connect" tab (you'll need this)

### 2.3 Deploy Backend Service
1. In your Railway project, click "+ New"
2. Select "GitHub Repo" → choose your LabZ repository
3. Railway will ask for configuration:
   - **Root Directory:** Set to `backend` (this tells Railway where your backend code is)
   - Railway will auto-detect the Dockerfile in the `backend` folder
   - Alternatively, Railway can use the `railway.json` config at the repo root

### 2.4 Set Environment Variables
In your Railway backend service, go to "Variables" and add:

```
DATABASE_URL=<your-postgres-connection-string-from-railway>
PORT=3001
CORS_ORIGINS=https://your-app.vercel.app
OPENAI_API_KEY=<your-openai-api-key>
OPENAI_MODEL=gpt-4o
UPLOAD_DIR=uploads
SECRET_KEY=<generate-a-random-secret-key>
```

**Important Notes:**
- `OPENAI_MODEL`: Use `gpt-4o` or `gpt-4o-mini` for PDF file support
- `UPLOAD_DIR`: Railway containers are ephemeral. For persistent file storage:
  1. Go to your Railway service → **Settings** → **Volumes**
  2. Click **"Mount Volume"**
  3. Mount path: `/app/uploads`
  4. This ensures uploaded files persist across deployments
- `CHROMA_PERSIST_DIR`: Also mount a volume for ChromaDB vector store:
  1. In the same **Volumes** section, click **"+ New Volume"** again
  2. Mount path: `/app/chroma_db`
  3. This ensures document embeddings persist across deployments
  4. Add `CHROMA_PERSIST_DIR=chroma_db` to your environment variables

**Note:** ChromaDB runs embedded (in-process), not as a separate Railway service. You just need to mount a volume for persistence.

**To generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2.5 Get Your Backend URL
1. Once deployed, Railway will give you a URL like: `https://your-app.up.railway.app`
2. **Copy this URL** - you'll need it for the frontend

## Step 3: Deploy Frontend to Vercel

### 3.1 Create Vercel Project
1. Go to [vercel.com](https://vercel.com)
2. Sign up/login with GitHub
3. Click "Add New Project"
4. Import your LabZ repository

### 3.2 Configure Build Settings
Vercel should auto-detect, but verify:
- **Framework Preset:** Vite
- **Root Directory:** `frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Install Command:** `npm install`

### 3.3 Set Environment Variables
In Vercel project settings → Environment Variables, add:

```
VITE_API_URL=https://your-backend-url.up.railway.app
```

**Important:** Replace `your-backend-url` with your actual Railway backend URL

### 3.4 Deploy
Click "Deploy" - Vercel will build and deploy your frontend!

## Step 4: Update CORS Settings

After you have your Vercel URL, update Railway backend environment variable:

```
CORS_ORIGINS=https://your-app.vercel.app
```

Then redeploy the backend (Railway auto-redeploys on env var changes).

## Step 5: Test Your Deployment

1. Visit your Vercel URL
2. Try registering a new user
3. Try logging in
4. Send a chat message

## Troubleshooting

### Backend Issues

**Database Connection Errors:**
- Verify `DATABASE_URL` is set correctly in Railway
- Check that Postgres service is running
- Ensure the connection string format is: `postgresql://user:pass@host:port/dbname`

**CORS Errors:**
- Make sure `CORS_ORIGINS` includes your Vercel URL (no trailing slash)
- Redeploy backend after changing CORS settings

**Port Issues:**
- Railway sets `PORT` automatically - make sure your Dockerfile uses `${PORT}`

### Frontend Issues

**API Connection Errors:**
- Verify `VITE_API_URL` is set correctly in Vercel
- Check that the backend URL is accessible (try opening it in browser)
- Make sure there's no trailing slash in the URL

**Build Errors:**
- Check Vercel build logs
- Ensure all dependencies are in `package.json`
- Verify Node.js version (Vercel auto-detects)

## Cost Breakdown

- **Vercel (Frontend):** Free
- **Railway (Backend + Postgres):** $5/month
- **Total:** ~$5/month

## Railway Tips

- Railway gives you 500 hours free per month on the free plan
- After that, it's $5/month for the hobby plan
- Postgres is included in the service
- Railway auto-deploys on git push (if connected to GitHub)

## Vercel Tips

- Vercel free tier is very generous
- Automatic deployments on every push
- Preview deployments for PRs
- Global CDN included

## Monitoring

- **Railway:** Check logs in the Railway dashboard
- **Vercel:** Check build logs and function logs in Vercel dashboard
- **Backend Health:** Visit `https://your-backend.railway.app/health`
- **API Docs:** Visit `https://your-backend.railway.app/docs`

## Next Steps

- Set up custom domains (optional)
- Configure monitoring/alerting
- Set up CI/CD (already done if using GitHub)
- Add environment-specific configs (staging/production)

