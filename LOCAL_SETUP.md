# Local Development Setup

## Quick Start (Docker Compose - Recommended)

The easiest way to run the app locally is using Docker Compose:

### Prerequisites
- Docker Desktop installed and running
- OpenAI API key (get one from https://platform.openai.com/api-keys)

### Steps

1. **Set your OpenAI API key** (optional - there's a default in docker-compose.yml, but you should use your own):
   - Create a `.env` file in the root directory (optional)
   - Or edit `docker-compose.yml` and replace the `OPENAI_API_KEY` value

2. **Start all services:**
   ```bash
   docker-compose up
   ```

   This will:
   - Start PostgreSQL database
   - Start the FastAPI backend (runs migrations automatically)
   - Start the React frontend
   - All services will be available at:
     - Frontend: http://localhost:3000
     - Backend API: http://localhost:3001
     - PostgreSQL: localhost:5432

3. **Access the application:**
   - Open your browser to http://localhost:3000
   - Register a new account or login
   - Create an organization
   - Start chatting!

4. **Stop services:**
   ```bash
   docker-compose down
   ```

5. **View logs:**
   ```bash
   docker-compose logs -f
   ```

## Alternative: Local Development (Without Docker)

If you prefer to run services locally:

### Backend Setup

1. **Start PostgreSQL:**
   ```bash
   docker-compose up postgres -d
   ```

2. **Set up Python environment:**
   ```bash
   cd backend
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

5. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Start backend:**
   ```bash
   uvicorn src.main:app --reload --port 3001
   ```

### Frontend Setup

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Start frontend:**
   ```bash
   npm run dev
   ```

3. **Access the app:**
   - Frontend will be at http://localhost:5173 (Vite default)
   - Make sure backend is running on http://localhost:3001

## Troubleshooting

### Database Migration Issues

If you see migration errors, you can reset the database:

```bash
# Stop containers
docker-compose down

# Remove the database volume (WARNING: This deletes all data)
docker volume rm labz_postgres_data

# Start again
docker-compose up
```

### Port Already in Use

If ports 3000, 3001, or 5432 are already in use:

1. Edit `docker-compose.yml` and change the port mappings
2. Or stop the service using those ports

### Frontend Not Connecting to Backend

1. Check that backend is running: http://localhost:3001/health
2. Check browser console for CORS errors
3. Verify `VITE_API_URL` in frontend environment

### OpenAI API Errors

1. Make sure your API key is valid
2. Check you have credits in your OpenAI account
3. Verify the key is set correctly in docker-compose.yml or .env

## New Features Added

### Thread Preferences
- Each thread can now have preferences for budget-conscious vs outcome-conscious
- This affects how agents make recommendations
- UI controls coming soon!

### Dark Mode
- Toggle dark/light mode using the moon/sun icon in the sidebar
- Theme persists across sessions

### Enhanced Prompts
- All prompts now emphasize data-driven recommendations
- ROI analysis is included for all spending/investment recommendations
- Measurement frameworks and KPIs are always provided

### Image Generation
- Synthesizer agent now uses image_generator tool more frequently
- Creates visual aids, diagrams, and flowcharts automatically

## Development Tips

- Backend auto-reloads on file changes (when using `--reload`)
- Frontend hot-reloads automatically (Vite)
- Check backend logs: `docker-compose logs -f backend`
- Check frontend logs: `docker-compose logs -f frontend`
- Database migrations run automatically on backend startup


