# ATS Resume Parser

Upload a text-based PDF resume to see the contact information, skills, work
experience, and education a parser can extract. Compare structured results with
the raw text and review warnings for missing information.

## Features

- PDF upload with loading feedback and clear file or extraction errors.
- Structured contact details, skills, experience, and education.
- Neutral missing-data labels and warnings for missing name, email, skills,
  experience, or education.
- Raw extracted text alongside the results for comparison with the original PDF.
- Responsive interface with keyboard focus states and plain-text rendering of
  resume content.

## Stack and flow

**Frontend:** React, TypeScript, Vite.

**Backend:** Python, FastAPI, PyMuPDF, Groq, Pydantic.

```text
PDF upload → text extraction → AI extraction → Pydantic validation
           → structured results and parsing warnings
```

React sends the PDF as `FormData` to `POST /api/parse`. FastAPI validates the PDF,
PyMuPDF reads text from every page, and Groq converts that text into structured
JSON. Pydantic validates the returned data. React displays the results and
computes missing-information warnings from the validated fields.

The API returns `filename`, `text`, and `resume`. `GET /api/health` returns
`{"status":"ok"}` and works without a Groq key.

## Run locally

Use **Python 3.12.14** and **Node.js 24.13.1** (the project's pinned deployment
versions), plus npm and a Groq API key. Start both terminals at the repository root.

```sh
git clone https://github.com/motion28/ATS-resume-parser.git
cd ATS-resume-parser
```

### Backend — terminal 1

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create `backend/.env` from [backend/.env.example](backend/.env.example) if it does
not already exist. Replace the key placeholder privately on your machine:

```dotenv
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
ALLOWED_ORIGINS=
```

`GROQ_MODEL` must support Groq's strict structured outputs. `ALLOWED_ORIGINS` adds
comma-separated frontend origins when needed; local origins
`http://localhost:5173` and `http://127.0.0.1:5173` are already allowed.
`python-dotenv` loads `backend/.env`; process environment variables take precedence.

Start the backend from `backend/`:

```sh
python -m uvicorn main:app --reload --port 8000
```

On Windows, activate with `.venv\Scripts\activate`. On subsequent runs, activate
the existing environment and start Uvicorn. Restart it after configuration changes.

### Frontend — terminal 2

```sh
cd frontend
npm ci
npm run dev
```

Open [localhost:5173](http://localhost:5173). The frontend defaults to the backend
at `http://localhost:8000`. For a different backend, create `frontend/.env.local`
using [frontend/.env.example](frontend/.env.example):

```dotenv
VITE_API_BASE_URL=https://your-backend.example.com
```

Restart Vite after editing its environment. This URL is embedded at build time,
so production changes require a new frontend build. **Never put a Groq key in a
`VITE_` variable.** Local `.env` files are gitignored.

## Checks

From `frontend/`, type-check and build:

```sh
npm run build
```

From `backend/`, with the virtual environment active:

```sh
python check_backend.py
```

The backend checks use fictional PDFs and mocked provider responses. They cover
PDF validation, structured extraction, provider errors, model defaults, and CORS
without loading real credentials or making Groq requests.

With the backend running:

```sh
curl http://localhost:8000/api/health
```

Expect `{"status":"ok"}`. Interactive API documentation is at
[localhost:8000/docs](http://localhost:8000/docs).

## Limitations and data handling

- Text-based PDFs only. Scanned or image-only PDFs are unsupported; there is no OCR.
- Complex layouts can affect extracted text order, and AI extraction can make
  mistakes. Always compare results with the original resume.
- Warnings indicate missing extracted information. They are **not an ATS score**
  or a prediction of an employer's hiring system.
- **Extracted resume text is sent to Groq for processing.** The original PDF is
  not sent to Groq. Only upload information you intend to share with that service.
- The application does not intentionally persist resumes or use a database.
  FastAPI may temporarily spool larger uploads to disk; upload cleanup closes
  that temporary storage.

## Deployment

See the [Render deployment guide](docs/deployment.md) for the two free services,
commands, environment variables, and CORS setup. The free backend sleeps after
15 idle minutes and can take about a minute to wake; refresh or retry after startup.
