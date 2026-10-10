"""B2 tests: Application Readiness Engine (backend/app/readiness.py).

All rulebooks used here are SYNTHETIC, test-only fixtures under
backend/tests/rulebooks/ — never official government rules (AGENTS.md: never
invent government rules or mark them verified).

Gemini is never contacted in these tests: an autouse fixture removes
GEMINI_API_KEY, and the live-failure/invalid-output paths are simulated by
monkeypatching ``google.genai.Client``.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import readiness
from app.main import app
from app.matching import compare_documents
from app.schemas import (
    CheckResponse,
    Document,
    DocumentType,
    ExtractedField,
    FindingClassification,
    ReadinessStatus,
)

client = TestClient(app)

FIXTURE_RULEBOOKS = Path(__file__).resolve().parent / "rulebooks" / "services"


@pytest.fixture(autouse=True)
def _test_rulebooks(monkeypatch):
    """Point the engine at synthetic fixtures and disable live Gemini calls."""
    monkeypatch.setattr(readiness, "RULEBOOK_DIR", FIXTURE_RULEBOOKS)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


def _field(name, raw, confidence=0.95):
    return ExtractedField(
        name=name,
        raw_value=raw,
        normalized_value=raw,
        confidence=confidence,
        evidence="test",
    )


def _doc(doc_id, doc_type, fields):
    return Document(id=doc_id, document_type=doc_type, filename=f"{doc_id}.jpg", fields=fields)


def _findings(result, classification):
    return [f for f in result.findings if f.classification == classification]


def _by_field(result):
    return {f.mismatch_field: f for f in result.findings}


def _anita_documents():
    """Anita: surname changed after marriage; marriage certificate uploaded."""
    return [
        _doc("aadhaar", DocumentType.AADHAAR, [_field("full_name", "Anita Sharma")]),
        _doc("bank", DocumentType.BANK_PASSBOOK, [_field("full_name", "Anita Verma")]),
        _doc("marriage", DocumentType.MARRIAGE_CERTIFICATE, [_field("full_name", "Anita Verma")]),
    ]


def _clean_pension_documents_with_father_name_gap():
    """Names consistent; father's name differs — no verified rule covers it."""
    return [
        _doc("aadhaar", DocumentType.AADHAAR, [
            _field("full_name", "Anita Sharma"),
            _field("father_name", "Ramesh Kumar"),
        ]),
        _doc("bank", DocumentType.BANK_PASSBOOK, [
            _field("full_name", "Anita Sharma"),
            _field("father_name", "Ram Kumar"),
        ]),
        _doc("marriage", DocumentType.MARRIAGE_CERTIFICATE, [_field("full_name", "Anita Sharma")]),
    ]


# --------------------------------------------------------------------------- #
# 1. Anita: surname difference after marriage, with marriage certificate
# --------------------------------------------------------------------------- #
def test_anita_surname_change_after_marriage_needs_supporting_doc():
    docs = _anita_documents()
    mismatches = compare_documents(docs)
    result = readiness.check_readiness("old_age_pension", ["marriage"], docs, mismatches)

    assert result.status == ReadinessStatus.NEEDS_DOCUMENTS
    supporting = _findings(result, FindingClassification.NEEDS_SUPPORTING_DOC)
    assert supporting, "expected a supporting-document finding for the name difference"
    assert supporting[0].rule_id == "rule_name_consistency_verified"
    assert "marriage" in supporting[0].reason.lower()          # rule evidence quoted
    assert "example.gov" in supporting[0].reason               # source-linked reasoning
    steps = " ".join(result.next_steps).lower()
    assert "source" in steps


# --------------------------------------------------------------------------- #
# 2. Mismatch without an applicable verified rule -> VERIFY_AT_OFFICE
#    (also proves the PENDING address rule's "blocker" severity never applies)
# --------------------------------------------------------------------------- #
def test_mismatch_without_applicable_verified_rule_is_verify_at_office():
    docs = [
        _doc("aadhaar", DocumentType.AADHAAR, [
            _field("full_name", "Anita Sharma"),
            _field("father_name", "Ramesh Kumar"),
            _field("address", "12 MG Road"),
        ]),
        _doc("bank", DocumentType.BANK_PASSBOOK, [
            _field("full_name", "Anita Sharma"),
            _field("father_name", "Ram Kumar"),
            _field("address", "45 Park Lane"),
        ]),
        _doc("marriage", DocumentType.MARRIAGE_CERTIFICATE, [_field("full_name", "Anita Sharma")]),
    ]
    result = readiness.check_readiness("old_age_pension", [], docs, compare_documents(docs))

    fields = _by_field(result)
    # father_name: no rule at all mentions it.
    assert fields["father_name"].classification == FindingClassification.VERIFY_AT_OFFICE
    assert fields["father_name"].rule_id is None
    # address: only a PENDING (UNVERIFIED) rule mentions it — never applied.
    assert fields["address"].classification == FindingClassification.VERIFY_AT_OFFICE
    assert fields["address"].rule_id is None
    assert result.status == ReadinessStatus.UNVERIFIED
    assert not _findings(result, FindingClassification.LIKELY_BLOCKER)


