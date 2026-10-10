"""B1 tests: deterministic matching (cases A-F) and Gemini extraction safety.

These use synthetic documents only — no real identity documents. Gemini is never
called here: failures are simulated by monkeypatching, and mock mode is verified
to work without any API key.
"""

from unittest import mock

import pytest
from fastapi.testclient import TestClient

from app.extraction import extract_document
from app.main import app
from app.matching import compare_documents, normalize_dob, normalize_for_compare
from app.schemas import Document, DocumentType, ExtractedField, MismatchStatus

client = TestClient(app)


def _field(name, raw, confidence=0.95, transliteration=None, needs_confirmation=False):
    return ExtractedField(
        name=name,
        raw_value=raw,
        normalized_value=raw,
        confidence=confidence,
        transliterated_value=transliteration,
        needs_confirmation=needs_confirmation,
        evidence="test",
    )


def _doc(doc_id, doc_type, fields):
    return Document(id=doc_id, document_type=doc_type, filename=doc_id, fields=fields)


def _status_for(documents, field):
    matches = {m.field: m for m in compare_documents(documents)}
    return matches.get(field)


# --------------------------------------------------------------------------- #
# A-F: required comparison cases
# --------------------------------------------------------------------------- #
def test_a_identical_fields_match():
    docs = [
        _doc("d1", DocumentType.AADHAAR, [_field("full_name", "Meera Sharma"), _field("date_of_birth", "12/04/1998")]),
        _doc("d2", DocumentType.PAN, [_field("full_name", "Meera Sharma"), _field("date_of_birth", "12/04/1998")]),
    ]
    assert _status_for(docs, "name").status == MismatchStatus.MATCH
    assert _status_for(docs, "date_of_birth").status == MismatchStatus.MATCH


def test_b_surname_difference():
    docs = [
        _doc("d1", DocumentType.AADHAAR, [_field("full_name", "Meera Sharma")]),
        _doc("d2", DocumentType.PAN, [_field("full_name", "Meera Verma")]),
    ]
    mismatch = _status_for(docs, "name")
    assert mismatch.status == MismatchStatus.DIFFERENCE
    # Original values are preserved unchanged.
    assert mismatch.values == {"d1": "Meera Sharma", "d2": "Meera Verma"}


def test_c_dob_one_day_difference():
    docs = [
        _doc("d1", DocumentType.AADHAAR, [_field("date_of_birth", "12/04/1998")]),
        _doc("d2", DocumentType.PAN, [_field("date_of_birth", "13/04/1998")]),
    ]
    assert _status_for(docs, "date_of_birth").status == MismatchStatus.DIFFERENCE


def test_d_mohd_versus_mohammad_possible_variant():
    docs = [
        _doc("d1", DocumentType.AADHAAR, [_field("full_name", "Mohd. Rahim")]),
        _doc("d2", DocumentType.PAN, [_field("full_name", "Mohammad Rahim")]),
    ]
    mismatch = _status_for(docs, "name")
    assert mismatch.status == MismatchStatus.POSSIBLE_VARIANT
    assert mismatch.differences_explained, "expected an explanatory note"
    joined = " ".join(mismatch.differences_explained).lower()
    assert "abbrev" in joined or "honorific" in joined


def test_e_unreadable_dob_is_unknown():
    docs = [
        _doc("d1", DocumentType.AADHAAR, [_field("date_of_birth", "12/04/1998")]),
        _doc("d2", DocumentType.PAN, [_field("date_of_birth", "", confidence=0.2, needs_confirmation=True)]),
    ]
    mismatch = _status_for(docs, "date_of_birth")
    assert mismatch.status == MismatchStatus.UNKNOWN


def test_f_devanagari_versus_latin_possible_variant():
    docs = [
        _doc("d1", DocumentType.AADHAAR, [_field("full_name", "रमेश कुमार", transliteration="Ramesh Kumar")]),
        _doc("d2", DocumentType.PAN, [_field("full_name", "Ramesh Kumar")]),
    ]
    mismatch = _status_for(docs, "name")
    assert mismatch.status == MismatchStatus.POSSIBLE_VARIANT
    joined = " ".join(mismatch.differences_explained).lower()
    assert "transliter" in joined, "expected a transliteration/script explanation"


# --------------------------------------------------------------------------- #
# Normalisation helpers
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "value,expected",
    [
        ("12/04/1998", "1998-04-12"),
        ("12-04-1998", "1998-04-12"),
        ("12.04.1998", "1998-04-12"),
        ("1998-04-12", "1998-04-12"),
    ],
)
def test_normalize_dob_supported_formats(value, expected):
    assert normalize_dob(value) == expected


def test_normalize_dob_ambiguous_returns_none():
    # Not a recognised, unambiguous format -> must not guess.
    assert normalize_dob("sometime in April") is None
    assert normalize_dob("") is None


