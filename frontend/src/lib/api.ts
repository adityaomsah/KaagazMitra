// Single entry point for every backend API call.
// The Vite dev server proxies /api to http://localhost:8000 (see vite.config.ts).

import type {
  CheckRequest,
  CheckResponse,
  CorrectionRule,
  Document,
  HealthResponse,
  Mismatch,
  ServiceRule,
} from "@/types/api";

const BASE = "/api";

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

/** POST /api/upload — upload a document image for extraction. */
export async function uploadDocument(file: File): Promise<Document> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/upload`, {
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
