import os

import pymupdf
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from extraction import ExtractionError, extract_resume

app = FastAPI()

# extraction loads backend/.env before these settings are read.
allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
allowed_origins.extend(
    origin.strip().rstrip("/")
    for origin in os.environ.get("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
)

# The browser treats different ports as different origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=[],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/parse")
def parse_resume(file: UploadFile):
    # A regular def lets FastAPI run the blocking PDF work in a worker thread.
    try:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Please upload a PDF file.")

        contents = file.file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="The uploaded PDF is empty.")

        try:
            with pymupdf.open(stream=contents) as document:
                # Check the actual format, not just the filename or browser MIME type.
                if not document.is_pdf:
                    raise HTTPException(status_code=400, detail="Please upload a valid PDF file.")
                if document.needs_pass:
                    raise HTTPException(
                        status_code=400,
                        detail="This PDF is password-protected. Upload an unlocked PDF.",
                    )
                text = "\n".join(page.get_text() for page in document)
        except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
            raise HTTPException(
                status_code=400,
                detail="This file could not be read as a PDF. It may be invalid or damaged.",
            ) from exc

        if not text.strip():
            raise HTTPException(
                status_code=422,
                detail="No readable text was found. Upload a text-based PDF; scanned or image-only PDFs are not supported yet.",
            )

        try:
            resume = extract_resume(text)
        except ExtractionError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None

        return {"filename": file.filename, "text": text, "resume": resume.model_dump()}
    finally:
        file.file.close()
