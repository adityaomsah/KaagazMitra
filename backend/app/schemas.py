"""Pydantic schemas for KaagazMitra.

This module is the single source of truth for the API contract.
The frontend types in ``src/types/api.ts`` must mirror these models exactly.

Privacy/safety notes (per AGENTS.md):
- Extracted values are preserved verbatim in ``raw_value``; original names and
  scripts are never rewritten or stripped.
- ``confidence`` is an estimate, never verified certainty.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Supported identity/official document categories."""

    AADHAAR = "aadhaar"
    PAN = "pan"
    BANK_PASSBOOK = "bank_passbook"
    CLASS10_MARKSHEET = "class10_marksheet"
    MARRIAGE_CERTIFICATE = "marriage_certificate"
    OTHER = "other"


class MismatchStatus(str, Enum):
    """Outcome of comparing a single field across documents."""

    MATCH = "MATCH"
    DIFFERENCE = "DIFFERENCE"
    POSSIBLE_VARIANT = "POSSIBLE_VARIANT"
    UNKNOWN = "UNKNOWN"


class FindingClassification(str, Enum):
    """How a mismatch affects readiness for a chosen service."""

    NOT_RELEVANT = "NOT_RELEVANT"
    NEEDS_SUPPORTING_DOC = "NEEDS_SUPPORTING_DOC"
    LIKELY_BLOCKER = "LIKELY_BLOCKER"
    VERIFY_AT_OFFICE = "VERIFY_AT_OFFICE"


class ReadinessStatus(str, Enum):
    """Overall readiness verdict for a service."""

    READY = "READY"
    NEEDS_DOCUMENTS = "NEEDS_DOCUMENTS"
    BLOCKED = "BLOCKED"
    UNVERIFIED = "UNVERIFIED"


class VerificationStatus(str, Enum):
    """Verification state of a source-linked rule."""

    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    DISPUTED = "DISPUTED"


class ExtractedField(BaseModel):
    """A single field extracted from a document."""

    name: str = Field(..., description="Canonical field name, e.g. 'full_name'.")
    raw_value: str = Field(..., description="Value exactly as printed on the document.")
    normalized_value: str = Field(
        ..., description="Cleaned value used for comparison (never destroys original)."
    )
    confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Extraction confidence estimate."
    )
    evidence: str = Field(..., description="Where on the document the value was read from.")
    transliterated_value: Optional[str] = Field(
        None,
        description="Latin-script transliteration when the printed value is in another script.",
    )
    needs_confirmation: bool = Field(
        False,
        description="True when the field is missing or its confidence is below 0.7.",
    )


class Document(BaseModel):
    """An uploaded document and its extracted fields."""

    id: str
    document_type: DocumentType
    filename: str
    fields: List[ExtractedField] = Field(default_factory=list)


class Mismatch(BaseModel):
    """A field that differs (or may differ) across documents."""

    field: str
    document_ids: List[str] = Field(default_factory=list)
    values: Dict[str, str] = Field(default_factory=dict)
    status: MismatchStatus
    explanation: str
    differences_explained: List[str] = Field(
        default_factory=list,
        description="Normalisation assumptions and notes behind the status.",
    )


class ServiceRule(BaseModel):
    """A verified, source-linked requirement for a government service."""

    rule_id: str
    service: str
    topic: str
    conditions: Dict[str, object] = Field(default_factory=dict)
    requirement: str
    source_urls: List[str] = Field(default_factory=list)
    last_verified: str
    verification_status: VerificationStatus
    source_conflict: bool = False


class CorrectionRule(BaseModel):
    """A verified procedure for fixing a specific mismatch."""

    rule_id: str
    fixes: str
    depends_on: List[str] = Field(default_factory=list)
    proof_needed: str
    source_urls: List[str] = Field(default_factory=list)
    verification_status: VerificationStatus


class Finding(BaseModel):
    """A mismatch classified against the rules for a chosen service."""

    mismatch_field: str
    classification: FindingClassification
    reason: str
    rule_id: Optional[str] = None


class CorrectionStep(BaseModel):
    """One ordered step in a correction plan."""

    order: int
    rule_id: str
    action: str
    depends_on: List[str] = Field(default_factory=list)
    is_deadlock: bool = False


class ReadinessResult(BaseModel):
    """Readiness verdict plus findings, open questions and next steps."""

    service_id: str
    status: ReadinessStatus
    findings: List[Finding] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)


class CheckRequest(BaseModel):
    """Request body for the readiness check endpoint."""

    service_id: str
    life_events: List[str] = Field(default_factory=list)
    documents: List[Document] = Field(default_factory=list)


class TraceStep(BaseModel):
    """A non-sensitive processing step recorded for transparency/debugging.

    Never contains document contents or personal data — only the operation name
    and how long it took.
    """

    operation: str
    duration_ms: float


class CheckResponse(BaseModel):
    """Full response for a readiness check."""

    mismatches: List[Mismatch] = Field(default_factory=list)
    readiness: ReadinessResult
    correction_path: List[CorrectionStep] = Field(default_factory=list)
    correction_path_dot: str
    sources: List[str] = Field(default_factory=list)
    trace: List[TraceStep] = Field(
        default_factory=list,
        description="Non-sensitive operation timings (no personal data).",
    )


class DecodeRejectionRequest(BaseModel):
    """Request body for decoding an application rejection reason."""

    rejection_text: str = Field(..., description="The rejection text/code as received.")
    language: str = Field("en", description="Preferred output language code, e.g. 'en'.")


class DecodeRejectionResponse(BaseModel):
    """Plain-language explanation of a rejection reason (synthetic for B0)."""

    plain_language: str
    category: str
    possible_reasons: List[str] = Field(default_factory=list)
    suggested_next_steps: List[str] = Field(default_factory=list)


class TranslateRequest(BaseModel):
    """Request body for translating guidance text."""

    text: str = Field(..., description="Text to translate.")
    target_language: str = Field(..., description="Target language code, e.g. 'hi'.")


class TranslateResponse(BaseModel):
    """Translated text (synthetic for B0)."""

    source_text: str
    translated_text: str
    target_language: str


class ReportRequest(BaseModel):
    """Request body for generating a shareable readiness report."""

    service_id: str
    check: Optional[CheckResponse] = None


class ReportResponse(BaseModel):
    """A plain-language readiness report (synthetic for B0)."""

    service_id: str
    summary: str
    key_findings: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
