# Beacon Web Platform

Run the backend and frontend as follows.

## Backend (FastAPI)

From the **repo root** (parent of `backend/`):

```bash
cd backend
pip install -r requirements.txt
# Set .env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
uvicorn backend.main:app --reload --app-dir .
```

Or from repo root:

```bash
pip install -r backend/requirements.txt
# Copy backend/.env.example to backend/.env and set values
uvicorn backend.main:app --reload
```

## Frontend (Next.js 14)

```bash
cd frontend
npm install
# Set .env.local: NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, NEXT_PUBLIC_API_URL (e.g. http://localhost:8000)
npm run dev
```

Open http://localhost:3000. Sign up, complete onboarding, then use Dashboard, Find Mentees/Mentors, Messages, and Profile.

## Env vars

- **Frontend:** `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL`
- **Backend:** `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (JWT is verified via Supabase Auth API; works with asymmetric signing.)

Do not expose the service role key to the frontend.
