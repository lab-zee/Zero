# Railway Step-by-Step: Adding Backend Service

## Current Status
✅ You have Postgres created
❌ Need to add backend service

## Step 1: Add Backend Service

### Method A: Using the "+ Create" Button
1. Look at the **top right** of your Railway dashboard
2. Click the **"+ Create"** button (purple/blue button)
3. A dropdown menu will appear
4. Select **"GitHub Repo"** or **"New Service"** → **"GitHub Repo"**

### Method B: Using the Architecture View
1. You're currently in the "Architecture" view (purple tab at top)
2. Look for a **"+" icon** or **"Add Service"** button on the canvas
3. Click it and select **"GitHub Repo"**

### Method C: Project Menu
1. If you see a project menu/sidebar, look for **"+ New"** or **"Add Service"**
2. Click it and select **"GitHub Repo"**

## Step 2: Connect Your Repository

1. Railway will show a list of your GitHub repositories
2. **Select your LabZ repository**
3. Railway will start analyzing it

## Step 3: Configure the Service

After selecting your repo, Railway will show configuration options:

### Critical Setting: Root Directory
1. Look for a field labeled **"Root Directory"** or **"Service Root"**
2. **Type:** `backend` (this is crucial!)
3. This tells Railway where your backend code lives

### Railway Should Auto-Detect:
- ✅ Dockerfile (in `backend/Dockerfile`)
- ✅ Python project
- ✅ Build settings

### If Railway Shows Options:
- **Build Command:** Leave default (or empty - Dockerfile handles it)
- **Start Command:** Leave default (Dockerfile CMD handles it)
- **Dockerfile Path:** Should auto-detect as `backend/Dockerfile`

## Step 4: Deploy

1. Click **"Deploy"** or **"Add Service"**
2. Railway will start building your Docker image
3. You'll see build logs in real-time

## Step 5: Link to Postgres (Important!)

After the service is created:

### Option A: Auto-Link (Easiest)
1. Railway may automatically link services in the same project
2. Check the backend service's **"Variables"** tab
3. Look for `DATABASE_URL` - if it's there, you're good!

### Option B: Manual Link
1. Click on your **Postgres service** card
2. Go to **"Variables"** or **"Connect"** tab
3. Copy the `DATABASE_URL` value (looks like: `postgresql://user:pass@host:port/dbname`)
4. Click on your **backend service** card
5. Go to **"Variables"** tab
6. Click **"+ New Variable"**
7. Name: `DATABASE_URL`
8. Value: Paste the connection string
9. Click **"Add"**

## Step 6: Add Other Environment Variables

In your backend service → **"Variables"** tab, add:

```
PORT=3001
CORS_ORIGINS=*
SECRET_KEY=<generate-random-string>
```

**To generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Or use: `openssl rand -hex 32`

## Step 7: Verify Deployment

1. Wait for the build to complete (green checkmark)
2. Railway will give you a public URL (like: `https://your-app.up.railway.app`)
3. Test it:
   - Visit: `https://your-url/health` → Should return `{"status":"ok",...}`
   - Visit: `https://your-url/docs` → Should show FastAPI docs

## Troubleshooting

### "I don't see + Create button"
- Try refreshing the page
- Make sure you're in the project dashboard (not settings)
- Look for "+" icons in different locations

### "Root Directory not found"
- Make sure you typed `backend` (lowercase, no spaces)
- Verify your repo structure: `backend/Dockerfile` should exist

### "Build Failed"
- Check the build logs (click on the service → "Deployments" tab)
- Common issues:
  - Wrong root directory
  - Dockerfile not found
  - Build errors in requirements.txt

### "Database Connection Error"
- Verify `DATABASE_URL` is set in backend service variables
- Make sure Postgres service is running (green status)
- Check that the URL format is correct

## Visual Guide

Your Railway dashboard should show:
```
[Postgres Card]  [Backend Service Card]
```

Both services should be visible in the Architecture view.

## Next Steps After Backend is Running

1. Copy your Railway backend URL
2. Deploy frontend to Vercel
3. Update `CORS_ORIGINS` with your Vercel URL
4. Update `VITE_API_URL` in Vercel with your Railway URL

## Still Stuck?

If you can't find the "+ Create" button:
1. Take a screenshot of your Railway dashboard
2. Check if you're in the right project
3. Try clicking around the interface - Railway's UI can vary
4. Look for any "+" icons anywhere on the page

Common locations for add buttons:
- Top right corner
- Next to service cards
- In a sidebar menu
- As a floating action button

