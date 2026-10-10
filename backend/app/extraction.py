"""Gemini Vision field extraction for KaagazMitra (B1).

Extracts structured fields from a document image using Google Gemini and returns
a validated ``Document``. Safety (per AGENTS.md):
- The printed value is preserved verbatim in ``raw_value`` (original scripts kept).
- Nothing is invented: unreadable/absent fields are returned as empty and flagged
  ``needs_confirmation`` rather than guessed.
- ``confidence`` is an estimate in [0, 1], never a calibrated probability.
- Gemini/parse failures degrade to review-required fields instead of crashing.
- Uploaded images are never written to disk.
- A small bounded in-memory cache keyed by image hash avoids repeat Gemini calls
  for identical demo images; nothing sensitive is persisted to disk.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from collections import OrderedDict
from typing import Dict, List, Optional

from .schemas import Document, DocumentType, ExtractedField

# Confidence below this threshold marks a field as needing human review.
CONFIDENCE_THRESHOLD = 0.7

# Fields we ask Gemini to read when visible on a document. Canonical names match
# the rest of the system (schemas, mock fixtures, matching aliases).
TARGET_FIELDS = ("name", "date_of_birth", "father_name", "spouse_name", "address", "gender")

# Map our canonical field names to the JSON keys we ask Gemini to use.
_FIELD_PROMPT_KEYS = {
    "name": "name",
    "date_of_birth": "date_of_birth",
    "father_name": "father_name",
    "spouse_name": "spouse_name",
    "address": "address",
    "gender": "gender",
}

# Bounded in-memory cache: image-hash -> Document. Never persisted to disk.
_CACHE_MAX = 32
_CACHE: "OrderedDict[str, Document]" = OrderedDict()


def _get_model() -> str:
    """Return the Gemini model id from the environment (GEMINI_MODEL)."""
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def _image_hash(image_bytes: bytes) -> str:
    """Stable hash of the image bytes for in-memory caching."""
    return hashlib.sha256(image_bytes).hexdigest()


def _cache_get(key: str) -> Optional[Document]:
    """Fetch from the bounded cache, refreshing recency. None on miss."""
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return _CACHE[key]
    return None


def _cache_put(key: str, doc: Document) -> None:
    """Store in the bounded cache, evicting the oldest entry if needed."""
    _CACHE[key] = doc
    _CACHE.move_to_end(key)
    while len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)


def _build_prompt(document_type: Optional[DocumentType]) -> str:
    """Instruction prompt asking Gemini for a strict JSON object."""
    doc_hint = document_type.value if document_type else "identity document"
    return f"""
You are reading an Indian {doc_hint} image. Extract ONLY the fields that are
clearly visible. Do NOT guess, infer or invent any value.

For each field below, return an object with:
- "raw_value": the value EXACTLY as printed, preserving the original script
  (e.g. keep Devanagari as Devanagari). Use "" if not visible.
- "transliteration": a Latin-script transliteration IF the printed value is in a
  non-Latin script; otherwise "".
- "confidence": your confidence from 0.0 to 1.0 that you read it correctly.
- "evidence": a short note on where on the document you read it (e.g. "top-right").

