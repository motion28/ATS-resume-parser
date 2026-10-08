"""Offline checks: python check_backend.py (no real credentials or network)."""
import json
import importlib
import os
from unittest.mock import patch

import groq
import httpx
import pymupdf
from fastapi.testclient import TestClient

# Do not load a real .env during offline verification.
with patch("dotenv.load_dotenv"):
    import extraction
    import main
from models import Education, Experience, ParsedResume

RealGroq = groq.Groq
sample = ParsedResume(
    name="Alex Example", skills=["Python"],
    experience=[Experience(company="Fictional Co", start_date="June 2024", end_date="Present")],
    education=[Education(institution="Fictional University", graduation_date="2022")],
).model_dump()


def completion(content, finish="stop", refusal=None):
    return {"id": "test", "object": "chat.completion", "created": 0, "model": "test",
            "choices": [{"index": 0, "finish_reason": finish,
                         "message": {"role": "assistant", "content": content, "refusal": refusal}}]}


def provider(body, status=200, failure=None):
    def handler(request):
        sent = json.loads(request.content)
        assert sent["model"] == "test-model"
        schema = sent["response_format"]["json_schema"]
        assert schema["strict"] is True
        for obj in [schema["schema"], *schema["schema"]["$defs"].values()]:
            assert obj["additionalProperties"] is False
            assert set(obj["required"]) == set(obj["properties"])
            assert all("default" not in field for field in obj["properties"].values())
        if failure:
            raise failure(request)
        return httpx.Response(status, json=body)

    def create(**kwargs):
        assert kwargs == {"timeout": 30.0, "max_retries": 0}
        return RealGroq(api_key="test-only", http_client=httpx.Client(
            transport=httpx.MockTransport(handler)), **kwargs)
    return patch.object(extraction.groq, "Groq", side_effect=create)


def run():
    with provider(completion(json.dumps(sample))):
        parsed = extraction.extract_resume("Fictional resume text")
        assert parsed.model_dump() == sample
    print("PASS: nested extraction, configurable model, strict schema, timeout and retry settings")

    bad_outputs = [
        completion("not JSON"), completion("{}"), completion(""), completion(None),
        completion(json.dumps(dict(sample, skills="wrong type"))),
        completion(json.dumps(dict(sample, extra="unexpected"))),
        completion(json.dumps(dict(sample, experience=[{"company": "Incomplete"}]))),
        completion("{}", finish="length"), completion(None, refusal="private refusal"),
        completion(None, finish="content_filter"), completion("{}", finish="tool_calls"),
        {"choices": []}, {},
    ]
    for response in bad_outputs:
        with provider(response):
            try:
                extraction.extract_resume("Fictional resume text")
            except extraction.ExtractionError as exc:
                assert exc.status_code in (422, 502)
                assert "private refusal" not in str(exc)
            else:
                raise AssertionError("Bad output was accepted")
    print("PASS: malformed, invalid, incomplete, empty, refused and truncated responses")

    for status, expected in [(400, 502), (401, 503), (403, 503), (429, 429), (500, 502)]:
        with provider({"error": {"message": "PRIVATE_PROVIDER_BODY"}}, status=status):
            try:
                extraction.extract_resume("Fictional resume text")
            except extraction.ExtractionError as exc:
                assert exc.status_code == expected and "PRIVATE_PROVIDER_BODY" not in str(exc)
            else:
                raise AssertionError("Provider error was accepted")
    for error_type, expected in [(httpx.ReadTimeout, 504), (httpx.ConnectError, 502)]:
        with provider(None, failure=lambda req: error_type("PRIVATE", request=req)):
            try:
                extraction.extract_resume("Fictional resume text")
            except extraction.ExtractionError as exc:
                assert exc.status_code == expected and "PRIVATE" not in str(exc)
            else:
                raise AssertionError("Transport failure was accepted")
    print("PASS: provider errors, rate limits, timeout and network failure are sanitized")

    with pymupdf.open() as doc:
        doc.new_page().insert_text((72, 72), "Alex Example\nPython")
        doc.new_page().insert_text((72, 72), "Fictional University")
        pdf = doc.tobytes()
        locked = doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="secret")
    with pymupdf.open() as doc:
        doc.new_page()
        blank = doc.tobytes()
    with TestClient(main.app) as client:
        with provider(completion(json.dumps(sample))):
            response = client.post("/api/parse", files={"file": ("fiction.pdf", pdf, "application/pdf")})
            assert response.status_code == 200
            result = response.json()
            assert set(result) == {"filename", "text", "resume"}
            assert "Fictional University" in result["text"] and result["resume"] == sample
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}), patch.object(extraction.groq, "Groq") as sdk:
            assert client.get("/api/health").json() == {"status": "ok"}
            response = client.post("/api/parse", files={"file": ("fiction.pdf", pdf)})
            assert response.status_code == 503 and "not configured" in response.json()["detail"]
            sdk.assert_not_called()
        with patch.object(main, "extract_resume") as extract:
            for name, data, status in [("bad.txt", pdf, 400), ("bad.pdf", b"fake", 400),
                                       ("empty.pdf", b"", 400), ("locked.pdf", locked, 400),
                                       ("blank.pdf", blank, 422)]:
                assert client.post("/api/parse", files={"file": (name, data)}).status_code == status
            extract.assert_not_called()
        with provider({"error": {"message": "PRIVATE_PROVIDER_BODY"}}, status=429):
            response = client.post("/api/parse", files={"file": ("fiction.pdf", pdf)})
            assert response.status_code == 429 and "PRIVATE_PROVIDER_BODY" not in response.text
    print("PASS: API success, PDF validation, missing configuration, health and safe API errors")

    first, second = ParsedResume(), ParsedResume()
    assert first.name is None and first.skills == []
    first.skills.append("Python")
    first.experience.append(Experience())
    first.education.append(Education())
    assert second.skills == second.experience == second.education == []
    print("PASS: model defaults and independent lists preserved")

    # Reload the app with fictional deployment origins, without loading .env.
    with patch.dict(os.environ, {"ALLOWED_ORIGINS": " https://fictional-site.onrender.com/, https://second.example "}):
        importlib.reload(main)
        with TestClient(main.app) as client:
            for origin in ["http://localhost:5173", "http://127.0.0.1:5173",
                           "https://fictional-site.onrender.com", "https://second.example"]:
                response = client.get("/api/health", headers={"Origin": origin})
                assert response.status_code == 200
                assert response.headers["access-control-allow-origin"] == origin
                preflight = client.options("/api/parse", headers={
                    "Origin": origin, "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                })
                assert preflight.status_code == 200
            response = client.get("/api/health", headers={"Origin": "https://unlisted.example"})
            assert "access-control-allow-origin" not in response.headers
    print("PASS: configured deployment CORS, local origins, upload preflight and unlisted-origin exclusion")


if __name__ == "__main__":
    with patch.dict(os.environ, {"GROQ_API_KEY": "test-only", "GROQ_MODEL": "test-model"}, clear=True):
        run()
