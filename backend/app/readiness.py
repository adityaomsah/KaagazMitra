"""Application Readiness Engine for KaagazMitra (B2).

Turns detected document mismatches into a conservative, source-linked readiness
verdict for a chosen government service.

Safety (per AGENTS.md and the B2 spec):
- ONLY rules with ``verification_status == "verified"`` are treated as confirmed
  requirements. Pending/unverified/disputed rules are never applied; they surface
  as unresolved questions instead.
- Deterministic rule applicability runs first. Gemini (when enabled and only in
  live mode) may interpret ONLY the supplied verified rule text, quotes and rule
  IDs — never external requirements and never personal document values.
- An AI classification without a valid verified ``rule_id`` becomes
  VERIFY_AT_OFFICE; any Gemini failure safely falls back to VERIFY_AT_OFFICE.
- Official-source conflicts are surfaced, never auto-resolved.
- READY never means guaranteed government approval.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional, Tuple

from .schemas import (
    Document,
    Finding,
    FindingClassification,
    Mismatch,
    MismatchStatus,
    ReadinessResult,
    ReadinessStatus,
    ServiceRule,
    VerificationStatus,
)

# Versioned rulebooks live here in production (populated by rule research).
# Tests override this to point at synthetic fixtures under backend/tests/.
RULEBOOK_DIR = Path(__file__).resolve().parent.parent / "rulebooks" / "services"

# Mismatch statuses that indicate a discrepancy worth acting on.
_DISCREPANCY_STATUSES = {
    MismatchStatus.DIFFERENCE,
    MismatchStatus.POSSIBLE_VARIANT,
    MismatchStatus.UNKNOWN,
}

# Map a rule's declared severity to a finding classification.
_SEVERITY_TO_CLASSIFICATION = {
    "blocker": FindingClassification.LIKELY_BLOCKER,
    "supporting_doc": FindingClassification.NEEDS_SUPPORTING_DOC,
    "verify_at_office": FindingClassification.VERIFY_AT_OFFICE,
    "not_relevant": FindingClassification.NOT_RELEVANT,
}


def load_service_rules(service_id: str) -> List[ServiceRule]:
    """Load and validate the versioned rulebook for a service.

    Returns an empty list when no rulebook exists (never invents rules).
    """
    path = RULEBOOK_DIR / f"{service_id}.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data["rules"] if isinstance(data, dict) else data
    return [ServiceRule.model_validate(item) for item in items]


def _service_matches(rule: ServiceRule, service_id: str) -> bool:
    return rule.service == service_id


def _life_event_applies(rule: ServiceRule, life_events: List[str]) -> bool:
    """A rule with a life-event gate applies only if one is selected.

    Rules without a life-event gate apply regardless of life events.
    """
    gated = rule.conditions.get("life_events")
    if not gated:
        return True
    selected = {str(e).lower() for e in life_events}
    return any(str(e).lower() in selected for e in gated)  # type: ignore[union-attr]


def _missing_required_docs(rule: ServiceRule, present_types: set) -> List[str]:
    required = rule.conditions.get("documents_required") or []
    return [dt for dt in required if dt not in present_types]  # type: ignore[union-attr]


def _rule_governs_field(rule: ServiceRule, field: str) -> bool:
    """True when the rule's conditions target this comparison field."""
    fields = rule.conditions.get("fields") or rule.conditions.get("applies_to_fields")
    if not fields:
        return False
    return field in fields  # type: ignore[operator]


def _classify_mismatch_with_rule(
    rule: ServiceRule, mismatch: Mismatch
) -> Tuple[FindingClassification, str]:
    """Deterministically classify a governed mismatch using a verified rule.

    The rule's declared ``severity`` (in conditions) drives the classification.
    A name change after marriage supported by a marriage certificate, for
    example, is a supporting-document need rather than a blocker.
    """
    severity = str(rule.conditions.get("severity", "verify_at_office")).lower()
    classification = _SEVERITY_TO_CLASSIFICATION.get(
        severity, FindingClassification.VERIFY_AT_OFFICE
    )
    label = mismatch.field.replace("_", " ")
    reason = (
        f"Rule {rule.rule_id} ({rule.topic}): {rule.requirement} "
        f"This applies to the {label} discrepancy ({mismatch.status.value})."
    )
    if rule.source_urls:
        reason += f" Source: {', '.join(rule.source_urls)}."
    if rule.source_conflict:
        reason += (
            " Official sources conflict on this rule, so it is not certain — "
            "confirm the exact requirement at the office."
        )
    return classification, reason


