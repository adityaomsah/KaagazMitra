// TEMP contract gaps — every frontend workaround for fields the API contract
// (backend/app/schemas.py) does not provide yet lives in THIS file, so each one
// can be deleted in a single place once the backend catches up.
//
//   1. needsChecking()      -> replace with ExtractedField.needs_confirmation
//   2. getTransliteration() -> replace with a dedicated transliteration field
//   3. REVIEW_FIELDS        -> replace once field names are a shared enum
//   4. applyFieldEdit()     -> drop once the backend re-normalises user edits

import type { Document, ExtractedField } from "@/types/api";

// ---------------------------------------------------------------------------
// 1. TEMP contract gap: "needs checking" until `needs_confirmation` exists.
// ---------------------------------------------------------------------------

/** Below this confidence estimate we ask the user to look at the field. */
export const LOW_CONFIDENCE_THRESHOLD = 0.7;

/** True when the user should double-check a field (confidence null or < 0.7). */
export function needsChecking(field: ExtractedField): boolean {
  return field.confidence === null || field.confidence < LOW_CONFIDENCE_THRESHOLD;
}

// ---------------------------------------------------------------------------
// 2. TEMP contract gap: transliteration until the API returns one explicitly.
// ---------------------------------------------------------------------------

const LETTER = /\p{L}/gu;
const LATIN_LETTER = /^\p{Script=Latin}$/u;

/** True when every letter in the value is Latin script (no letters = Latin). */
export function isLatinScript(value: string): boolean {
  const letters = value.match(LETTER) ?? [];
  return letters.every((letter) => LATIN_LETTER.test(letter));
}

/**
 * The Latin reading of a non-Latin value, or null. Uses normalized_value when
 * it differs from raw_value and raw_value is not Latin script.
 */
export function getTransliteration(field: ExtractedField): string | null {
  const normalized = field.normalized_value.trim();
  if (!normalized || normalized === field.raw_value.trim()) return null;
  if (isLatinScript(field.raw_value)) return null;
  return normalized;
}

// ---------------------------------------------------------------------------
// 3. TEMP contract gap: map review fields to the names the data really uses.
// ---------------------------------------------------------------------------

export type ReviewFieldKey =
  | "name"
  | "dob"
  | "father_name"
  | "spouse_name"
  | "address"
  | "gender";

interface ReviewFieldSpec {
  key: ReviewFieldKey;
  label: string;
  /** ExtractedField.name values that count as this review field. */
  sourceNames: string[];
}

export const REVIEW_FIELDS: ReviewFieldSpec[] = [
  { key: "name", label: "Name", sourceNames: ["name", "full_name", "account_holder_name"] },
  { key: "dob", label: "Date of birth", sourceNames: ["dob", "date_of_birth"] },
  { key: "father_name", label: "Father's name", sourceNames: ["father_name"] },
  { key: "spouse_name", label: "Spouse's name", sourceNames: ["spouse_name"] },
  { key: "address", label: "Address", sourceNames: ["address"] },
  { key: "gender", label: "Gender", sourceNames: ["gender"] },
];

export interface ReviewFieldEntry {
  key: ReviewFieldKey;
  label: string;
  /** Index into document.fields, used to apply edits. */
  index: number;
  field: ExtractedField;
}

/** The reviewable fields present on a document, in REVIEW_FIELDS order. */
export function getReviewFields(doc: Document): ReviewFieldEntry[] {
  const entries: ReviewFieldEntry[] = [];
  for (const spec of REVIEW_FIELDS) {
    doc.fields.forEach((field, index) => {
      if (spec.sourceNames.includes(field.name)) {
        entries.push({ key: spec.key, label: spec.label, index, field });
      }
    });
  }
  return entries;
}

/** Friendly label for an API field name (e.g. "full_name" -> "Name"). */
export function fieldLabel(fieldName: string): string {
  const spec = REVIEW_FIELDS.find((s) => s.sourceNames.includes(fieldName));
  if (spec) return spec.label;
  const words = fieldName.split(/[_\s]+/).filter(Boolean).join(" ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

// ---------------------------------------------------------------------------
// 4. TEMP contract gap: the backend does not re-normalise user edits yet.
// ---------------------------------------------------------------------------

/**
 * Apply a user edit. raw_value always takes the edit (original script kept as
 * typed). If the edit is Latin script, normalized_value follows it so the
 * comparison uses what the user confirmed; otherwise the previous
 * normalized_value is kept so the transliteration is not lost.
 */
export function applyFieldEdit(field: ExtractedField, value: string): ExtractedField {
  return {
    ...field,
    raw_value: value,
    normalized_value: isLatinScript(value) ? value.trim() : field.normalized_value,
  };
}
