# ATS Resume Parser

Upload a PDF resume to extract raw text with PyMuPDF and structured resume data
with Groq. The frontend displays structured results, missing-information
warnings, and raw extracted text.

## Structure

The existing `ATS Resume Parser` workspace is the project root (equivalent to
`ats-resume-parser/`):

```text
ats-resume-parser/
├── frontend/       # React page and Vite configuration
├── backend/        # FastAPI app and Python requirements
├── .gitignore
└── README.md
```

## Run locally

Prerequisites: Node.js 22.12+, npm, and Python. Deployment uses Node 24.13.1
and Python 3.12.14, pinned in `frontend/.node-version` and
`backend/.python-version`. The pinned backend dependencies also support the
existing local Python 3.9 environment.
Use two terminals, both initially opened in the project root.

**Terminal 1 — backend**

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create `backend/.env` locally (copy `.env.example` only if `.env` does not already
exist), then fill in:

```dotenv
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

Put the actual key only in that local file or the backend process environment,
never in chat, frontend code, or Git. `.env` is gitignored. `python-dotenv` loads
this exact backend file; existing environment variables take precedence.
Restart the backend after changing configuration:

```sh
python -m uvicorn main:app --reload --port 8000
```

On later runs, activate the existing environment and run Uvicorn again.
On Windows, use `.venv\Scripts\activate` instead of `source .venv/bin/activate`.

**Terminal 2 — frontend**

```sh
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. You should see **Backend connected — status: ok**.
Select a text-based PDF and click **Upload Resume** to see its results.
If the backend was started after opening the page, refresh the page.
Stop either server with Ctrl+C in its terminal.

If Node/npm is not found and you use nvm, run `source ~/.nvm/nvm.sh` and
`nvm use 24` before the frontend commands.

## How the connection works

`frontend/src/App.tsx` uses `useEffect` to call
the configured backend's `GET /api/health` when the page mounts, then updates
React state based on the JSON response. The request is cancelled on unmount.

In `backend/main.py`, `@app.get('/api/health')` registers a route, similar to
Express's `app.get(...)`. Returning a Python dictionary automatically sends JSON:
`{"status": "ok"}`. Uvicorn runs the Python web app and listens for HTTP requests.
The `.venv` folder keeps this project's Python dependencies isolated.

The frontend and backend run on different ports, so the browser considers them
different origins. FastAPI's `CORSMiddleware` (similar to Express CORS middleware)
allows GET and POST requests from `http://localhost:5173` and `http://127.0.0.1:5173`.
Vite uses `strictPort` so it won't silently switch to an origin that isn't allowed.
These local origins remain allowed. Add other origins using the backend
`ALLOWED_ORIGINS` variable: a comma-separated list of complete origins, such as
`https://ats-resume-parser.onrender.com` (no paths).

The frontend reads `VITE_API_BASE_URL`, defaulting to `http://localhost:8000`
when unset or blank. For another backend, set it in `frontend/.env.local` using
`frontend/.env.example` as a guide, then restart Vite. Vite embeds this public URL
at build time; changing it in production requires a new frontend build.
Never put `GROQ_API_KEY` or other secrets in a `VITE_` variable.

## PDF upload and extraction

React puts the selected file in a `FormData` object under the name `file` and sends
it to `POST /api/parse`. The browser supplies the multipart request headers;
don't set `Content-Type` manually because it needs a matching boundary.

FastAPI gives the endpoint an `UploadFile`, similar to the file object Multer
provides in Express. It contains the filename and a readable file object.
`python-multipart` lets FastAPI decode the multipart form upload.

The endpoint checks the `.pdf` extension and lets PyMuPDF verify the actual file
format. PyMuPDF opens the uploaded bytes in memory and calls `page.get_text()`
for every page, joining the results with newlines. It reads the existing text
layer; it does not perform OCR or identify resume fields. Text order can differ
from the visual layout, particularly for columns.

The response is `{"filename": "resume.pdf", "text": "...", "resume": {...}}`.
**The extracted resume text is sent to Groq for processing.** The original PDF
is not sent to Groq. Only upload resumes you intend to share with that service.
Invalid, empty,
damaged, or password-protected files return HTTP 400 with a helpful `detail`.
PDFs with no readable text return HTTP 422. React displays these errors and
disables the form while extraction is running.

The regular Python `def` endpoint runs in FastAPI's worker thread pool so the
blocking extraction doesn't run directly on the async event loop. The `with`
block closes the PyMuPDF document automatically; `finally` closes the upload
whether parsing succeeds or fails. `HTTPException` sends an error status and JSON
body, similar to returning `res.status(400).json(...)` in Express.

The application does not intentionally persist resumes to disk or a database.
FastAPI's default upload handling may spool larger uploads to temporary disk
files. Closing the upload releases that temporary storage. The endpoint reads
the uploaded bytes into memory for PyMuPDF extraction.

## Structured extraction

`backend/extraction.py` uses the official Groq SDK and strict JSON Schema output.
The schema is generated from `ParsedResume` and its nested Pydantic models.
Models reject extra fields; local defaults remain `None` and independent empty
lists. The provider schema requires all fields and omits schema defaults, so
Groq must explicitly return `null` for missing scalars and `[]` for missing lists.
Responses are validated again locally, including checking for omitted fields.
Dates remain strings. Instructions forbid inventing facts and tell the model
to treat resume text as data. Extraction accuracy still depends on the model.

The default model is `openai/gpt-oss-120b`; any `GROQ_MODEL` replacement must
support Groq's strict structured outputs. Requests use a 30-second SDK timeout,
zero automatic retries, and an 8,192 completion-token limit. Rate limits return
429, timeouts 504, missing configuration/access errors 503, refusals 422, and
other provider/output errors 502. Errors contain safe messages, never raw
provider errors or resume contents. SDK/HTTP debug logging is suppressed.
`/api/health` stays available without a key. Extraction failures do not return
an empty resume or a partial success response.

Added dependencies: `groq==1.0.0` and `python-dotenv==1.2.1`, both declaring
Python 3.9 support in installed package metadata and tested on Python 3.9.6.
Deployment uses Python 3.12.14 with the same pinned dependencies.

## Deploy to Render (free services)

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

## Check the setup

With the backend running:

```sh
curl -i -H 'Origin: http://localhost:5173' http://localhost:8000/api/health
```

Expect HTTP 200, `{"status":"ok"}`, and
`access-control-allow-origin: http://localhost:5173`.
FastAPI's generated API docs are available at http://localhost:8000/docs.

To test a PDF (its extracted text will be sent to Groq):

```sh
curl -F 'file=@/absolute/path/to/resume.pdf' http://localhost:8000/api/parse
```

From `frontend/`, run `npm run build` to type-check TypeScript and build the app.
From `backend/`, run `.venv/bin/python check_backend.py` for offline checks.
These use standard-library mocks, HTTPX's mock transport, and FastAPI's test
client, with fictional PDFs and no real credentials, `.env` loading, or provider
network calls. They cover structured extraction, errors, PDF validation, health,
and model defaults. No additional testing framework is installed.

References: [Vite setup](https://vite.dev/guide/) and
[FastAPI file uploads](https://fastapi.tiangolo.com/tutorial/request-files/),
[FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/), and
[PyMuPDF text extraction](https://pymupdf.readthedocs.io/en/latest/recipes-text.html),
[Groq structured outputs](https://console.groq.com/docs/structured-outputs), and
[the official Groq Python SDK](https://github.com/groq/groq-python).
