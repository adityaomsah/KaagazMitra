// Plain-language display labels shared by the Review and Results steps.

import type { Document, DocumentType, ReadinessStatus } from "@/types/api";

/** Plain-language readiness verdicts. Hedged: never guarantees approval. */
export const READINESS_TEXT: Record<
  ReadinessStatus,
  { title: string; body: string; className: string }
> = {
  READY: {
    title: "Your documents look ready",
    body: "We didn't find anything that should stop your application. The office makes the final decision.",
    className: "border-green-300 bg-green-50",
  },
  NEEDS_DOCUMENTS: {
    title: "Almost there: a few things to sort out",
    body: "Some details differ between your documents. The steps below can help before you apply.",
    className: "border-yellow-300 bg-yellow-50",
  },
  BLOCKED: {
    title: "Something needs fixing first",
    body: "One difference may stop the application. Start with the first step below.",
    className: "border-red-300 bg-red-50",
  },
  UNVERIFIED: {
    title: "We couldn't confirm everything",
    body: "Some details could not be read or checked. Please confirm them at the office.",
    className: "border-gray-300 bg-gray-100",
  },
};

const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  aadhaar: "Aadhaar",
  pan: "PAN card",
  bank_passbook: "Bank passbook",
  class10_marksheet: "Class 10 marksheet",
  marriage_certificate: "Marriage certificate",
  other: "Other document",
};

export function documentTypeLabel(type: DocumentType): string {
  return DOCUMENT_TYPE_LABELS[type] ?? "Document";
}

/** Label for a document id used in Mismatch.values (falls back to the id). */
export function documentLabelById(documents: Document[], id: string): string {
  const doc = documents.find((d) => d.id === id);
  return doc ? documentTypeLabel(doc.document_type) : id;
}