Fields to look for:
- name (the person's full name)
- date_of_birth
- father_name
- spouse_name
- address
- gender

Return STRICT JSON only, with this exact shape:
{{
  "fields": {{
    "name": {{"raw_value": "", "transliteration": "", "confidence": 0.0, "evidence": ""}},
    "date_of_birth": {{"raw_value": "", "transliteration": "", "confidence": 0.0, "evidence": ""}},
    "father_name": {{"raw_value": "", "transliteration": "", "confidence": 0.0, "evidence": ""}},
    "spouse_name": {{"raw_value": "", "transliteration": "", "confidence": 0.0, "evidence": ""}},
    "address": {{"raw_value": "", "transliteration": "", "confidence": 0.0, "evidence": ""}},
    "gender": {{"raw_value": "", "transliteration": "", "confidence": 0.0, "evidence": ""}}
  }}
}}
If a field is not visible, set raw_value to "" and confidence to 0.0.
""".strip()


def _coerce_confidence(value: object) -> Optional[float]:
    """Coerce a raw JSON confidence into a float in [0, 1], else None."""
    try:
        conf = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if conf < 0.0:
        return 0.0
    if conf > 1.0:
        return 1.0
    return conf


def _build_field(canonical: str, raw: Dict[str, object]) -> ExtractedField:
    """Build a validated ``ExtractedField`` from one Gemini field object.

    Missing/unreadable values become empty strings flagged for confirmation —
    never invented.
    """
    raw_value = str(raw.get("raw_value") or "").strip()
    transliteration = str(raw.get("transliteration") or "").strip()
    confidence = _coerce_confidence(raw.get("confidence"))
    evidence = str(raw.get("evidence") or "").strip()

    # Only keep a transliteration when it differs from the printed value.
    if transliteration and transliteration.lower() == raw_value.lower():
        transliteration = ""

    missing = not raw_value
    low_confidence = confidence is not None and confidence < CONFIDENCE_THRESHOLD
    needs_confirmation = bool(missing or low_confidence)

    return ExtractedField(
        name=canonical,
        raw_value=raw_value,
        normalized_value=raw_value,  # deterministic comparison happens in matching
        transliterated_value=transliteration or None,
        confidence=confidence,
        needs_confirmation=needs_confirmation,
        evidence=evidence or ("Not visible on document" if missing else ""),
    )


def _parse_response(text: str, document_type: DocumentType, filename: str) -> Document:
    """Parse Gemini's JSON text into a validated ``Document``.

    Malformed JSON or unexpected shapes degrade to a document whose fields are
    all flagged for confirmation rather than raising.
    """
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    try:
        data = json.loads(text)
        fields_raw = data["fields"]
        if not isinstance(fields_raw, dict):
            raise ValueError("fields is not an object")
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        # Could not understand the model output -> review-required, nothing invented.
        return Document(
            id=doc_id,
            document_type=document_type,
            filename=filename,
            fields=[
                ExtractedField(
                    name=canonical,
                    raw_value="",
                    normalized_value="",
                    confidence=None,
                    needs_confirmation=True,
                    evidence="Could not read a structured response from the document.",
                )
                for canonical in TARGET_FIELDS
            ],
        )

    fields: List[ExtractedField] = []
    for canonical in TARGET_FIELDS:
        raw = fields_raw.get(_FIELD_PROMPT_KEYS[canonical], {})
        if not isinstance(raw, dict):
            raw = {}
        fields.append(_build_field(canonical, raw))

    return Document(id=doc_id, document_type=document_type, filename=filename, fields=fields)


def _review_required_document(document_type: DocumentType, filename: str) -> Document:
    """A document whose fields are all flagged for confirmation (no invention)."""
    return Document(
        id=f"doc_{uuid.uuid4().hex[:12]}",
        document_type=document_type,
        filename=filename,
        fields=[
            ExtractedField(
                name=canonical,
                raw_value="",
                normalized_value="",
                confidence=None,
                needs_confirmation=True,
                evidence="Document could not be read automatically; please review manually.",
            )
            for canonical in TARGET_FIELDS
        ],
    )


def _resolve_document_type(document_type: Optional[DocumentType]) -> DocumentType:
    """Return a concrete ``DocumentType`` (defaults to OTHER)."""
    return document_type if isinstance(document_type, DocumentType) else DocumentType.OTHER


def extract_document(
    image_bytes: bytes,
    document_type: Optional[DocumentType],
    filename: str,
) -> Document:
    """Extract structured fields from a document image using Gemini Vision.

    Returns a validated ``Document``. On any API/parse failure the result is a
    review-required document (empty, flagged fields) rather than an exception, so
    the API never crashes and never invents data. Uses a bounded in-memory cache
    keyed by image hash; the image is never written to disk.
    """
    resolved_type = _resolve_document_type(document_type)

    # Return a cached result for an identical image (bounded, in-memory only).
    cache_key = f"{_image_hash(image_bytes)}:{resolved_type.value}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        # No credentials -> review-required, never invent. (Mock mode is handled
        # by the caller; this keeps live mode safe without a key.)
        return _review_required_document(resolved_type, filename)

    try:
        # Imported lazily so mock mode works even without the package installed.
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        response = client.models.generate_content(
            model=_get_model(),
            contents=[_build_prompt(resolved_type), image_part],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        document = _parse_response(response.text or "", resolved_type, filename)
    except Exception:
        # Gemini API error, timeout, or anything unexpected -> safe fallback.
        document = _review_required_document(resolved_type, filename)

    _cache_put(cache_key, document)
    return document