def _ai_classify_uncovered(
    rule: ServiceRule, mismatch: Mismatch
) -> Tuple[Optional[FindingClassification], Optional[str]]:
    """Optionally ask Gemini to interpret a verified rule for an uncovered mismatch.

    Gemini receives ONLY the verified rule text, its quote and rule_id — never
    the user's document values. It must return a valid rule_id and one of the
    allowed classifications. Any failure or an invalid/absent rule_id yields
    ``(None, None)`` so the caller falls back to VERIFY_AT_OFFICE.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None, None
    try:
        from google import genai
        from google.genai import types

        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        prompt = f"""
You are classifying a document discrepancy against ONE verified official rule.
Use ONLY the rule text below. Do not invent requirements. Do not use any
personal data. Return STRICT JSON:
{{"rule_id": "<the rule id>", "classification": "<one of NOT_RELEVANT, NEEDS_SUPPORTING_DOC, LIKELY_BLOCKER, VERIFY_AT_OFFICE>"}}

Verified rule:
- rule_id: {rule.rule_id}
- topic: {rule.topic}
- requirement: {rule.requirement}
- official quote: {rule.conditions.get("official_quote", rule.requirement)}

Discrepancy (no personal values): field="{mismatch.field}", status="{mismatch.status.value}".
""".strip()
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json", temperature=0.0
            ),
        )
        data = json.loads(response.text or "{}")
        rule_id = data.get("rule_id")
        classification_raw = str(data.get("classification", "")).upper()
        # The AI must cite the exact verified rule and a valid classification.
        if rule_id != rule.rule_id:
            return None, None
        classification = FindingClassification(classification_raw)
        return classification, f"AI interpretation of verified rule {rule.rule_id}."
    except Exception:
        # Gemini failure or malformed output -> safe fallback handled by caller.
        return None, None


def check_readiness(
    service_id: str,
    life_events: List[str],
    documents: List[Document],
    mismatches: List[Mismatch],
) -> ReadinessResult:
    """Evaluate application readiness for a service.

    Deterministic first, verified-rules-only. Produces a conservative verdict,
    plain-language next steps with source links, and unresolved questions for
    anything pending, conflicting or unknown. READY never implies approval.
    """
    rules = load_service_rules(service_id)
    present_types = {doc.document_type.value for doc in documents}
    discrepancies = [m for m in mismatches if m.status in _DISCREPANCY_STATUSES]

    findings: List[Finding] = []
    unresolved: List[str] = []
    next_steps: List[str] = []
    verified_applicable = 0

    # ---- Pass 1: rules applicable to this service + life events ------------- #
    applicable_rules: List[ServiceRule] = []
    for rule in rules:
        if not _service_matches(rule, service_id):
            continue
        if not _life_event_applies(rule, life_events):
            continue

        # Only VERIFIED rules may drive confirmed requirements; pending or
        # missing verification is surfaced as an unresolved question instead.
        if rule.verification_status != VerificationStatus.VERIFIED:
            unresolved.append(
                f"Rule {rule.rule_id} ({rule.topic}) is {rule.verification_status.value} "
                "and was NOT applied. It still needs official verification: "
                f"{rule.requirement}"
            )
            continue

        applicable_rules.append(rule)
        verified_applicable += 1

        # Official-source conflict: surface, never auto-resolve.
        if rule.source_conflict:
            note = rule.conditions.get("conflict_note") or (
                "Official sources disagree on this rule; the requirement is disputed."
            )
            unresolved.append(
                f"Source conflict on rule {rule.rule_id}: {note} "
                "This requirement is not certain and must be confirmed at the office."
            )

        # Missing required documents -> NEEDS_SUPPORTING_DOC.
        missing = _missing_required_docs(rule, present_types)
        if missing:
            findings.append(
                Finding(
                    mismatch_field="documents",
                    classification=FindingClassification.NEEDS_SUPPORTING_DOC,
                    reason=(
                        f"Rule {rule.rule_id} requires {missing} but they are missing. "
                        f"{rule.requirement}"
                    ),
                    rule_id=rule.rule_id,
                )
            )
            next_steps.append(
                f"Obtain the required document(s): {', '.join(missing)}. "
                f"Source: {', '.join(rule.source_urls) or 'official rulebook'}."
            )

    # ---- Pass 2: classify each discrepancy against governing verified rules - #
    for mismatch in discrepancies:
        governing = [
            r for r in applicable_rules
            if r.verification_status == VerificationStatus.VERIFIED
            and _rule_governs_field(r, mismatch.field)
        ]
        if governing:
            rule = governing[0]
            classification, reason = _classify_mismatch_with_rule(rule, mismatch)
            findings.append(
                Finding(
                    mismatch_field=mismatch.field,
                    classification=classification,
                    reason=reason,
                    rule_id=rule.rule_id,
                )
            )
            if classification == FindingClassification.NEEDS_SUPPORTING_DOC:
                next_steps.append(
                    f"For the {mismatch.field.replace('_', ' ')} difference, gather the "
                    f"supporting document described by rule {rule.rule_id}. "
                    f"Source: {', '.join(rule.source_urls) or 'official rulebook'}."
                )
            elif classification == FindingClassification.LIKELY_BLOCKER:
                next_steps.append(
                    f"Resolve the {mismatch.field.replace('_', ' ')} difference described by "
                    f"rule {rule.rule_id} before applying."
                )
            continue

        # No deterministic governing rule: optionally ask Gemini to interpret a
        # verified rule; otherwise fall back to VERIFY_AT_OFFICE.
        verified_candidates = [
            r for r in applicable_rules
            if r.verification_status == VerificationStatus.VERIFIED
        ]
        classification = FindingClassification.VERIFY_AT_OFFICE
        rule_id: Optional[str] = None
        reason = (
            f"The {mismatch.field.replace('_', ' ')} difference "
            f"({mismatch.status.value}) has no verified rule that clearly covers it, "
            "so it must be checked with an official before applying."
        )
        if verified_candidates:
            ai_classification, ai_reason = _ai_classify_uncovered(
                verified_candidates[0], mismatch
            )
            if ai_classification is not None and ai_reason is not None:
                classification = ai_classification
                reason = ai_reason
                rule_id = verified_candidates[0].rule_id

        findings.append(
            Finding(
                mismatch_field=mismatch.field,
                classification=classification,
                reason=reason,
                rule_id=rule_id,
            )
        )
        if classification == FindingClassification.VERIFY_AT_OFFICE:
            next_steps.append(
                f"Ask the office how to handle the {mismatch.field.replace('_', ' ')} "
                "difference; no verified rule currently covers it."
            )

    # ---- Determine overall status ------------------------------------------ #
    has_blocker = any(
        f.classification == FindingClassification.LIKELY_BLOCKER for f in findings
    )
    has_needs_doc = any(
        f.classification == FindingClassification.NEEDS_SUPPORTING_DOC for f in findings
    )
    has_verify = any(
        f.classification == FindingClassification.VERIFY_AT_OFFICE for f in findings
    )

    if has_blocker:
        status = ReadinessStatus.BLOCKED
    elif has_needs_doc:
        status = ReadinessStatus.NEEDS_DOCUMENTS
    elif has_verify or unresolved or verified_applicable == 0:
        # Unknown/conflicting/pending items, or no verified coverage at all.
        status = ReadinessStatus.UNVERIFIED
        if verified_applicable == 0 and not unresolved:
            unresolved.append(
                f"No verified readiness rules are available for '{service_id}' yet, "
                "so readiness cannot be confirmed automatically."
            )
    else:
        # Verified coverage with no open discrepancies — still not an approval.
        status = ReadinessStatus.READY
        next_steps.append(
            "All verified checks passed. This is not a guarantee of approval; the "
            "office makes the final decision."
        )

    if unresolved:
        next_steps.append(
            "Confirm the open questions listed above with the office before "
            "applying; they are not verified requirements yet."
        )

    if not next_steps:
        next_steps.append("Review your documents with an official before applying.")

    return ReadinessResult(
        service_id=service_id,
        status=status,
        findings=findings,
        unresolved_questions=unresolved,
        next_steps=next_steps,
    )




