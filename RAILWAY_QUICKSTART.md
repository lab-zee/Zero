# Railway Quick Start Guide

Since you're new to Railway, here's a focused guide on getting your backend deployed.

## What is Railway?

Railway is a platform that makes deploying apps super simple:
- Connects to your GitHub repo
- Auto-detects Dockerfiles
- Handles builds and deployments automatically
- Includes managed Postgres databases
- Auto-deploys on every git push

## Step-by-Step: Deploying Your Backend

### 1. Sign Up
- Go to [railway.app](https://railway.app)
- Click "Start a New Project"
- Sign in with GitHub (recommended - enables auto-deploy)

### 2. Create a New Project
- Click "New Project"
- Select "Deploy from GitHub repo"
- Choose your LabZ repository
- Railway will start analyzing your repo

### 3. Add PostgreSQL Database
**Important:** Add the database FIRST, then the backend service.

1. In your Railway project dashboard, click **"+ New"**
2. Select **"Database"** → **"Add PostgreSQL"**
3. Railway creates the database automatically
4. Click on the Postgres service
5. Go to the **"Connect"** or **"Variables"** tab
6. Copy the `DATABASE_URL` value (looks like: `postgresql://user:pass@host:port/dbname`)
   - **Save this!** You'll need it for the backend

### 4. Add Backend Service
1. Click **"+ New"** again
2. Select **"GitHub Repo"** → choose your LabZ repo
3. Railway will show configuration options:
   - **Root Directory:** Type `backend` (this is important!)
   - Railway will auto-detect `backend/Dockerfile`
4. Click **"Deploy"**

### 5. Configure Environment Variables
1. Click on your backend service
2. Go to the **"Variables"** tab
3. Add these variables:

```
DATABASE_URL=<paste-the-database-url-from-step-3>
PORT=3001
CORS_ORIGINS=https://your-app.vercel.app
SECRET_KEY=<generate-a-random-string>
```

**To generate SECRET_KEY:**
```bash
# On Mac/Linux:
openssl rand -hex 32

# Or use Python:
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Note:** For `CORS_ORIGINS`, you'll update this after deploying to Vercel. For now, you can leave it or set it to `*` temporarily.

### 6. Get Your Backend URL
1. Once deployed, Railway gives you a public URL
2. It looks like: `https://your-app-name.up.railway.app`
3. Click on your service → **"Settings"** → **"Generate Domain"** if needed
4. **Copy this URL** - you'll need it for Vercel!

### 7. Test Your Backend
- Visit: `https://your-backend-url.up.railway.app/health`
- Should return: `{"status":"ok","timestamp":"..."}`
- Visit: `https://your-backend-url.up.railway.app/docs`
- Should show FastAPI interactive docs

## Railway Dashboard Overview

### Service Tabs:
- **Deployments:** See build history and logs
- **Metrics:** CPU, memory usage
- **Variables:** Environment variables
- **Settings:** Domain, scaling, etc.
- **Logs:** Real-time application logs

### Useful Features:
- **Auto-deploy:** Every push to main branch triggers a new deployment
- **Rollback:** Click any previous deployment to rollback
- **Logs:** Real-time logs help debug issues
- **Metrics:** Monitor resource usage

## Common Issues & Solutions

### "Build Failed"
- Check the build logs in Railway dashboard
- Make sure `Root Directory` is set to `backend`
- Verify `backend/Dockerfile` exists

### "Database Connection Error"
- Verify `DATABASE_URL` is set correctly
- Make sure Postgres service is running (green status)
- Check that the URL format is correct

### "Port Already in Use"
- Railway sets `PORT` automatically - don't hardcode it
- Our Dockerfile uses `${PORT:-3001}` which handles this

### "CORS Errors"
- Make sure `CORS_ORIGINS` includes your Vercel URL
- No trailing slashes in the URL
- Redeploy after changing CORS settings

## Railway Pricing

- **Free Trial:** 500 hours/month (plenty for a side project!)
- **Hobby Plan:** $5/month after trial
- **Includes:** Postgres database, unlimited deployments, 512MB RAM, 1GB disk

## Pro Tips

1. **Use GitHub Integration:** Auto-deploys on every push
2. **Check Logs First:** Most issues show up in the logs
3. **Environment Variables:** Railway auto-injects `DATABASE_URL` if services are linked
4. **Custom Domains:** Free custom domains in hobby plan
5. **Monitoring:** Railway shows basic metrics for free

## Next Steps

After Railway is working:
1. Deploy frontend to Vercel (see DEPLOYMENT.md)
2. Update `CORS_ORIGINS` with your Vercel URL
3. Update `VITE_API_URL` in Vercel with your Railway URL
4. Test the full stack!

## Getting Help

- Railway Docs: [docs.railway.app](https://docs.railway.app)
- Railway Discord: [discord.gg/railway](https://discord.gg/railway)
- Check logs in Railway dashboard for specific errors

