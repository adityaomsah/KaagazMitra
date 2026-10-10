// Single entry point for every backend API call.
// The Vite dev server proxies /api to http://localhost:8000 (see vite.config.ts).

import type {
  CheckRequest,
  CheckResponse,
  CorrectionRule,
  DecodeRejectionRequest,
  DecodeRejectionResponse,
  Document,
  DocumentType,
  HealthResponse,
  Mismatch,
  ReportRequest,
  ReportResponse,
  ServiceRule,
  TranslateRequest,
  TranslateResponse,
} from "@/types/api";
import type { UploadedDocument } from "@/types/wizard";
import { DEFAULT_PERSONA_ID, getPersona, type PersonaId } from "@/mock";

const BASE = "/api";

/**
 * Frontend mock mode (VITE_USE_MOCK=1): extract() and check() return data from
 * src/mock instead of calling the backend, so the flow works offline.
 */
export function isMockMode(): boolean {
  const flag = (import.meta.env.VITE_USE_MOCK ?? "").toLowerCase();
  return flag === "1" || flag === "true";
}

const MOCK_DELAY_MS = 600;

function mockDelay<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), MOCK_DELAY_MS));
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

async function handle<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${response.statusText}`);
  }
  return (await response.json()) as T;
}

/** GET /api/health — liveness probe. */
export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch(`${BASE}/health`);
  return handle<HealthResponse>(res);
}

/** GET /api/services — list verified service rules. */
export async function listServices(): Promise<ServiceRule[]> {
  const res = await fetch(`${BASE}/services`);
  return handle<ServiceRule[]>(res);
}

/** GET /api/services/:ruleId — fetch a single service rule. */
export async function getService(ruleId: string): Promise<ServiceRule> {
  const res = await fetch(`${BASE}/services/${ruleId}`);
  return handle<ServiceRule>(res);
}

/** GET /api/correction-rules — list verified correction rules. */
export async function listCorrectionRules(): Promise<CorrectionRule[]> {
  const res = await fetch(`${BASE}/correction-rules`);
  return handle<CorrectionRule[]>(res);
}

/** GET /api/correction-rules/:ruleId — fetch a single correction rule. */
export async function getCorrectionRule(ruleId: string): Promise<CorrectionRule> {
  const res = await fetch(`${BASE}/correction-rules/${ruleId}`);
  return handle<CorrectionRule>(res);
}

/** GET /api/documents — list the currently loaded documents. */
export async function listDocuments(): Promise<Document[]> {
  const res = await fetch(`${BASE}/documents`);
  return handle<Document[]>(res);
}

/** GET /api/mismatches — list detected mismatches. */
export async function listMismatches(): Promise<Mismatch[]> {
  const res = await fetch(`${BASE}/mismatches`);
  return handle<Mismatch[]>(res);
}

/** POST /api/extract — extract fields from a document image (requires consent). */
export async function extractDocument(
  file: File,
  consent: boolean,
  documentType?: DocumentType,
): Promise<Document> {
  const form = new FormData();
  form.append("file", file);
  form.append("consent", String(consent));
  if (documentType) {
    form.append("document_type", documentType);
  }
  const res = await fetch(`${BASE}/extract`, {
    method: "POST",
    body: form,
  });
  return handle<Document>(res);
}

/** POST /api/check — run the document-consistency and readiness check. */
export async function runCheck(request: CheckRequest): Promise<CheckResponse> {
  const res = await fetch(`${BASE}/check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  return handle<CheckResponse>(res);
}

export interface MockOptions {
  /** Demo persona whose mock data to use. Forces mock data when set. */
  personaId?: PersonaId | null;
}

/**
 * Mock extraction: for each upload, pick an unused persona document of the
 * same type (else any unused one, else a copy), keeping the user's chosen type
 * and file name. Images are never read in mock mode.
 */
function mockExtract(uploads: UploadedDocument[], personaId: PersonaId): Document[] {
  const pool = clone(getPersona(personaId).documents);
  const used = new Set<string>();
  return uploads.map((upload, index) => {
    const type = upload.documentType || "other";
    const pick =
      pool.find((d) => !used.has(d.id) && d.document_type === type) ??
      pool.find((d) => !used.has(d.id));
    const doc: Document = pick
      ? pick
      : { ...clone(pool[0]), id: `${pool[0].id}_${index + 1}` };
    used.add(doc.id);
    return { ...doc, document_type: type, filename: upload.file.name };
  });
}

/**
 * Step 3 -> 4: read every uploaded document. In mock mode returns persona data;
 * otherwise calls POST /api/extract once per document.
 */
export async function extract(
  uploads: UploadedDocument[],
  consent: boolean,
  options: MockOptions = {},
): Promise<Document[]> {
  if (!consent) {
    throw new Error("Consent is required before reading your documents.");
  }
  if (options.personaId || isMockMode()) {
    return mockDelay(mockExtract(uploads, options.personaId ?? DEFAULT_PERSONA_ID));
  }
  return Promise.all(
    uploads.map((upload) =>
      extractDocument(upload.file, consent, upload.documentType || undefined),
    ),
  );
}

/**
 * Step 4 -> 5: compare the (user-edited) documents and get readiness guidance.
 * In mock mode or for a demo persona returns that persona's prepared response.
 */
export async function check(
  request: CheckRequest,
  options: MockOptions = {},
): Promise<CheckResponse> {
  if (options.personaId || isMockMode()) {
    const persona = getPersona(options.personaId ?? DEFAULT_PERSONA_ID);
    return mockDelay(clone(persona.check));
  }
  return runCheck(request);
}

/** POST /api/decode-rejection — explain a rejection reason in plain language. */
export async function decodeRejection(
  request: DecodeRejectionRequest,
): Promise<DecodeRejectionResponse> {
  const res = await fetch(`${BASE}/decode-rejection`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  return handle<DecodeRejectionResponse>(res);
}

/** POST /api/translate — translate guidance text into a target language. */
export async function translate(
  request: TranslateRequest,
): Promise<TranslateResponse> {
  const res = await fetch(`${BASE}/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  return handle<TranslateResponse>(res);
}

/** POST /api/report — generate a shareable readiness report. */
export async function generateReport(
  request: ReportRequest,
): Promise<ReportResponse> {
  const res = await fetch(`${BASE}/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  return handle<ReportResponse>(res);
}
