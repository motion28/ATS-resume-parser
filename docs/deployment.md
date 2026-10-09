# Render deployment

[Back to README](../README.md)

Publish this project to a GitHub repository and connect that repository to
Render. Commit source, lockfiles, and `.env.example` files; do not commit `.env`,
`.venv`, `node_modules`, or `dist`. The root `.gitignore` excludes them, including
`backend/.env`. Enter the actual Groq key privately in Render's backend
environment settings; never put it in this README or the frontend settings.

Create the backend first: **New > Web Service**, select your repository, and use
these settings (commands are relative to the root directory):

| Setting | Value |
| --- | --- |
| Runtime | Python 3 |
| Branch | Your published branch, normally `main` |
| Root directory | `backend` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Instance type | **Free** |
| Health check path | `/api/health` |

Add these backend environment variables:

| Variable | Value |
| --- | --- |
| `PYTHON_VERSION` | `3.12.14` |
| `GROQ_API_KEY` | Your key, entered privately in Render |
| `GROQ_MODEL` | `openai/gpt-oss-120b` |
| `ALLOWED_ORIGINS` | The frontend's `https://<site-name>.onrender.com` origin |

You can initially leave `ALLOWED_ORIGINS` blank and update it after creating the
frontend. The explicit Python version avoids relying on Render's changing
default. Wait for the backend to deploy, then open
`https://<backend-name>.onrender.com/api/health`; expect `{"status":"ok"}`.

Create **New > Static Site** from the same repository:

| Setting | Value |
| --- | --- |
| Branch | The same published branch |
| Root directory | `frontend` |
| Build command | `npm ci && npm run build` |
| Publish directory | `dist` |
| `NODE_VERSION` environment variable | `24.13.1` |
| `SKIP_INSTALL_DEPS` environment variable | `true` |
| `VITE_API_BASE_URL` environment variable | `https://<backend-name>.onrender.com` |

Static Sites are free. `SKIP_INSTALL_DEPS=true` skips Render's automatic dependency
installation because the build command already runs `npm ci`. This page uses no
client-side routes, so it needs no rewrite rule.

After the Static Site URL is assigned, set the backend's `ALLOWED_ORIGINS` to
that exact origin and save/redeploy the backend. Open the public frontend and
verify health, then upload an entirely fictional text-based PDF. Check structured
results, missing-data warnings when applicable, and raw text. Extracted resume
text is sent to Groq on every successful text extraction, including in production.

Render's free Web Service spins down after 15 minutes without inbound traffic.
Its next request wakes it up, which takes about one minute. If health or an
upload fails during startup, wait and refresh/retry. The Static Site remains
available while the backend sleeps. Do not choose a paid instance or add paid
resources for this setup.

Official instructions: [FastAPI on Render](https://render.com/docs/deploy-fastapi),
[Static Sites](https://render.com/docs/static-sites),
[monorepo root directories](https://render.com/docs/monorepo-support),
[Python versions](https://render.com/docs/python-version), and
[free-service behavior](https://render.com/docs/free).