def test_normalize_for_compare_collapses_and_strips():
    assert normalize_for_compare("  Meera,  SHARMA!! ") == "meera sharma"


# --------------------------------------------------------------------------- #
# Extraction safety: failures degrade, nothing is invented
# --------------------------------------------------------------------------- #
def test_extraction_gemini_failure_is_review_required(monkeypatch):
    """A Gemini API error must not crash; fields become review-required."""
    import app.extraction as extraction

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(extraction, "_get_model", lambda: "gemini-test")

    with mock.patch("google.genai.Client") as client_cls:
        client_cls.return_value.models.generate_content.side_effect = RuntimeError("boom")
        doc = extract_document(b"fake-image-bytes", DocumentType.AADHAAR, "aadhaar.jpg")

    assert isinstance(doc, Document)
    assert doc.fields, "expected fields to be present for review"
    assert all(f.needs_confirmation for f in doc.fields), "all fields must need confirmation"
    assert all(f.raw_value == "" for f in doc.fields), "nothing may be invented"


def test_extraction_malformed_json_is_review_required():
    """Malformed model output degrades to review-required, never crashes."""
    from app import extraction
    doc = extraction._parse_response("not-json{{{", DocumentType.AADHAAR, "bad.jpg")
    assert isinstance(doc, Document)
    assert all(f.needs_confirmation for f in doc.fields)


def test_extraction_without_api_key_returns_review_required(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    doc = extract_document(b"bytes", DocumentType.PAN, "pan.jpg")
    assert all(f.needs_confirmation for f in doc.fields)
    assert all(f.raw_value == "" for f in doc.fields)


def test_extraction_valid_json_preserves_raw_and_transliteration():
    from app import extraction
    payload = (
        '{"fields": {"name": {"raw_value": "रमेश कुमार", "transliteration": '
        '"Ramesh Kumar", "confidence": 0.93, "evidence": "top"}, '
        '"date_of_birth": {"raw_value": "12/04/1998", "confidence": 0.9, "evidence": "mid"}}}'
    )
    doc = extraction._parse_response(payload, DocumentType.AADHAAR, "a.jpg")
    name = next(f for f in doc.fields if f.name == "name")
    assert name.raw_value == "रमेश कुमार"          # original script preserved
    assert name.transliterated_value == "Ramesh Kumar"
    assert name.needs_confirmation is False         # 0.93 >= 0.7
    dob = next(f for f in doc.fields if f.name == "date_of_birth")
    assert dob.needs_confirmation is False


def test_extraction_low_confidence_flagged():
    from app import extraction
    payload = '{"fields": {"name": {"raw_value": "Meera", "confidence": 0.4, "evidence": "x"}}}'
    doc = extraction._parse_response(payload, DocumentType.AADHAAR, "a.jpg")
    name = next(f for f in doc.fields if f.name == "name")
    assert name.needs_confirmation is True  # 0.4 < 0.7


# --------------------------------------------------------------------------- #
# API integration: mock mode, consent, and B0 regression
# --------------------------------------------------------------------------- #
def test_mock_check_still_works_without_api_key(monkeypatch):
    """USE_MOCK=1 path must not require a Gemini key."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.post(
        "/api/check",
        json={"service_id": "old_age_pension", "life_events": [], "documents": []},
    )
    assert response.status_code == 200
    assert response.json()["readiness"]["status"] in {"NEEDS_DOCUMENTS", "UNVERIFIED"}


def test_extract_consent_still_enforced():
    response = client.post(
        "/api/extract",
        files={"file": ("a.jpg", b"bytes", "image/jpeg")},
        data={"consent": "false"},
    )
    assert response.status_code == 400


def test_extract_mock_with_consent_returns_document():
    response = client.post(
        "/api/extract",
        files={"file": ("a.jpg", b"bytes", "image/jpeg")},
        data={"consent": "true", "document_type": "aadhaar"},
    )
    assert response.status_code == 200
    Document.model_validate(response.json())


def test_extract_live_mode_calls_extraction_module(monkeypatch):
    """Live mode (USE_MOCK=0) must call the extraction module, not recurse.

    Guards against the route handler shadowing the imported extract function.
    """
    import app.main as main

    captured = {}

    def fake_extract(image_bytes, document_type, filename):
        captured["called"] = True
        return _doc("live1", DocumentType.AADHAAR, [_field("full_name", "Synthetic Name")])

    # Flip to live mode and stub the extraction call.
    monkeypatch.setattr(main, "USE_MOCK", False)
    monkeypatch.setattr(main, "run_extraction", fake_extract)

    response = client.post(
        "/api/extract",
        files={"file": ("a.jpg", b"bytes", "image/jpeg")},
        data={"consent": "true", "document_type": "aadhaar"},
    )
    assert response.status_code == 200
    assert captured.get("called") is True
    doc = Document.model_validate(response.json())
    assert doc.id == "live1"
