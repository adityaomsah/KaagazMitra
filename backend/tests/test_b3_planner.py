"""B3 tests: Correction Path Planner (backend/app/planner.py).

All correction rulebooks used here are SYNTHETIC, test-only fixtures under
backend/tests/rulebooks/corrections/ — never official government rules
(AGENTS.md: never invent government rules or correction procedures).

Gemini is never contacted: an autouse fixture removes GEMINI_API_KEY.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import planner
from app import readiness as readiness_module
from app.main import app
from app.schemas import (
    CheckResponse,
    CorrectionStep,
    Finding,
    FindingClassification,
    ReadinessResult,
    ReadinessStatus,
)

client = TestClient(app)

FIXTURE_DIR = Path(__file__).resolve().parent / "rulebooks" / "corrections"
SERVICE_RULEBOOKS = Path(__file__).resolve().parent / "rulebooks" / "services"


@pytest.fixture(autouse=True)
def _test_rulebooks(monkeypatch):
    """Point planner + readiness at synthetic fixtures; no live Gemini."""
    monkeypatch.setattr(planner, "CORRECTION_RULEBOOK_PATH", FIXTURE_DIR / "chain2.json")
    monkeypatch.setattr(readiness_module, "RULEBOOK_DIR", SERVICE_RULEBOOKS)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


def _readiness(field="name", classification=FindingClassification.LIKELY_BLOCKER):
    """A minimal readiness result with one synthetic finding."""
    return ReadinessResult(
        service_id="test_service",
        status=ReadinessStatus.UNVERIFIED,
        findings=[
            Finding(
                mismatch_field=field,
                classification=classification,
                reason="synthetic test finding",
            )
        ],
    )


# --------------------------------------------------------------------------- #
# A. Verified 2-step dependency chain is ordered correctly
# --------------------------------------------------------------------------- #
def test_two_step_chain_is_ordered_correctly():
    rules = planner.load_correction_rules()  # autouse -> chain2.json
    steps = planner.plan_corrections(_readiness(), rules)

    assert [s.rule_id for s in steps] == [
        "corr_obtain_primary_proof",
        "corr_update_bank_record",
    ]
    assert [s.order for s in steps] == [1, 2]
    # The prerequisite appears before the dependent step.
    assert steps[1].depends_on == ["corr_obtain_primary_proof"]
    assert steps[0].depends_on == []
    assert all(s.order_unknown is False and s.is_deadlock is False for s in steps)
    # Plain-language action + authority + proof from the verified rule.
    assert steps[0].authority == "Office that issued the primary proof"
    assert "primary name proof" in steps[0].proof_needed.lower()


# --------------------------------------------------------------------------- #
# B. Verified 3-step dependency chain is ordered correctly
# --------------------------------------------------------------------------- #
def test_three_step_chain_is_ordered_correctly(monkeypatch):
    monkeypatch.setattr(planner, "CORRECTION_RULEBOOK_PATH", FIXTURE_DIR / "chain3.json")
    # The rulebook lists the rules out of order; dependencies must win.
    rules = planner.load_correction_rules()
    steps = planner.plan_corrections(_readiness(), rules)

    assert [s.rule_id for s in steps] == [
        "corr_first_obtain_proof",
        "corr_second_update_record",
        "corr_third_update_record",
    ]
    assert [s.order for s in steps] == [1, 2, 3]
    assert steps[1].depends_on == ["corr_first_obtain_proof"]
    assert steps[2].depends_on == ["corr_second_update_record"]


# --------------------------------------------------------------------------- #
# C. A 2-rule cycle is detected and marked order_unknown
# --------------------------------------------------------------------------- #
def test_two_rule_cycle_is_detected_and_marked(monkeypatch):
    monkeypatch.setattr(planner, "CORRECTION_RULEBOOK_PATH", FIXTURE_DIR / "cycle2.json")
    rules = planner.load_correction_rules()
    steps = planner.plan_corrections(_readiness(), rules)

    assert {s.rule_id for s in steps} == {"corr_cycle_alpha", "corr_cycle_beta"}
    # Both mutually-dependent steps are flagged, and never silently resolved.
    assert all(s.order_unknown is True for s in steps)
    assert all(s.is_deadlock is True for s in steps)
    # Orders stay deterministic and unique even when the order is unknown.
    assert sorted(s.order for s in steps) == [1, 2]
    # The exact user-facing message required by the spec.
    assert planner.CYCLE_MESSAGE == (
        "These steps depend on each other. Ask the issuing office which to do first."
    )


# --------------------------------------------------------------------------- #
# D. Pending correction rules are not applied
# --------------------------------------------------------------------------- #
def test_pending_rule_is_never_applied(monkeypatch):
    monkeypatch.setattr(
        planner, "CORRECTION_RULEBOOK_PATH", FIXTURE_DIR / "pending_missing.json"
    )
    steps = planner.plan_corrections(_readiness(), planner.load_correction_rules())

    ids = [s.rule_id for s in steps]
    assert "corr_pending_update" not in ids
    # The pending rule's synthetic instruction never leaks into any action.
    assert all("PENDING" not in s.action for s in steps)


# --------------------------------------------------------------------------- #
# E. Missing dependencies never become invented instructions
# --------------------------------------------------------------------------- #
def test_missing_dependencies_are_dropped_not_invented(monkeypatch):
    monkeypatch.setattr(
        planner, "CORRECTION_RULEBOOK_PATH", FIXTURE_DIR / "pending_missing.json"
    )
    steps = planner.plan_corrections(_readiness(), planner.load_correction_rules())

    ids = [s.rule_id for s in steps]
    assert ids == ["corr_verified_with_missing_dep"]
    # Neither the undefined nor the pending dependency becomes a step...
    assert "corr_never_defined" not in ids
    assert "corr_pending_update" not in ids
    # ...and the unavailable dependency ids are removed from depends_on.
    assert steps[0].depends_on == []


# --------------------------------------------------------------------------- #
# F. No matching verified rules -> no fabricated correction plan
# --------------------------------------------------------------------------- #
def test_no_matching_rules_produces_empty_plan():
    rules = planner.load_correction_rules()  # fixes full_name only

    # Finding on an unrelated field.
    assert planner.plan_corrections(_readiness(field="date_of_birth"), rules) == []
    # No rules at all.
    assert planner.plan_corrections(_readiness(), []) == []
    # Non-actionable findings never drive a plan.
    assert (
        planner.plan_corrections(
            _readiness(classification=FindingClassification.VERIFY_AT_OFFICE), rules
        )
        == []
    )


def test_missing_rulebook_produces_empty_plan(monkeypatch):
    monkeypatch.setattr(
        planner, "CORRECTION_RULEBOOK_PATH", FIXTURE_DIR / "no_such_file.json"
    )
    assert planner.load_correction_rules() == []
    assert planner.plan_corrections(_readiness(), planner.load_correction_rules()) == []


# --------------------------------------------------------------------------- #
# DOT rendering safety
# --------------------------------------------------------------------------- #
def test_dot_escapes_rule_text():
    steps = [
        CorrectionStep(
            order=1,
            rule_id='corr_quoted"rule',
            action='Say "done" \\ then\ncontinue',
            proof_needed="synthetic",
        )
    ]
    dot = planner.render_correction_dot(steps)
    assert '\\"done\\"' in dot                      # quotes escaped
    assert 'corr_quoted\\"rule' in dot              # rule id escaped
    assert "\\\\" in dot                            # backslash escaped
    assert "then continue" in dot                   # newline flattened to a space
    assert dot.startswith("digraph correction_path {")


def test_dot_empty_plan_matches_historical_output():
    assert planner.render_correction_dot([]) == "digraph correction_path {\n}\n"


# --------------------------------------------------------------------------- #
# G. POST /api/check returns a valid correction_path and correction_path_dot
# --------------------------------------------------------------------------- #
def _anita_payload():
    def doc(doc_id, doc_type, name):
        return {
            "id": doc_id,
            "document_type": doc_type,
            "filename": f"{doc_id}.jpg",
            "fields": [
                {
                    "name": "full_name",
                    "raw_value": name,
                    "normalized_value": name,
                    "evidence": "test",
                }
            ],
        }

    return {
        "service_id": "old_age_pension",
        "life_events": ["marriage"],
        "documents": [
            doc("aadhaar", "aadhaar", "Anita Sharma"),
            doc("bank", "bank_passbook", "Anita Verma"),
            doc("marriage", "marriage_certificate", "Anita Verma"),
        ],
    }


def test_live_check_returns_correction_path_and_dot(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "USE_MOCK", False)
    response = client.post("/api/check", json=_anita_payload())
    assert response.status_code == 200

    # Valid CheckResponse with the existing contract fields intact.
    result = CheckResponse.model_validate(response.json())
    assert result.readiness.service_id == "old_age_pension"
    assert [s.rule_id for s in result.correction_path] == [
        "corr_obtain_primary_proof",
        "corr_update_bank_record",
    ]
    assert [s.order for s in result.correction_path] == [1, 2]
    assert result.correction_path_dot.startswith("digraph correction_path {")
    assert "corr_obtain_primary_proof" in result.correction_path_dot
    assert "https://example.gov/corr-primary" in result.sources
    # TraceStep records planning duration without any personal values.
    operations = {t.operation for t in result.trace}
    assert {"compare_documents", "check_readiness", "plan_corrections"} <= operations


def test_live_check_surfaces_cycle_message_exactly(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "USE_MOCK", False)
    monkeypatch.setattr(
        planner, "CORRECTION_RULEBOOK_PATH", FIXTURE_DIR / "cycle2.json"
    )
    response = client.post("/api/check", json=_anita_payload())
    assert response.status_code == 200

    result = CheckResponse.model_validate(response.json())
    assert result.correction_path and all(s.order_unknown for s in result.correction_path)
    assert planner.CYCLE_MESSAGE in result.readiness.unresolved_questions


# --------------------------------------------------------------------------- #
# H. Mock mode continues working (no Gemini, no key)
# --------------------------------------------------------------------------- #
def test_mock_check_still_works_without_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.post(
        "/api/check",
        json={"service_id": "old_age_pension", "life_events": [], "documents": []},
    )
    assert response.status_code == 200

    result = CheckResponse.model_validate(response.json())
    # The B0 mock correction plan survives B3 untouched.
    assert result.correction_path, "mock fixture correction plan must survive"
    assert result.correction_path_dot
    assert result.readiness.status in {
        ReadinessStatus.NEEDS_DOCUMENTS,
        ReadinessStatus.UNVERIFIED,
    }


