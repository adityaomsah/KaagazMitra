"""Deterministic document comparison for KaagazMitra (B1).

Compares extracted fields across documents and returns ``Mismatch`` records with
a conservative status. RapidFuzz is only a *helper signal* — never the final
identity decision.

Safety (per AGENTS.md): originals are always preserved; transliteration is never
treated as certain identity proof; name components are never silently removed;
every normalisation assumption is recorded; we never conclude two documents
belong to the same person from fuzzy matching alone.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from rapidfuzz import fuzz

from .schemas import Document, ExtractedField, Mismatch, MismatchStatus

# Confidence below this is treated as unconfirmed (needs human review).
CONFIDENCE_THRESHOLD = 0.7

# Canonical comparison fields -> field labels that may hold them on a document.
FIELD_ALIASES: Dict[str, Tuple[str, ...]] = {
    "name": ("name", "full_name", "account_holder_name"),
    "date_of_birth": ("date_of_birth", "dob"),
    "father_name": ("father_name", "fathers_name"),
    "address": ("address", "permanent_address"),
}

# Common Indian name abbreviations expanded to a canonical form (comparison only;
# the original value is never rewritten).
ABBREVIATIONS: Dict[str, str] = {
    "md": "mohammad", "mohd": "mohammad", "mohmed": "mohammad",
    "mohammed": "mohammad", "mohamad": "mohammad", "muhammed": "mohammad",
    "muhammad": "mohammad", "mohammad": "mohammad",
}

# Honorifics/titles ignored for comparison but recorded as an assumption.
HONORIFICS = {"mr", "mrs", "ms", "dr", "smt", "shri", "sri", "sh", "late"}


def normalize_for_compare(name: str) -> str:
    """Lower-case, strip punctuation, collapse whitespace (safe normalisation)."""
    if not name:
        return ""
    cleaned = [c if (c.isalnum() or c.isspace()) else " " for c in name.lower()]
    return " ".join("".join(cleaned).split())


def normalize_dob(value: str) -> Optional[str]:
    """Parse a DOB into ISO ``YYYY-MM-DD``; ``None`` if not a known format.

    Supported: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY (day-first per the
    Indian convention). Ambiguous/unrecognised input is never guessed.
    """
    if not value:
        return None
    text = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _is_latin(text: str) -> bool:
    """True when every character is ASCII (a Latin-script value)."""
    return all(ord(ch) < 128 for ch in text)


def _comparable_form(field: ExtractedField) -> str:
    """Latin-script form for comparison (uses transliteration for other scripts)."""
    raw = (field.raw_value or "").strip()
    if raw and not _is_latin(raw) and field.transliterated_value:
        return field.transliterated_value
    return raw


def _name_tokens(norm: str) -> Tuple[List[str], bool]:
    """Split a normalised name into canonical tokens; flag dropped honorifics."""
    tokens: List[str] = []
    dropped = False
    for tok in norm.split():
        if tok in HONORIFICS:
            dropped = True
            continue
        tokens.append(ABBREVIATIONS.get(tok, tok))
    return tokens, dropped


def _token_compatible(a: str, b: str) -> bool:
    """Compatible if equal or one is an initial (single letter) of the other."""
    if a == b:
        return True
    if len(a) == 1 and b.startswith(a):
        return True
    if len(b) == 1 and a.startswith(b):
        return True
    return False


def _tokens_equivalent(ta: List[str], tb: List[str]) -> Optional[str]:
    """Reason string if two token lists are plausibly the same name, else None."""
    if ta == tb:
        return "Names match after expanding abbreviations and ignoring honorifics."
    if len(ta) == len(tb):
        if all(_token_compatible(x, y) for x, y in zip(ta, tb)):
            if any(len(x) == 1 or len(y) == 1 for x, y in zip(ta, tb)):
                return "An initial appears to stand for a full name component."
            return "Names match after expanding abbreviations."
        return None
    # Different lengths: allow a missing component (shorter is a compatible
    # subset of the longer) — a possible variant, never a silent merge.
    shorter, longer = (ta, tb) if len(ta) < len(tb) else (tb, ta)
    remaining = list(longer)
    for tok in shorter:
        idx = next((i for i, c in enumerate(remaining) if _token_compatible(tok, c)), None)
        if idx is None:
            return None
        remaining.pop(idx)
    return "One name appears to be missing a component present in the other."


# --------------------------------------------------------------------------- #
# Per-field pair comparators
# --------------------------------------------------------------------------- #
def _compare_name_pair(a: "FieldValue", b: "FieldValue") -> Tuple[MismatchStatus, List[str]]:
    """Compare two name values -> (status, notes)."""
    notes: List[str] = []
    cross_script = a.is_latin != b.is_latin
    if cross_script:
        notes.append(
            "One value is in a non-Latin script and was compared using its "
            "transliteration. Transliteration is an estimate, not proof of identity."
        )
    a_norm = normalize_for_compare(a.comparable)
    b_norm = normalize_for_compare(b.comparable)
    a_tokens, a_honorific = _name_tokens(a_norm)
    b_tokens, b_honorific = _name_tokens(b_norm)
    if a_honorific or b_honorific:
        notes.append("An honorific/title (e.g. Mr/Smt) was ignored during comparison.")

    # Exact match on both scripts with no dropped honorifics -> confident MATCH.
    if a_norm == b_norm and a.is_latin and b.is_latin and not (a_honorific or b_honorific):
        return MismatchStatus.MATCH, notes

    reason = _tokens_equivalent(a_tokens, b_tokens)
    if reason is not None:
        notes.append(reason)
        # A transliteration-based match is never a confident MATCH.
        return MismatchStatus.POSSIBLE_VARIANT, notes
    return MismatchStatus.DIFFERENCE, notes


def _compare_dob_pair(a: "FieldValue", b: "FieldValue") -> Tuple[MismatchStatus, List[str]]:
    """Compare two DOB values -> (status, notes)."""
    notes = ["Dates were parsed as day-first (DD/MM/YYYY) per Indian convention."]
    a_iso = normalize_dob(a.comparable)
    b_iso = normalize_dob(b.comparable)
    if a_iso is None or b_iso is None:
        notes.append("A date could not be parsed from a known format and was left unverified.")
        return MismatchStatus.UNKNOWN, notes
    if a_iso == b_iso:
        return MismatchStatus.MATCH, notes
    notes.append(f"Parsed dates differ: {a_iso} vs {b_iso}.")
    return MismatchStatus.DIFFERENCE, notes


def _compare_address_pair(a: "FieldValue", b: "FieldValue") -> Tuple[MismatchStatus, List[str]]:
    """Compare two address values -> (status, notes)."""
    notes = [
        "Addresses were compared after lowercasing, removing punctuation and "
        "collapsing whitespace; fuzzy similarity was used only as a helper signal."
    ]
    a_norm = normalize_for_compare(a.comparable)
    b_norm = normalize_for_compare(b.comparable)
    if a_norm == b_norm:
        return MismatchStatus.MATCH, notes
    score = fuzz.token_set_ratio(a_norm, b_norm)  # helper signal only
    if score >= 90:
        notes.append(f"Addresses are highly similar (fuzzy score {score:.0f}/100) but not identical.")
        return MismatchStatus.POSSIBLE_VARIANT, notes
    notes.append(f"Addresses differ materially (fuzzy score {score:.0f}/100).")
    return MismatchStatus.DIFFERENCE, notes


_PAIR_COMPARATORS = {
    "name": _compare_name_pair,
    "father_name": _compare_name_pair,
    "date_of_birth": _compare_dob_pair,
    "address": _compare_address_pair,
}

_STATUS_RANK = {
    MismatchStatus.MATCH: 0,
    MismatchStatus.POSSIBLE_VARIANT: 1,
    MismatchStatus.UNKNOWN: 2,
    MismatchStatus.DIFFERENCE: 3,
}


def _worst(statuses: List[MismatchStatus]) -> MismatchStatus:
    """Return the most serious status (DIFFERENCE outranks everything)."""
    return max(statuses, key=lambda s: _STATUS_RANK[s])


# --------------------------------------------------------------------------- #
# Field extraction / aggregation
# --------------------------------------------------------------------------- #
class FieldValue:
    """A single document's value for a canonical field, ready for comparison."""

    def __init__(self, doc_id: str, field: ExtractedField):
        self.doc_id = doc_id
        self.raw_value = field.raw_value or ""
        self.comparable = _comparable_form(field)
        self.is_latin = _is_latin(self.raw_value) if self.raw_value else True
        stripped = self.raw_value.strip()
        # A value is confirmed only if it is present, not flagged for review, and
        # (if a confidence was given) at or above the threshold.
        self.confirmed = bool(stripped) and not field.needs_confirmation and (
            field.confidence is None or field.confidence >= CONFIDENCE_THRESHOLD
        )


