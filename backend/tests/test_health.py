"""Tests for the KaagazMitra B0 API contract.

Verifies that the agreed endpoints are registered with the correct methods,
appear in the OpenAPI schema (so they show in /docs), and return valid mock
responses using the fixtures (USE_MOCK=1) — no Gemini required.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import (
    CheckResponse,
    DecodeRejectionResponse,
    Document,
    ReportResponse,
    ServiceRule,
    TranslateResponse,
)

client = TestClient(app)

# The agreed B0 contract: (method, path).
EXPECTED_ROUTES = [
    ("get", "/api/health"),
    ("get", "/api/services"),
    ("post", "/api/extract"),
    ("post", "/api/check"),
    ("post", "/api/decode-rejection"),
    ("post", "/api/translate"),
    ("post", "/api/report"),
]


def _registered():
    """Return the set of (METHOD, path) registered in the OpenAPI schema."""
    paths = app.openapi()["paths"]
    return {(method.upper(), path) for path, ops in paths.items() for method in ops}


def test_openapi_registers_all_b0_endpoints():
    registered = _registered()
    for method, path in EXPECTED_ROUTES:
        assert (method.upper(), path) in registered, f"Missing {method.upper()} {path}"


def test_openapi_json_is_served():
    """The /openapi.json document must expose every B0 endpoint (drives /docs)."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for _method, path in EXPECTED_ROUTES:
        assert path in paths, f"{path} missing from /openapi.json"


def test_health_returns_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_services_returns_valid_schema():
    response = client.get("/api/services")
    assert response.status_code == 200
    rules = [ServiceRule.model_validate(item) for item in response.json()]
    assert rules, "expected at least one service rule"


def test_check_returns_valid_schema():
    payload = {
        "service_id": "old_age_pension",
        "life_events": ["retirement"],
        "documents": [],
    }
    response = client.post("/api/check", json=payload)
    assert response.status_code == 200

    # Validate the response against the source-of-truth Pydantic model.
    result = CheckResponse.model_validate(response.json())

    assert result.readiness.status is not None
    assert result.readiness.service_id == "old_age_pension"
    assert isinstance(result.correction_path_dot, str) and result.correction_path_dot
    # The Rahim scenario ships a possible name variant.
    assert any(m.field == "full_name" for m in result.mismatches)


def test_extract_requires_consent():
    """Missing consent must be rejected (AGENTS.md: consent before cloud AI)."""
    response = client.post(
        "/api/extract",
        files={"file": ("aadhaar.jpg", b"fake-bytes", "image/jpeg")},
        data={"consent": "false"},
    )
    assert response.status_code == 400


def test_extract_with_consent_returns_document():
    response = client.post(
        "/api/extract",
        files={"file": ("aadhaar.jpg", b"fake-bytes", "image/jpeg")},
        data={"consent": "true", "document_type": "aadhaar"},
    )
    assert response.status_code == 200
    doc = Document.model_validate(response.json())
    assert doc.document_type.value == "aadhaar"
    assert doc.fields, "expected extracted fields"


def test_decode_rejection_returns_valid_schema():
    payload = {
        "rejection_text": "Name mismatch with bank account",
        "language": "en",
    }
    response = client.post("/api/decode-rejection", json=payload)
    assert response.status_code == 200
    result = DecodeRejectionResponse.model_validate(response.json())
    assert result.plain_language
    assert result.category


def test_translate_returns_valid_schema():
    payload = {"text": "Your application is ready.", "target_language": "hi"}
    response = client.post("/api/translate", json=payload)
    assert response.status_code == 200
    result = TranslateResponse.model_validate(response.json())
    assert result.source_text == payload["text"]
    assert result.target_language == "hi"
    assert result.translated_text


def test_report_returns_valid_schema():
    payload = {"service_id": "old_age_pension", "check": None}
    response = client.post("/api/report", json=payload)
    assert response.status_code == 200
    result = ReportResponse.model_validate(response.json())
    assert result.service_id == "old_age_pension"
    assert result.summary

