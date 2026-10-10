"""KaagazMitra FastAPI application.

Endpoints are documented in docs/API_CONTRACT.md and mirror the Pydantic models
in app/schemas.py (the source of truth).

Current milestone: every endpoint returns data from backend/mock/*.json so the
full flow works with USE_MOCK=1 and no Gemini access. Gemini Vision extraction
and RapidFuzz comparison will replace these fixtures in later milestones.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .extraction import extract_document as run_extraction
from .matching import compare_documents
from .planner import (
    CYCLE_MESSAGE,
    collect_sources,
    load_correction_rules,
    plan_corrections,
    render_correction_dot,
)
from .readiness import check_readiness
from .schemas import (
    CheckRequest,
    CheckResponse,
    CorrectionRule,
    DecodeRejectionRequest,
    DecodeRejectionResponse,
    Document,
    DocumentType,
    Mismatch,
    ReportRequest,
    ReportResponse,
    ServiceRule,
    TraceStep,
    TranslateRequest,
    TranslateResponse,
)

# Load environment variables from backend/.env if present.
load_dotenv()

USE_MOCK = os.getenv("USE_MOCK", "1") == "1"
MOCK_DIR = Path(__file__).resolve().parent.parent / "mock"

app = FastAPI(title="KaagazMitra API", version="0.1.0")

# The Vite dev server proxies /api -> localhost:8000, but allow CORS too so the
# API can be called directly during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_mock(filename: str):
    """Load and parse a JSON fixture from the mock directory."""
    path = MOCK_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=500, detail=f"Missing mock fixture: {filename}")
    return json.loads(path.read_text(encoding="utf-8"))


class _Timer:
    """Context manager that records a non-sensitive operation + its duration.

    Only the operation name and elapsed milliseconds are captured — never any
    document contents or personal data.
    """

    def __init__(self, operation: str, trace: List[TraceStep]):
        self.operation = operation
        self.trace = trace
        self._start = 0.0

    def __enter__(self) -> "_Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc: object) -> None:
        duration_ms = (time.perf_counter() - self._start) * 1000.0
        self.trace.append(TraceStep(operation=self.operation, duration_ms=round(duration_ms, 2)))


@app.get("/api/health")
def health() -> dict:
    """Simple liveness probe used by the frontend connection banner."""
    return {
        "status": "ok",
        "version": app.version,
        "use_mock": USE_MOCK,
    }


@app.get("/api/services", response_model=List[ServiceRule])
def list_services() -> List[ServiceRule]:
    """List the verified service rules (the rulebook)."""
    return [ServiceRule.model_validate(item) for item in load_mock("services.json")]


@app.get("/api/services/{rule_id}", response_model=ServiceRule)
def get_service(rule_id: str) -> ServiceRule:
    """Fetch a single service rule by id."""
    for item in load_mock("services.json"):
        if item["rule_id"] == rule_id:
            return ServiceRule.model_validate(item)
    raise HTTPException(status_code=404, detail=f"Service rule not found: {rule_id}")


@app.get("/api/correction-rules", response_model=List[CorrectionRule])
def list_correction_rules() -> List[CorrectionRule]:
    """List the verified correction rules (how to fix mismatches)."""
    return [CorrectionRule.model_validate(item) for item in load_mock("correction_rules.json")]


@app.get("/api/correction-rules/{rule_id}", response_model=CorrectionRule)
def get_correction_rule(rule_id: str) -> CorrectionRule:
    """Fetch a single correction rule by id."""
    for item in load_mock("correction_rules.json"):
        if item["rule_id"] == rule_id:
            return CorrectionRule.model_validate(item)
    raise HTTPException(status_code=404, detail=f"Correction rule not found: {rule_id}")


@app.get("/api/documents", response_model=List[Document])
def list_documents() -> List[Document]:
    """Return the demo (Rahim) documents currently loaded."""
    return [Document.model_validate(item) for item in load_mock("documents.json")["documents"]]


@app.get("/api/mismatches", response_model=List[Mismatch])
def list_mismatches() -> List[Mismatch]:
    """Return the mismatches detected across the demo documents."""
    return [Mismatch.model_validate(item) for item in load_mock("check_response.json")["mismatches"]]


@app.post("/api/extract", response_model=Document)
async def extract_document(
    file: UploadFile = File(...),
    document_type: Optional[DocumentType] = Form(None),
    consent: Optional[bool] = Form(None),
) -> Document:
    """Extract fields from an uploaded document image.

    Multipart inputs: ``file`` (the image), optional ``document_type`` and a
    required ``consent`` flag. Per AGENTS.md we must obtain consent before
    sending images to cloud AI, so a missing or false consent is rejected.

    With USE_MOCK=1 this returns a fixed demo document so the flow works without
    Gemini. The file is never stored permanently (privacy rules in AGENTS.md).
    """
    if consent is not True:
        raise HTTPException(
            status_code=400,
            detail="Consent is required before sending images to cloud AI.",
        )
    if USE_MOCK:
        doc = Document.model_validate(load_mock("extract_response.json"))
        if document_type is not None:
            doc.document_type = document_type
        return doc
    # Live mode: real Gemini Vision extraction. The image bytes are read into
    # memory only and never written to disk (privacy rules in AGENTS.md).
    image_bytes = await file.read()
    return run_extraction(image_bytes, document_type, file.filename or "upload")


@app.post("/api/check", response_model=CheckResponse)
def check(request: CheckRequest) -> CheckResponse:
    """Run the document-consistency and application-readiness check.

    With USE_MOCK=1 this returns the prepared Rahim scenario regardless of the
    request body; the body is still validated against CheckRequest.

    With USE_MOCK=0 this runs the real deterministic comparison
    (``compare_documents``) over the submitted documents, then the B2 readiness
    engine (``check_readiness``) and the B3 correction planner
    (``plan_corrections``) against the versioned rulebooks, recording
    non-sensitive trace steps for each operation.
    """
    if USE_MOCK:
        return CheckResponse.model_validate(load_mock("check_response.json"))

    trace: List[TraceStep] = []
    with _Timer("compare_documents", trace):
        mismatches = compare_documents(request.documents)

    # B2: evaluate readiness against verified, source-linked rules only.
    # Missing/pending rulebooks stay UNVERIFIED rather than guessing a verdict.
    with _Timer("check_readiness", trace):
        readiness = check_readiness(
            service_id=request.service_id,
            life_events=request.life_events,
            documents=request.documents,
            mismatches=mismatches,
        )

    # B3: plan corrections from verified correction rules only. Dependency
    # cycles are surfaced as unresolved ordering questions, never resolved
    # silently; missing/pending rules never produce steps.
    with _Timer("plan_corrections", trace):
        correction_rules = load_correction_rules()
        correction_path = plan_corrections(readiness, correction_rules)
        if any(step.order_unknown for step in correction_path):
            if CYCLE_MESSAGE not in readiness.unresolved_questions:
                readiness.unresolved_questions.append(CYCLE_MESSAGE)
        sources = collect_sources(correction_path, correction_rules)
        correction_path_dot = render_correction_dot(correction_path)

    return CheckResponse(
        mismatches=mismatches,
        readiness=readiness,
        correction_path=correction_path,
        correction_path_dot=correction_path_dot,
        sources=sources,
        trace=trace,
    )


@app.post("/api/decode-rejection", response_model=DecodeRejectionResponse)
def decode_rejection(request: DecodeRejectionRequest) -> DecodeRejectionResponse:
    """Explain an application rejection reason in plain language.

    With USE_MOCK=1 this returns a synthetic explanation derived from the
    Rahim scenario. No real rules are invented; guidance stays generic.
    """
    if USE_MOCK:
        return DecodeRejectionResponse(
            plain_language=(
                "Your application was returned because the name on your bank "
                "account did not exactly match the name on your Aadhaar."
            ),
            category="name_mismatch",
            possible_reasons=[
                "Bank passbook shows 'Md Rahim Khan' while Aadhaar shows 'Rahim Khan'.",
                "A middle name or prefix was added on one document but not another.",
            ],
            suggested_next_steps=[
                "Carry a bank letter linking both spellings of your name.",
                "Ask the office whether a one-and-the-same affidavit is accepted.",
            ],
        )
    raise HTTPException(status_code=501, detail="Live rejection decoding is not implemented yet.")


@app.post("/api/translate", response_model=TranslateResponse)
def translate(request: TranslateRequest) -> TranslateResponse:
    """Translate guidance text into a target language.

    With USE_MOCK=1 this echoes the text with a clearly-marked placeholder so the
    flow works without a live translation service.
    """
    if USE_MOCK:
        return TranslateResponse(
            source_text=request.text,
            translated_text=f"[mock-{request.target_language}] {request.text}",
            target_language=request.target_language,
        )
    raise HTTPException(status_code=501, detail="Live translation is not implemented yet.")


@app.post("/api/report", response_model=ReportResponse)
def report(request: ReportRequest) -> ReportResponse:
    """Generate a shareable, plain-language readiness report.

    With USE_MOCK=1 this returns a synthetic summary built from the Rahim
    scenario check result.
    """
    if USE_MOCK:
        check_data = load_mock("check_response.json")
        readiness = check_data["readiness"]
        return ReportResponse(
            service_id=request.service_id,
            summary=(
                f"Your {request.service_id} application is not ready yet. "
                "There is a name difference across your documents that should be "
                "resolved or explained before you apply."
            ),
            key_findings=[
                f"Readiness status: {readiness['status']}.",
                "The name is spelled differently on your Aadhaar, PAN, bank "
                "passbook and marksheet.",
            ],
            next_steps=readiness.get("next_steps", []),
        )
    raise HTTPException(status_code=501, detail="Live report generation is not implemented yet.")
