// TypeScript mirror of backend/app/schemas.py.
// This file must stay in sync with the Pydantic models (source of truth).
// All API calls go through src/lib/api.ts.

export type DocumentType =
  | "aadhaar"
  | "pan"
  | "bank_passbook"
  | "class10_marksheet"
  | "marriage_certificate"
  | "other";

export type MismatchStatus =
  | "MATCH"
  | "DIFFERENCE"
  | "POSSIBLE_VARIANT"
  | "UNKNOWN";

export type FindingClassification =
  | "NOT_RELEVANT"
  | "NEEDS_SUPPORTING_DOC"
  | "LIKELY_BLOCKER"
  | "VERIFY_AT_OFFICE";

export type ReadinessStatus =
  | "READY"
  | "NEEDS_DOCUMENTS"
  | "BLOCKED"
  | "UNVERIFIED";

export type VerificationStatus = "VERIFIED" | "UNVERIFIED" | "DISPUTED";

export interface ExtractedField {
  name: string;
  raw_value: string;
  normalized_value: string;
  confidence: number | null;
  evidence: string;
}

export interface Document {
  id: string;
  document_type: DocumentType;
  filename: string;
  fields: ExtractedField[];
}

export interface Mismatch {
  field: string;
  document_ids: string[];
  values: Record<string, string>;
  status: MismatchStatus;
  explanation: string;
}

export interface ServiceRule {
  rule_id: string;
  service: string;
  topic: string;
  conditions: Record<string, unknown>;
  requirement: string;
  source_urls: string[];
  last_verified: string;
  verification_status: VerificationStatus;
  source_conflict: boolean;
}

export interface CorrectionRule {
  rule_id: string;
  fixes: string;
  depends_on: string[];
  proof_needed: string;
  source_urls: string[];
  verification_status: VerificationStatus;
}

export interface Finding {
  mismatch_field: string;
  classification: FindingClassification;
  reason: string;
  rule_id: string | null;
}

export interface CorrectionStep {
  order: number;
  rule_id: string;
  action: string;
  depends_on: string[];
  is_deadlock: boolean;
}

export interface ReadinessResult {
  service_id: string;
  status: ReadinessStatus;
  findings: Finding[];
  unresolved_questions: string[];
  next_steps: string[];
}

export interface CheckRequest {
  service_id: string;
  life_events: string[];
  documents: Document[];
}

export interface CheckResponse {
  mismatches: Mismatch[];
  readiness: ReadinessResult;
  correction_path: CorrectionStep[];
  correction_path_dot: string;
  sources: string[];
}

// Response shape of the /api/health endpoint (not part of schemas.py).
export interface HealthResponse {
  status: string;
  version: string;
  use_mock: boolean;
}