# --------------------------------------------------------------------------- #
# 3. Pending rule -> never applied, surfaced as an unresolved question
# --------------------------------------------------------------------------- #
def test_pending_rule_is_not_applied():
    docs = [
        _doc("aadhaar", DocumentType.AADHAAR, [_field("full_name", "Suresh Patel")]),
        _doc("pan", DocumentType.PAN, [_field("full_name", "Suresh Patil")]),
    ]
    result = readiness.check_readiness("no_coverage", [], docs, compare_documents(docs))

    assert result.status == ReadinessStatus.UNVERIFIED  # never BLOCKED, never READY
    assert all(f.rule_id != "rule_only_pending" for f in result.findings)
    assert not _findings(result, FindingClassification.LIKELY_BLOCKER)
    assert any("rule_only_pending" in q for q in result.unresolved_questions)


# --------------------------------------------------------------------------- #
# 4. Source conflict -> conflict_note included in unresolved_questions
# --------------------------------------------------------------------------- #
def test_source_conflict_surfaces_unresolved_question():
    result = readiness.check_readiness("old_age_pension", [], [], [])

    conflict_questions = [
        q for q in result.unresolved_questions
        if "rule_source_conflict_verified" in q
    ]
    assert conflict_questions, "expected the source conflict to be raised"
    # The fixture's conflict_note must appear verbatim.
    assert "school marksheet" in conflict_questions[0]
    assert "not certain" in conflict_questions[0].lower()
    assert result.status != ReadinessStatus.READY


# --------------------------------------------------------------------------- #
# 5. Verified requirement for a missing supporting document -> NEEDS_SUPPORTING_DOC
# --------------------------------------------------------------------------- #
def test_verified_missing_supporting_document():
    # PAN only — the verified passport rule requires an aadhaar address proof.
    docs = [_doc("pan", DocumentType.PAN, [_field("full_name", "Vikram Rao")])]
    result = readiness.check_readiness("passport", [], docs, compare_documents(docs))

    assert result.status == ReadinessStatus.NEEDS_DOCUMENTS
    supporting = _findings(result, FindingClassification.NEEDS_SUPPORTING_DOC)
    assert any(f.rule_id == "rule_passport_address" for f in supporting)
    assert any("aadhaar" in f.reason.lower() for f in supporting)
    assert any("example.gov/passport-address" in s for s in result.next_steps)


# --------------------------------------------------------------------------- #
# 6. Gemini failure -> safe VERIFY_AT_OFFICE fallback
# --------------------------------------------------------------------------- #
class _RaisingClient:
    """Simulates a Gemini outage: constructing the client raises."""

    def __init__(self, *args, **kwargs):
        raise RuntimeError("simulated Gemini outage")


def test_gemini_failure_falls_back_to_verify_at_office(monkeypatch):
    from google import genai

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(genai, "Client", _RaisingClient)

    docs = _clean_pension_documents_with_father_name_gap()
    result = readiness.check_readiness("old_age_pension", [], docs, compare_documents(docs))

    father = _by_field(result)["father_name"]
    assert father.classification == FindingClassification.VERIFY_AT_OFFICE
    assert father.rule_id is None
    assert result.status == ReadinessStatus.UNVERIFIED
    assert not _findings(result, FindingClassification.LIKELY_BLOCKER)


# --------------------------------------------------------------------------- #
# 6b. AI output without a valid verified rule_id -> VERIFY_AT_OFFICE
# --------------------------------------------------------------------------- #
class _FakeClient:
    """Returns a plausible-looking but INVENTED rule_id and a blocker verdict."""

    def __init__(self, *args, **kwargs):
        self.models = SimpleNamespace(
            generate_content=lambda **kwargs: SimpleNamespace(
                text='{"rule_id": "rule_invented", "classification": "LIKELY_BLOCKER"}'
            )
        )