def _get_field(doc: Document, canonical: str) -> Optional[ExtractedField]:
    """Return the first field on ``doc`` matching any alias of ``canonical``."""
    labels = {label.lower() for label in FIELD_ALIASES[canonical]}
    for field in doc.fields:
        if field.name.lower() in labels:
            return field
    return None


def _compare_field(canonical: str, documents: List[Document]) -> Optional[Mismatch]:
    """Compare one canonical field across all documents; None if not present."""
    present = [(doc.id, f) for doc in documents if (f := _get_field(doc, canonical)) is not None]
    if not present:
        return None  # field absent everywhere -> nothing to compare

    values: Dict[str, str] = {doc_id: (f.raw_value or "") for doc_id, f in present}
    doc_ids = [doc_id for doc_id, _ in present]

    field_values = [FieldValue(doc_id, f) for doc_id, f in present]
    confirmed = [fv for fv in field_values if fv.confirmed]
    unconfirmed = [fv.doc_id for fv in field_values if not fv.confirmed]

    base_note = (
        "Values were compared after lowercasing, removing punctuation and "
        "collapsing whitespace. Original values are preserved unchanged."
    )

    # A document has the field but it could not be read confidently.
    if unconfirmed:
        return Mismatch(
            field=canonical,
            document_ids=doc_ids,
            values=values,
            status=MismatchStatus.UNKNOWN,
            explanation=(
                f"The {canonical.replace('_', ' ')} could not be read confidently on "
                f"{', '.join(unconfirmed)}. It needs manual review before comparison."
            ),
            differences_explained=[
                base_note,
                "One or more documents have an unreadable, missing or low-confidence "
                "value for this field, so it cannot be confirmed.",
            ],
        )

    if len(confirmed) < 2:
        return None  # only one readable value -> nothing to compare against

    comparator = _PAIR_COMPARATORS[canonical]
    statuses: List[MismatchStatus] = []
    notes: List[str] = [base_note]
    for i in range(len(confirmed)):
        for j in range(i + 1, len(confirmed)):
            status, pair_notes = comparator(confirmed[i], confirmed[j])
            statuses.append(status)
            for note in pair_notes:
                if note not in notes:
                    notes.append(note)

    status = _worst(statuses)
    label = canonical.replace("_", " ")
    if status == MismatchStatus.MATCH:
        explanation = f"The {label} matches across all documents."
    elif status == MismatchStatus.POSSIBLE_VARIANT:
        explanation = (
            f"The {label} looks like it could be the same across documents, but "
            "there is a difference that needs review."
        )
    elif status == MismatchStatus.DIFFERENCE:
        explanation = f"The {label} is materially different across documents."
    else:
        explanation = f"The {label} could not be confirmed."

    return Mismatch(
        field=canonical,
        document_ids=doc_ids,
        values=values,
        status=status,
        explanation=explanation,
        differences_explained=notes,
    )


def compare_documents(documents: List[Document]) -> List[Mismatch]:
    """Compare all comparable fields across the given documents.

    Produces one ``Mismatch`` per canonical field present on at least one
    document (fields absent everywhere are skipped). Every original value is
    preserved and all normalisation assumptions are explained.
    """
    if len(documents) < 2:
        return []
    results: List[Mismatch] = []
    for canonical in FIELD_ALIASES:
        mismatch = _compare_field(canonical, documents)
        if mismatch is not None:
            results.append(mismatch)
    return results


