# KaagazMitra API Contract

This document is the contract between the FastAPI backend (`backend/`) and the
React frontend (`frontend/`).

- **Base URL (development):** the Vite dev server proxies `/api` → `http://localhost:8000`,
  so the frontend always calls `/api/...`.
- **Source of truth:** `backend/app/schemas.py` (Pydantic models). The frontend
  mirror is `frontend/src/types/api.ts` and must stay in sync.
- **All frontend calls** go through `frontend/src/lib/api.ts`.

All request/response bodies are JSON unless noted (the upload endpoint uses
`multipart/form-data`).

---

## GET /api/health

Liveness probe used by the frontend connection banner.

**Response `200 OK`**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "use_mock": true
}
```

---

## GET /api/services

List the verified service rules (the rulebook).

**Response `200 OK`**
```json
[
  {
    "rule_id": "rule_pension_age",
    "service": "old_age_pension",
    "topic": "eligibility",
    "conditions": { "min_age": 60 },
    "requirement": "Applicant must be at least 60 years old on the date of application.",
    "source_urls": ["https://nsap.nic.in/"],
    "last_verified": "2025-01-15",
    "verification_status": "VERIFIED",
    "source_conflict": false
  }
]
```

---

## GET /api/services/{rule_id}

Fetch a single service rule.

**Response `200 OK`** — a single `ServiceRule` (same shape as above).

**Response `404 Not Found`**
```json
{ "detail": "Service rule not found: rule_pension_age" }
```

---

## GET /api/correction-rules

List the verified correction rules (how to fix a mismatch).

**Response `200 OK`**
```json
[
  {
    "rule_id": "corr_name_gazette",
    "fixes": "full_name",
    "depends_on": [],
    "proof_needed": "Gazette name-change notification plus a notarised affidavit.",
    "source_urls": ["https://egazette.gov.in/"],
    "verification_status": "VERIFIED"
  }
]
```

---

## GET /api/correction-rules/{rule_id}

Fetch a single correction rule. Same shape as above; `404` if not found.

---

## GET /api/documents

Return the currently loaded documents (demo: Rahim scenario).

**Response `200 OK`**
```json
[
  {
    "id": "doc_aadhaar",
    "document_type": "aadhaar",
    "filename": "rahim_aadhaar.jpg",
    "fields": [
      {
        "name": "full_name",
        "raw_value": "रहीम खान",
        "normalized_value": "Rahim Khan",
        "confidence": 0.96,
        "evidence": "Name field, front of card"
      }
    ]
  }
]
```

---

## GET /api/mismatches

Return the mismatches detected across the loaded documents.

**Response `200 OK`**
```json
[
  {
    "field": "full_name",
    "document_ids": ["doc_aadhaar", "doc_pan"],
    "values": { "doc_aadhaar": "रहीम खान / Rahim Khan", "doc_pan": "Rahman Khan" },
    "status": "POSSIBLE_VARIANT",
    "explanation": "The name is spelled and abbreviated differently across documents…"
  }
]
```

---

## POST /api/extract

Extract fields from an uploaded document image.

**Request** — `multipart/form-data` with:
- `file` — the document image (required).
- `consent` — `true`/`false`; **required**. Per AGENTS.md we obtain consent
  before sending images to cloud AI, so a missing or `false` consent is rejected
  with `400`.
- `document_type` — optional; one of the `DocumentType` values.

With `USE_MOCK=1` this returns a fixed demo `Document` without storing the file
(per the privacy rules in AGENTS.md). Live Gemini Vision extraction replaces this
in a later milestone.

**Response `200 OK`** — a single `Document` (same shape as `GET /api/documents`).

**Response `400 Bad Request`** (missing/false consent)
```json
{ "detail": "Consent is required before sending images to cloud AI." }
```

---

## POST /api/check

Run the document-consistency and application-readiness check. This is the main
endpoint that powers the Review and Guidance steps.

**Request `200 OK`**
```json
{
  "service_id": "old_age_pension",
  "life_events": ["retirement"],
  "documents": []
}
```

**Response `200 OK`**
```json
{
  "mismatches": [
    {
      "field": "full_name",
      "document_ids": ["doc_aadhaar", "doc_pan", "doc_bank", "doc_marksheet", "doc_marriage"],
      "values": {
        "doc_aadhaar": "रहीम खान / Rahim Khan",
        "doc_pan": "Rahman Khan",
        "doc_bank": "Md Rahim Khan",
        "doc_marksheet": "Rahim Uddin Khan",
        "doc_marriage": "Rahim Khan"
      },
      "status": "POSSIBLE_VARIANT",
      "explanation": "The name is spelled and abbreviated differently across documents…"
    }
  ],
  "readiness": {
    "service_id": "old_age_pension",
    "status": "NEEDS_DOCUMENTS",
    "findings": [
      {
        "mismatch_field": "full_name",
        "classification": "NEEDS_SUPPORTING_DOC",
        "reason": "For the pension, the name on the Aadhaar must match the bank account…",
        "rule_id": "rule_pension_name_match"
      }
    ],
    "unresolved_questions": [
      "Is the legal name 'Rahim Khan' or 'Rahman Khan'?"
    ],
    "next_steps": [
      "Collect a bank confirmation letter that links 'Md Rahim Khan' to 'Rahim Khan'."
    ]
  },
  "correction_path": [
    {
      "order": 1,
      "rule_id": "corr_name_gazette",
      "action": "Publish a name-change gazette notification to unify the spelling…",
      "depends_on": [],
      "is_deadlock": false
    }
  ],
  "correction_path_dot": "digraph correction_path { … }",
  "sources": ["https://egazette.gov.in/", "https://www.incometax.gov.in/", "https://uidai.gov.in/"]
}
```

---

## POST /api/decode-rejection

Explain an application rejection reason in plain language.

**Request**
```json
{ "rejection_text": "Name mismatch with bank account", "language": "en" }
```

**Response `200 OK`**
```json
{
  "plain_language": "Your application was returned because the name on your bank account did not exactly match the name on your Aadhaar.",
  "category": "name_mismatch",
  "possible_reasons": ["Bank passbook shows 'Md Rahim Khan' while Aadhaar shows 'Rahim Khan'."],
  "suggested_next_steps": ["Carry a bank letter linking both spellings of your name."]
}
```

---

## POST /api/translate

Translate guidance text into a target language.

**Request**
```json
{ "text": "Your application is ready.", "target_language": "hi" }
```

**Response `200 OK`**
```json
{
  "source_text": "Your application is ready.",
  "translated_text": "[mock-hi] Your application is ready.",
  "target_language": "hi"
}
```

> With `USE_MOCK=1` the translated text is a clearly-marked placeholder so the
> flow works without a live translation service.

---

## POST /api/report

Generate a shareable, plain-language readiness report.

**Request**
```json
{ "service_id": "old_age_pension", "check": null }
```

**Response `200 OK`**
```json
{
  "service_id": "old_age_pension",
  "summary": "Your old_age_pension application is not ready yet. ...",
  "key_findings": ["Readiness status: NEEDS_DOCUMENTS."],
  "next_steps": ["Collect a bank confirmation letter ..."]
}
```

---

## Enumerations

| Type | Values |
| --- | --- |
| `DocumentType` | `aadhaar`, `pan`, `bank_passbook`, `class10_marksheet`, `marriage_certificate`, `other` |
| `MismatchStatus` | `MATCH`, `DIFFERENCE`, `POSSIBLE_VARIANT`, `UNKNOWN` |
| `FindingClassification` | `NOT_RELEVANT`, `NEEDS_SUPPORTING_DOC`, `LIKELY_BLOCKER`, `VERIFY_AT_OFFICE` |
| `ReadinessStatus` | `READY`, `NEEDS_DOCUMENTS`, `BLOCKED`, `UNVERIFIED` |
| `VerificationStatus` | `VERIFIED`, `UNVERIFIED`, `DISPUTED` |
