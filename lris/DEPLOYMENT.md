# DEPLOYMENT.md — Free-Tier Hosting Guide

## Why not "just Vercel" for everything

Vercel is excellent for the **frontend** (it's a static Vite build - a
perfect fit). It's a poor fit for the **backend**, because:

- Vercel's Python support is serverless functions: no persistent local
  disk, cold starts on every request, and a request time limit. This
  backend loads a CatBoost model file from disk and expects a real
  database connection - awkward and slow on that model.
- SQLite (the dev database) is a local file. Serverless/ephemeral hosts
  wipe local files between invocations, so SQLite effectively doesn't
  work in production there - you need real Postgres.

So the realistic free-tier split is:

| Piece | Where | Why |
|---|---|---|
| **Frontend** (React/Vite static build) | Vercel (or Netlify/Cloudflare Pages) | Exactly what it's built for |
| **Backend** (FastAPI + CatBoost model) | Render free web service (or Fly.io/Railway) | Persistent process, real disk during uptime |
| **Database** | Neon or Supabase (free Postgres) | Real Postgres, works from anywhere, survives backend redeploys |

Everything below uses entirely free tiers. All three (Vercel, Render,
Neon) offer free plans as of this writing - always double-check current
limits on their pricing pages before committing to a workflow, since free
tiers change over time.

---

## 1. Database — Neon (free Postgres)

1. Sign up at neon.tech, create a project.
2. Copy the connection string it gives you - looks like:
   ```
   postgresql://user:password@ep-xxxx.neon.tech/dbname?sslmode=require
   ```
3. Keep this for step 2's `DATABASE_URL`.

(Supabase's free Postgres works identically if you prefer it.)

---

## 2. Backend — Render (free web service)

1. Push this repo to GitHub if you haven't already.
2. On render.com: **New → Web Service**, connect your repo, set:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt && alembic upgrade head`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Set environment variables (Render dashboard -> Environment):
   ```
   ENVIRONMENT=production
   DATABASE_URL=<your Neon connection string from step 1>
   CORS_ORIGINS=["https://your-frontend.vercel.app"]
   LOG_LEVEL=INFO
   ```
   (You'll fill in the real Vercel URL after step 3 - redeploy or update
   the env var once you have it. `CORS_ORIGINS` accepts a JSON array
   string, already wired up via `pydantic-settings` - verified locally.)
4. Deploy. Check `https://<your-render-app>.onrender.com/health` returns
   `{"status": "ok", "environment": "production"}`.

**Important - the trained model won't exist on Render unless you ship it.**
`ml/models_registry/` is gitignored (model files are typically large and
environment-specific). For deployment, either:
- **Commit your trained model directory** to git (CatBoost `.cbm` files
  are usually a few MB - remove the `ml/models_registry/*` line from
  `.gitignore` and commit the specific version folder you want to serve), or
- Upload the model directory to the Render instance via their shell/disk
  feature after deploy.

Without a model present, `/predict` correctly returns a `503` with a
clear message (verified behavior - see `tests/api/test_endpoints.py`)
rather than crashing, so the rest of the app still works while you sort
this out.

**Free tier caveat:** Render's free web services spin down after
inactivity and take ~30-60s to wake on the next request. Fine for a
portfolio demo; not for anything latency-sensitive.

---

## 3. Frontend — Vercel

1. On vercel.com: **New Project**, import the same GitHub repo.
2. Set **Root Directory** to `frontend`.
3. Framework preset: Vite (Vercel usually auto-detects this).
4. Add an environment variable:
   ```
   VITE_API_BASE_URL=https://<your-render-app>.onrender.com/api/v1
   ```
   This is required - without it, the built frontend defaults to a
   relative `/api/v1` path that only works with the local dev proxy (see
   `frontend/src/lib/api.js`). Verified: building with this variable set
   correctly bakes the real backend URL into the output; building
   without it correctly falls back to the relative path for local dev.
5. Deploy. Vercel gives you a URL like `https://lris-frontend.vercel.app`.
6. Go back to Render and update `CORS_ORIGINS` to include this real URL,
   then redeploy the backend (or just restart it) so the browser isn't
   blocked by CORS.

---

## 4. Sanity check

```bash
curl https://<your-render-app>.onrender.com/health
curl https://<your-render-app>.onrender.com/api/v1/stats
```

Then open the Vercel URL in a browser and confirm Search/Estimate/Insights
all load data instead of showing "couldn't reach the backend."

---

## Alternatives to Render for the backend

- **Fly.io** - free allowance, works well for small FastAPI apps, no
  spin-down the way Render's free tier has, but requires their CLI and a
  `fly.toml` (not included here - ask if you want one generated).
- **Railway** - similar to Render, historically had a more generous free
  tier but check current terms, they've changed this more than once.
- **PythonAnywhere** - simplest for a single small Flask/FastAPI app, but
  less natural for a repo with this many moving parts (migrations, a
  separate ML model directory).

Whichever you pick, the three things that must be true are the same:
persistent-enough process to serve FastAPI, a real Postgres database, and
somewhere for the trained model files to physically live.