def test_ai_classification_without_valid_rule_id_is_verify_at_office(monkeypatch):
    from google import genai

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(genai, "Client", _FakeClient)

    docs = _clean_pension_documents_with_father_name_gap()
    result = readiness.check_readiness("old_age_pension", [], docs, compare_documents(docs))

    father = _by_field(result)["father_name"]
    assert father.classification == FindingClassification.VERIFY_AT_OFFICE
    assert father.rule_id is None
    # The invented LIKELY_BLOCKER must not flip the overall verdict.
    assert not _findings(result, FindingClassification.LIKELY_BLOCKER)
    assert result.status != ReadinessStatus.BLOCKED


# --------------------------------------------------------------------------- #
# 7. No applicable verified coverage -> never READY
# --------------------------------------------------------------------------- #
def test_no_applicable_verified_coverage_is_not_ready():
    result = readiness.check_readiness("no_coverage", [], [], [])
    assert result.status != ReadinessStatus.READY
    assert result.status == ReadinessStatus.UNVERIFIED


def test_missing_rulebook_is_not_ready():
    """A service with no rulebook file must never be reported READY."""
    result = readiness.check_readiness("service_without_rulebook", [], [], [])
    assert result.status == ReadinessStatus.UNVERIFIED
    assert any("No verified readiness rules" in q for q in result.unresolved_questions)


# --------------------------------------------------------------------------- #
# Life-event gating + BLOCKED only via a verified applicable rule
# --------------------------------------------------------------------------- #
def test_life_event_gates_rules_and_blocked_requires_verified_rule():
    docs = [
        _doc("aadhaar", DocumentType.AADHAAR, [_field("address", "12 MG Road")]),
        _doc("pan", DocumentType.PAN, [_field("address", "45 Park Lane")]),
    ]
    mismatches = compare_documents(docs)

    # Without the relocation life event, the gated blocker rule must not apply.
    no_event = readiness.check_readiness("passport", [], docs, mismatches)
    assert no_event.status != ReadinessStatus.BLOCKED

    # With the life event, the verified blocker rule applies deterministically.
    with_event = readiness.check_readiness(
        "passport", ["address_relocation"], docs, mismatches
    )
    blockers = _findings(with_event, FindingClassification.LIKELY_BLOCKER)
    assert blockers and blockers[0].rule_id == "rule_passport_relocation_blocker"
    assert with_event.status == ReadinessStatus.BLOCKED


# --------------------------------------------------------------------------- #
# READY: sufficient verified coverage, no open items, never a guarantee
# --------------------------------------------------------------------------- #
def test_ready_requires_verified_coverage_and_disclaims_approval():
    docs = [
        _doc("aadhaar", DocumentType.AADHAAR, [_field("address", "12 MG Road")]),
        _doc("pan", DocumentType.PAN, [_field("address", "12 MG Road")]),
    ]
    result = readiness.check_readiness("passport", [], docs, compare_documents(docs))

    assert result.status == ReadinessStatus.READY
    assert not result.unresolved_questions
    steps = " ".join(result.next_steps).lower()
    assert "not a guarantee" in steps  # READY never means guaranteed approval


# --------------------------------------------------------------------------- #
# Integration: POST /api/check (USE_MOCK=0) runs the readiness engine
# --------------------------------------------------------------------------- #
def test_live_check_runs_readiness_engine_and_keeps_contract(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "USE_MOCK", False)
    payload = {
        "service_id": "passport",
        "life_events": [],
        "documents": [
            {
                "id": "p1",
                "document_type": "pan",
                "filename": "p1.jpg",
                "fields": [
                    {
                        "name": "full_name",
                        "raw_value": "Vikram Rao",
                        "normalized_value": "Vikram Rao",
                        "evidence": "test",
                    }
                ],
            }
        ],
    }
    response = client.post("/api/check", json=payload)
    assert response.status_code == 200

    # The existing CheckResponse contract is preserved.
    result = CheckResponse.model_validate(response.json())
    assert result.readiness.service_id == "passport"
    assert result.readiness.status == ReadinessStatus.NEEDS_DOCUMENTS
    assert any(
        f.rule_id == "rule_passport_address" for f in result.readiness.findings
    )
    assert isinstance(result.correction_path_dot, str)
    assert any(s.operation == "check_readiness" for s in result.trace)


def test_mock_check_still_serves_fixture_without_api_key(monkeypatch):
    """USE_MOCK=1 keeps working with no Gemini key (contract regression)."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.post(
        "/api/check",
        json={"service_id": "old_age_pension", "life_events": [], "documents": []},
    )
    assert response.status_code == 200
    result = CheckResponse.model_validate(response.json())
    assert result.readiness.status in {
        ReadinessStatus.NEEDS_DOCUMENTS,
        ReadinessStatus.UNVERIFIED,
    }


